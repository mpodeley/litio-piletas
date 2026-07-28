#!/usr/bin/env python
"""Separa piletas de evaporación de agua natural, y arma la serie anual.

    python 02_piletas.py --salar hombre_muerto
    python 02_piletas.py --todos

EL PROBLEMA. Una pileta de evaporación y el núcleo saturado de un salar dan los dos
frecuencia de agua ≈ 1: están mojados todo el año. Umbralar `wetfreq` y nada más
cuenta como pileta a la costra que ya estaba mojada antes de que existiera la
operación. Sobre Hombre Muerto en 2024 eso da 73 km², bastante más que las piletas
reales.

LA SOLUCIÓN. Una pileta no es "superficie mojada": es superficie que **pasó a estar
mojada de forma permanente y antes no lo estaba**. Se compara cada año contra una
línea de base de los primeros años de la serie:

    pileta(año) = wetfreq(año) > 0.80   Y   wetfreq_base < 0.20

El agua natural permanente estaba mojada también en la base, así que queda afuera
por construcción, no por elección de umbral. Y lo que se mide pasa a ser una
cantidad con sentido físico: superficie inundada **agregada** desde la línea de base.

Salidas:
  docs/data/piletas.json            series anuales por salar
  _data/<salar>/piletas_anio.tif    año en que cada píxel se volvió pileta
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from scipy import ndimage

import aoi

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "_data"
SALIDA = RAIZ / "docs" / "data"

# Años de línea de base: los primeros de la serie, siempre anteriores al arranque
# de la operación. Se toma la mediana para que una temporada húmeda suelta no
# levante la base y borre piletas reales.
BASE_N = 6
BASE_MARGEN = 1  # cerrar la base este número de años antes del arranque

# Mínimo de píxeles de un cuerpo para contarlo (900 m² por píxel).
MIN_PX = 20  # 1.8 ha

# Mínimo de observaciones válidas para que la frecuencia signifique algo.
#
# Con pocas pasadas la frecuencia está sesgada HACIA ARRIBA: si un píxel tiene 4
# observaciones, wetfreq solo puede valer 0, 0.25, 0.5, 0.75 o 1, y llegar a 1 es
# fácil. Así, los píxeles peor observados son justo los que más se cuelan como
# "agua permanente". Por eso el mínimo es 10 y no 6.
MIN_OBS = 10

# Un año se considera cuantitativo si esta fracción del AOI llega a MIN_OBS.
FIABLE = 0.60

# Umbrales alternativos que se reportan al lado del elegido. Con ~10 pasadas por año,
# exigir >0.80 es filoso: una sola nube sobre una pileta la baja a 8/10 y la borra.
# Publicar la banda completa muestra cuánto del resultado depende de dónde se corta.
SENSIBILIDAD = (0.65, 0.75, 0.85)

# Un píxel entra al mapa de "año de aparición" solo si califica en 2 años seguidos:
# evita que una inundación puntual quede registrada como nacimiento de una pileta.
PERSISTENCIA = 2


def cargar_serie(salar: str) -> tuple[list[int], np.ndarray, np.ndarray, dict]:
    """Apila wetfreq y n_obs de todos los años cacheados.

    Los años con muy pocas pasadas se descartan enteros: con 2 o 3 observaciones,
    "fracción del año bajo agua" no significa nada. Landsat-5 en 1985 sobre la Puna
    deja apenas 4 escenas utilizables.
    """
    d = CACHE / salar
    tifs = sorted(d.glob("[0-9][0-9][0-9][0-9].tif"))
    if not tifs:
        raise SystemExit(f"no hay compuestos en {d} — corré antes 01_composites.py")

    anios, wf, nobs, perfil = [], [], [], None
    for t in tifs:
        with rasterio.open(t) as ds:
            if perfil is None:
                perfil = {"crs": ds.crs, "transform": ds.transform,
                          "width": ds.width, "height": ds.height}
            a, b = ds.read(1), ds.read(2)
        if np.nanmedian(b) < MIN_OBS:
            print(f"    (salteado {t.stem}: mediana de {np.nanmedian(b):.0f} observaciones)")
            continue
        anios.append(int(t.stem))
        wf.append(a)
        nobs.append(b)
    return anios, np.stack(wf), np.stack(nobs), perfil


def linea_base(anios: list[int], cubo: np.ndarray, salar: str) -> tuple[np.ndarray, list[int]]:
    """Agua natural permanente: lo que sigue mojado incluso en los años secos.

    No alcanza con promediar los primeros años. La superficie húmeda natural del
    salar varía muchísimo de un año a otro: en Hombre Muerto, 1987 y 1993 inundan
    ~60 km² y 1998 casi nada. Si la base es la mediana de un período que incluye
    años húmedos, queda alta justo en el centro-sur del salar — que es exactamente
    donde después se construyen las piletas, porque ahí la salmuera está somera.
    Resultado: se descuentan piletas reales.

    Por eso la base se arma con los años SECOS previos a la operación. Lo que está
    mojado hasta en un año seco es agua natural permanente; lo demás es estacional
    y no debería inflar la base.
    """
    corte = aoi.inicio_operacion(salar) - BASE_MARGEN
    previos = [i for i, a in enumerate(anios) if a < corte]
    if len(previos) < 3:
        # Atacama opera desde 1984 y Landsat arranca en 1985: no hay base previa
        # real. Se usan los primeros años disponibles y se declara el límite.
        previos = list(range(min(BASE_N * 2, len(anios))))

    # Ordenar los años previos por superficie húmeda total y quedarse con los más secos.
    humedad = [(float(np.nansum(cubo[i] > aoi.WETFREQ_NATURAL)), i) for i in previos]
    humedad.sort()
    idx = sorted(i for _, i in humedad[:BASE_N])
    base = np.nanmedian(cubo[idx], axis=0)
    return base, [anios[i] for i in idx]


def rectangularidad(mascara: np.ndarray) -> float:
    """Fracción del área que cae en cuerpos con forma de pileta (bordes rectos).

    Diagnóstico, no filtro: una pileta llena su caja envolvente casi por completo
    porque es un rectángulo; una laguna natural, no. Sirve para mostrar que lo
    detectado tiene geometría artificial y no es una mancha de agua cualquiera.
    """
    etiquetas, n = ndimage.label(mascara)
    if n == 0:
        return float("nan")
    total = buenos = 0
    for sl in ndimage.find_objects(etiquetas):
        alto, ancho = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = int(mascara[sl].sum())
        if area < MIN_PX:
            continue
        total += area
        if area / max(alto * ancho, 1) > 0.6:
            buenos += area
    return round(buenos / total, 3) if total else float("nan")


def limpiar(mascara: np.ndarray) -> np.ndarray:
    """Saca motas y rellena huecos chicos. Las piletas son cuerpos grandes y compactos."""
    m = ndimage.binary_opening(mascara, structure=np.ones((3, 3)))
    m = ndimage.binary_closing(m, structure=np.ones((3, 3)))
    etiquetas, n = ndimage.label(m)
    if n == 0:
        return m
    tam = np.bincount(etiquetas.ravel())
    tam[0] = 0
    return np.isin(etiquetas, np.flatnonzero(tam >= MIN_PX))


def rasterizar_osm(geojson: Path, perfil: dict, tags: tuple[str, ...]) -> np.ndarray | None:
    """Pasa a la grilla UTM las poligonales de OSM que tengan alguno de estos tags."""
    if not geojson.exists():
        return None
    fc = json.loads(geojson.read_text())
    geoms = [transform_geom("EPSG:4326", perfil["crs"].to_string(), f["geometry"])
             for f in fc.get("features", []) if f["properties"].get("tag") in tags]
    if not geoms:
        return None
    return rasterize(geoms, out_shape=(perfil["height"], perfil["width"]),
                     transform=perfil["transform"], dtype="uint8").astype(bool)


def analizar(salar: str, osm: Path | None = None) -> dict:
    anios, cubo, nobs, perfil = cargar_serie(salar)
    base, anios_base = linea_base(anios, cubo, salar)
    km2 = aoi.PIXEL_KM2

    nueva = base < aoi.WETFREQ_NATURAL          # superficie seca en la línea de base
    ya_mojado = base >= aoi.WETFREQ_PILETA      # agua natural permanente

    serie, mascaras = [], []
    for i, anio in enumerate(anios):
        wf = cubo[i]
        # Un píxel con pocas pasadas ese año no se clasifica: su frecuencia es ruido.
        medible = np.isfinite(wf) & (nobs[i] >= MIN_OBS)
        permanente = medible & (wf >= aoi.WETFREQ_PILETA)
        pileta = limpiar(permanente & nueva)
        mascaras.append(pileta)
        serie.append({
            "anio": anio,
            "piletas_km2": round(float(pileta.sum()) * km2, 2),
            "rectangularidad": rectangularidad(pileta),
            # Cota superior: toda la superficie permanentemente mojada, sin descontar
            # la natural. La cifra real está entre las dos, y se publican las dos.
            "permanente_total_km2": round(float(permanente.sum()) * km2, 2),
            # Cuánto se mueve el resultado si se corta en otro lado.
            "sensibilidad_km2": {
                f"{u:.2f}": round(float(limpiar(medible & (wf >= u) & nueva).sum()) * km2, 2)
                for u in SENSIBILIDAD},
            "px_medibles_pct": round(float(medible.mean()) * 100, 1),
            # Landsat 5 y 7 se saturan sobre la costra de sal brillante y el producto
            # L2 descarta esos píxeles. Por eso hay años sin cobertura suficiente, y
            # se marcan en vez de presentarlos como si valieran lo mismo.
            "cuantitativo": bool(medible.mean() >= FIABLE),
            "agua_natural_permanente_km2": round(float((permanente & ya_mojado).sum()) * km2, 2),
            "agua_estacional_km2": round(
                float((np.isfinite(wf) & (wf >= aoi.WETFREQ_NATURAL)
                       & (wf <= aoi.WETFREQ_PILETA)).sum()) * km2, 2),
        })

    # Año de aparición: primer año en que el píxel es pileta y lo sigue siendo.
    pila = np.stack(mascaras)
    aparicion = np.zeros(pila.shape[1:], dtype="float32")
    for i in range(len(anios) - PERSISTENCIA + 1):
        sostenido = np.all(pila[i:i + PERSISTENCIA], axis=0)
        nuevo = sostenido & (aparicion == 0)
        aparicion[nuevo] = anios[i]
    aparicion[aparicion == 0] = np.nan

    res = {
        "salar": salar,
        "nombre": aoi.SALARES[salar]["nombre"],
        "jurisdiccion": aoi.SALARES[salar]["jurisdiccion"],
        "operaciones": aoi.SALARES[salar]["operaciones"],
        "bbox_verificado": aoi.SALARES[salar]["verificado"],
        "anios_base": anios_base,
        "base_previa_a_operacion": max(anios_base) < aoi.inicio_operacion(salar),
        "serie": serie,
    }

    # Validación contra OSM. Solo sirve donde alguien haya digitalizado las piletas:
    # `landuse=salt_pond` es la referencia positiva de verdad (Atacama tiene 388).
    # Donde solo hay `landuse=industrial` (Hombre Muerto), eso es la huella de la
    # concesión, no las piletas, y compararse contra eso no mide nada.
    pred = mascaras[-1]
    ref = rasterizar_osm(osm, perfil, ("landuse=salt_pond", "landuse=salt_works")) if osm else None
    if ref is not None and ref.any():
        vp = int((pred & ref).sum())
        fp = int((pred & ~ref).sum())
        fn = int((~pred & ref).sum())
        res["validacion_osm"] = {
            "anio": anios[-1],
            "referencia": "landuse=salt_pond",
            "poligonos_osm_km2": round(float(ref.sum()) * km2, 2),
            "precision": round(vp / max(vp + fp, 1), 3),
            "recall": round(vp / max(vp + fn, 1), 3),
            "iou": round(vp / max(vp + fp + fn, 1), 3),
        }
    else:
        res["validacion_osm"] = {"referencia": None,
                                 "nota": "OSM no tiene las piletas digitalizadas en este salar"}

    # Control negativo: las lagunas naturales mapeadas (Chaxa, Barros Negros...) no
    # tendrían que caer dentro de la máscara de piletas. Es la prueba de que el
    # método no está contando agua natural.
    lagunas = rasterizar_osm(osm, perfil, ("natural=water",)) if osm else None
    if lagunas is not None and lagunas.any():
        res["control_negativo"] = {
            "lagunas_naturales_km2": round(float(lagunas.sum()) * km2, 2),
            "fraccion_clasificada_como_pileta": round(
                float((pred & lagunas).sum()) / float(lagunas.sum()), 3),
        }

    # Guardar el mapa de año de aparición.
    destino = CACHE / salar / "piletas_anio.tif"
    with rasterio.open(destino, "w", driver="GTiff", height=perfil["height"],
                       width=perfil["width"], count=1, dtype="float32",
                       crs=perfil["crs"], transform=perfil["transform"],
                       nodata=np.nan, compress="deflate", tiled=True) as ds:
        ds.write(aparicion, 1)
        ds.set_band_description(1, "anio_aparicion_pileta")

    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salar")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--osm", type=Path, default=None,
                    help="GeoJSON de piletas para validar (por defecto, el del salar en _data/)")
    args = ap.parse_args()

    salares = aoi.todos() if args.todos else [args.salar] if args.salar else None
    if not salares:
        ap.error("indicá --salar o --todos")

    resultados = []
    for salar in salares:
        osm = args.osm or (CACHE / salar / "osm_piletas.geojson")
        if not (CACHE / salar).exists():
            print(f"-- {salar}: sin compuestos todavía, salteado")
            continue
        r = analizar(salar, osm)
        resultados.append(r)

        ult = r["serie"][-1]
        print(f"\n=== {r['nombre']} ===")
        print(f"  línea de base: {r['anios_base'][0]}-{r['anios_base'][-1]}"
              f"{'' if r['base_previa_a_operacion'] else '  [NO es previa a la operación]'}")
        print(f"  {'año':>6} {'piletas':>10} {'nat.perm':>10} {'estacional':>11}")
        for f in r["serie"]:
            if f["anio"] % 5 == 0 or f is r["serie"][-1]:
                print(f"  {f['anio']:>6} {f['piletas_km2']:>9.1f} {f['agua_natural_permanente_km2']:>10.1f}"
                      f" {f['agua_estacional_km2']:>11.1f}")
        v = r.get("validacion_osm", {})
        if v.get("referencia"):
            print(f"  OSM {v['anio']} ({v['referencia']}): precisión {v['precision']} · "
                  f"recall {v['recall']} · IoU {v['iou']}  (referencia {v['poligonos_osm_km2']} km²)")
        else:
            print(f"  OSM: {v.get('nota', 'sin referencia')}")
        cn = r.get("control_negativo")
        if cn:
            print(f"  control negativo: {cn['fraccion_clasificada_como_pileta']*100:.1f}% de las "
                  f"lagunas naturales mapeadas ({cn['lagunas_naturales_km2']} km²) cae en la máscara")

    SALIDA.mkdir(parents=True, exist_ok=True)
    envoltorio = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Landsat 4/5/7/8/9 Collection-2 L2 vía Microsoft Planetary Computer",
        "metodo": ("pileta = wetfreq > %.2f en el año Y wetfreq < %.2f en la línea de base"
                   % (aoi.WETFREQ_PILETA, aoi.WETFREQ_NATURAL)),
        "data": resultados,
    }
    (SALIDA / "piletas.json").write_text(json.dumps(envoltorio, ensure_ascii=False, indent=1))
    print(f"\n→ {(SALIDA / 'piletas.json').relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
