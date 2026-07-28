#!/usr/bin/env python
"""Compuestos anuales de frecuencia de agua sobre los salares, desde Landsat.

    python 01_composites.py --salar hombre_muerto
    python 01_composites.py --salar hombre_muerto --anio 2024 --force
    python 01_composites.py --todos

Por cada salar y año arma un GeoTIFF de 4 bandas en `_data/<salar>/<año>.tif`:

    1  wetfreq    fracción de observaciones válidas con MNDWI > 0.15
    2  n_obs      cantidad de observaciones válidas del píxel ese año
    3  ndvi_mean  NDVI medio (para el análisis de vegas)
    4  ndvi_max   NDVI máximo (la vega se ve en el pico, no en el promedio)

POR QUÉ FRECUENCIA Y NO UNA ESCENA. Una escena suelta no distingue una pileta de
evaporación de una laguna natural: las dos dan MNDWI alto. Lo que las separa es la
persistencia. Una pileta operada está bajo salmuera todo el año (frecuencia ≈ 1);
una laguna natural se llena y se seca con la estación (0.2–0.6). Como la frecuencia
es un cociente sobre observaciones válidas, además es inmune a los huecos del
SLC-off de Landsat-7 y a la cobertura parcial de escena.

Fuente: Microsoft Planetary Computer (STAC público, sin credenciales).
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import odc.stac
import planetary_computer as pc
import pystac_client
import rasterio
from odc.geo.geobox import GeoBox
from odc.geo.geom import box
from rasterio.transform import Affine

import aoi

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
CACHE = Path(__file__).resolve().parent.parent / "_data"

# Landsat Collection-2 nivel 2: reflectancia = DN * 2.75e-5 - 0.2, válido en este rango de DN.
L2_SCALE, L2_OFFSET = 2.75e-5, -0.2
L2_DN_MIN, L2_DN_MAX = 7273, 43636

# Sensores con SWIR. Se excluye MSS (Landsat 1-5 temprano), que no tiene SWIR y por
# lo tanto no permite calcular MNDWI.
PLATAFORMAS = ["landsat-4", "landsat-5", "landsat-7", "landsat-8", "landsat-9"]

BANDAS = ["green", "red", "nir08", "swir16", "qa_pixel"]

# Hasta 2 escenas por mes. No es solo por velocidad: es para que el año quede
# repartido parejo. Si se toman todas las escenas disponibles, los meses despejados
# (invierno seco) pesan más que los nublados (verano húmedo), y entonces las lagunas
# naturales —que se llenan justo en verano— se subestiman de forma sistemática.
MAX_POR_MES = 2
HILOS = 8  # las lecturas COG son I/O puro; el cuello de botella es la red, no la CPU


def _geobox(salar: str) -> GeoBox:
    """Grilla UTM fija por salar: todos los años comparten exactamente la misma grilla."""
    w, s, e, n = aoi.bbox(salar)
    g = box(w, s, e, n, crs="EPSG:4326").to_crs(aoi.UTM_EPSG)
    return GeoBox.from_bbox(g.boundingbox, resolution=aoi.RES_M)


def _escenas(cat, salar: str, anio: int) -> list:
    """Escenas Landsat utilizables del año, ya filtradas por sensor y órbita."""
    res = cat.search(
        collections=["landsat-c2-l2"],
        bbox=aoi.bbox(salar),
        datetime=f"{anio}-01-01/{anio}-12-31",
        query={"eo:cloud_cover": {"lt": 60}, "platform": {"in": PLATAFORMAS}},
    )
    items = list(res.items())

    out = []
    for it in items:
        # Landsat-7 quedó a la deriva: desde 2022 la hora de paso se corre tanto que
        # la geometría de iluminación deja de ser comparable con el resto de la serie.
        if it.properties["platform"] == "landsat-7" and it.datetime.year >= 2022:
            continue
        # MSS entra en la misma colección pero no tiene SWIR.
        if "swir16" not in it.assets:
            continue
        out.append(it)

    # Estratificar por mes: las menos nubladas de cada mes, hasta MAX_POR_MES.
    por_mes: dict[int, list] = defaultdict(list)
    for it in out:
        por_mes[it.datetime.month].append(it)
    elegidas = []
    for mes in sorted(por_mes):
        cand = sorted(por_mes[mes], key=lambda i: i.properties.get("eo:cloud_cover", 100))
        elegidas.extend(cand[:MAX_POR_MES])
    return sorted(elegidas, key=lambda i: i.datetime)


def _cargar(it, gb: GeoBox):
    """Lee una escena y devuelve sus aportes al acumulador. Corre en hilo aparte."""
    ds = odc.stac.load([it], bands=BANDAS, geobox=gb, chunks=None)

    qa = ds["qa_pixel"].isel(time=0).values.astype("uint16")
    ok = _valido(qa)
    if not ok.any():
        return None

    verde = _reflectancia(ds["green"].isel(time=0).values)
    swir = _reflectancia(ds["swir16"].isel(time=0).values)
    rojo = _reflectancia(ds["red"].isel(time=0).values)
    nir = _reflectancia(ds["nir08"].isel(time=0).values)

    # Dos máscaras separadas, no una. Sobre las piletas más brillantes el NIR
    # satura y queda sin dato; exigir NIR finito para TODO borraba esos píxeles
    # también de la serie de agua, que solo necesita verde y SWIR.
    ok_agua = ok & np.isfinite(verde) & np.isfinite(swir)
    ok_ndvi = ok_agua & np.isfinite(rojo) & np.isfinite(nir)
    if not ok_agua.any():
        return None

    with np.errstate(invalid="ignore", divide="ignore"):
        mndwi = (verde - swir) / (verde + swir)
        ndvi = (nir - rojo) / (nir + rojo)

    return (ok_agua, ok_agua & _agua(mndwi),
            np.where(ok_ndvi, ndvi, np.nan).astype("float32"),
            it.properties["platform"])


def _valido(qa: np.ndarray) -> np.ndarray:
    """Máscara de píxeles usables a partir de QA_PIXEL de Landsat C2.

    Solo se descartan relleno (bit 0), nube confirmada (bit 3) y sombra de nube
    (bit 4).

    NO se exige el bit 6 "despejado" ni se descarta el bit 5 "nieve", y la razón
    es concreta: sobre un salar, CFMask se equivoca de forma sistemática. La costra
    de sal es blanca y fría, así que la marca como nube o como nieve en casi todas
    las escenas. Con la máscara estricta, el interior del salar quedaba con menos de
    6 observaciones válidas por año —323 km² en 2005— mientras los cerros de
    alrededor tenían 20. El contorno del salar aparecía calcado en el mapa de
    observaciones, que es la firma inconfundible del problema.

    Sacar la nieve del QA no deja el problema abierto: la nieve es transitoria y no
    sobrevive al criterio de frecuencia anual (no nieva el 80 % del año).
    """
    relleno = (qa & 0b1) > 0
    nube = (qa & (1 << 3)) > 0
    sombra = (qa & (1 << 4)) > 0
    return ~relleno & ~nube & ~sombra & (qa != 0)


def _agua(mndwi: np.ndarray) -> np.ndarray:
    """Agua/salmuera: MNDWI por encima del umbral calibrado.

    Hubo aquí una condición extra `NIR < 0.25`, puesta para descartar nieve. Estaba
    mal, y la validación contra OSM lo mostró: en las piletas de Atacama el NIR es
    tan alto que satura, así que la condición descartaba justo las piletas más
    concentradas y el recall caía al 38 %. Con un MNDWI más exigente y sin NIR sube
    al 75 %, y encima con menos falsos positivos. Ver aoi.MNDWI_AGUA.
    """
    return mndwi > aoi.MNDWI_AGUA


def _reflectancia(dn: np.ndarray) -> np.ndarray:
    """DN → reflectancia, con NaN fuera del rango válido."""
    dn = dn.astype("float32")
    malo = (dn < L2_DN_MIN) | (dn > L2_DN_MAX)
    r = dn * L2_SCALE + L2_OFFSET
    r[malo] = np.nan
    return r


def compuesto(cat, salar: str, anio: int, gb: GeoBox, verbose: bool = True) -> dict | None:
    """Acumula el año escena por escena. Memoria acotada: no apila, acumula."""
    items = _escenas(cat, salar, anio)
    if not items:
        if verbose:
            print(f"    {anio}: sin escenas utilizables", flush=True)
        return None

    forma = (gb.shape[0], gb.shape[1])
    n_obs = np.zeros(forma, dtype="uint16")
    n_agua = np.zeros(forma, dtype="uint16")
    ndvi_suma = np.zeros(forma, dtype="float32")
    ndvi_n = np.zeros(forma, dtype="uint16")
    ndvi_max = np.full(forma, -np.inf, dtype="float32")

    def _seguro(it):
        try:
            return _cargar(it, gb)
        except Exception as ex:  # escena corrupta o caída puntual del endpoint
            if verbose:
                print(f"      ! {it.id}: {str(ex)[:70]}", flush=True)
            return None

    usadas, plats = 0, set()
    with ThreadPoolExecutor(max_workers=HILOS) as pool:
        for res in pool.map(_seguro, items):
            if res is None:
                continue
            ok, agua, ndvi, plat = res
            n_obs += ok
            n_agua += agua
            ndvi_suma += np.nan_to_num(ndvi)
            ndvi_n += ok
            ndvi_max = np.maximum(ndvi_max, np.where(ok, ndvi, -np.inf))
            usadas += 1
            plats.add(plat)

    if usadas == 0:
        if verbose:
            print(f"    {anio}: {len(items)} escenas, ninguna con píxeles válidos", flush=True)
        return None

    with np.errstate(invalid="ignore", divide="ignore"):
        wetfreq = np.where(n_obs > 0, n_agua / np.maximum(n_obs, 1), np.nan).astype("float32")
        ndvi_mean = np.where(ndvi_n > 0, ndvi_suma / np.maximum(ndvi_n, 1), np.nan).astype("float32")
    ndvi_max = np.where(np.isfinite(ndvi_max), ndvi_max, np.nan).astype("float32")

    cobertura = float((n_obs > 0).mean())
    if verbose:
        print(f"    {anio}: {usadas}/{len(items)} escenas ({','.join(sorted(plats))})  "
              f"cobertura {cobertura*100:5.1f}%  mediana n_obs {int(np.median(n_obs))}", flush=True)

    return {"wetfreq": wetfreq, "n_obs": n_obs.astype("float32"),
            "ndvi_mean": ndvi_mean, "ndvi_max": ndvi_max,
            "n_escenas": usadas, "plataformas": sorted(plats), "cobertura": cobertura}


def escribir(destino: Path, capas: dict, gb: GeoBox) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    a = gb.transform
    perfil = {
        "driver": "GTiff", "height": gb.shape[0], "width": gb.shape[1],
        "count": 4, "dtype": "float32", "crs": aoi.UTM_EPSG,
        "transform": Affine(a.a, a.b, a.c, a.d, a.e, a.f),
        "nodata": np.nan, "compress": "deflate", "predictor": 3, "tiled": True,
    }
    nombres = ["wetfreq", "n_obs", "ndvi_mean", "ndvi_max"]
    tmp = destino.with_suffix(".tif.tmp")
    with rasterio.open(tmp, "w", **perfil) as dst:
        for i, nm in enumerate(nombres, start=1):
            dst.write(capas[nm], i)
            dst.set_band_description(i, nm)
        dst.update_tags(n_escenas=capas["n_escenas"],
                        plataformas=",".join(capas["plataformas"]),
                        cobertura=f"{capas['cobertura']:.4f}")
    tmp.replace(destino)  # atómico: si el proceso muere, no queda un .tif a medias


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salar", help=f"uno de: {', '.join(aoi.todos())}")
    ap.add_argument("--todos", action="store_true", help="todos los salares, en orden de prioridad")
    ap.add_argument("--anio", type=int, help="un año puntual (por defecto, la serie entera)")
    ap.add_argument("--desde", type=int, default=aoi.ANIO_INICIO)
    ap.add_argument("--hasta", type=int, default=aoi.ANIO_FIN)
    ap.add_argument("--force", action="store_true", help="recomputar años ya cacheados")
    args = ap.parse_args()

    if args.todos:
        salares = aoi.todos()
    elif args.salar:
        if args.salar not in aoi.SALARES:
            print(f"salar desconocido: {args.salar}. Opciones: {', '.join(aoi.todos())}")
            return 2
        salares = [args.salar]
    else:
        ap.error("indicá --salar o --todos")

    anios = [args.anio] if args.anio else list(range(args.desde, args.hasta + 1))
    cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)

    for salar in salares:
        gb = _geobox(salar)
        meta = aoi.SALARES[salar]
        print(f"\n==> {meta['nombre']}  grilla {gb.shape[0]}x{gb.shape[1]} px @ {aoi.RES_M} m"
              f"{'' if meta['verificado'] else '  [BBOX SIN VERIFICAR]'}", flush=True)

        for anio in anios:
            destino = CACHE / salar / f"{anio}.tif"
            if destino.exists() and not args.force:
                print(f"    {anio}: ya está en caché", flush=True)
                continue
            t0 = time.time()
            try:
                capas = compuesto(cat, salar, anio, gb)
            except Exception as ex:
                print(f"    {anio}: ERROR {str(ex)[:100]}", flush=True)
                continue
            if capas is None:
                continue
            escribir(destino, capas, gb)
            print(f"         → {destino.relative_to(CACHE.parent)}  ({time.time()-t0:.0f} s)", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
