#!/usr/bin/env python
"""Mapas interactivos autocontenidos, uno por salar.

    python 06_mapas.py --salar hombre_muerto
    python 06_mapas.py --todos

Escribe docs/assets/mapa_<salar>.html: un solo archivo que se abre en cualquier
navegador sin servidor, sin internet y sin dependencias. Es lo que se proyecta.

Capas:
  · Imagen satelital (Esri World Imagery) de fondo
  · Año de aparición de cada pileta — rampa secuencial azul, claro = viejo
  · Piletas del último año — contorno
  · Poligonales de OpenStreetMap — referencia independiente

Sigue el patrón de litio-subsidencia/docs/pipeline/04_export_visual.py: overlay PNG
embebido en base64 sobre un TileLayer, leyenda flotante con el caveat adentro.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject

import aoi

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "_data"
ASSETS = RAIZ / "docs" / "assets"

# Rampa secuencial azul 100→700 de la paleta de referencia (un solo tono,
# claro→oscuro). Para magnitud ordenada nunca un arcoíris.
RAMPA = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def _a_wgs84(src_path: Path) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Reproyecta a EPSG:4326 para que el overlay calce con el basemap."""
    with rasterio.open(src_path) as src:
        dt, w, h = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
        destino = np.full((h, w), np.nan, dtype="float32")
        reproject(source=rasterio.band(src, 1), destination=destino,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=dt, dst_crs="EPSG:4326",
                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    oeste, norte = dt.c, dt.f
    este, sur = oeste + dt.a * w, norte + dt.e * h
    return destino, (oeste, sur, este, norte)


def _png_b64(rgba: np.ndarray) -> str:
    from matplotlib import pyplot as plt
    buf = io.BytesIO()
    plt.imsave(buf, rgba, format="png")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _leyenda(a0: int, a1: int, res: dict) -> str:
    # Último año CERRADO: el año en curso tiene menos pasadas y da una cifra más baja
    # que no es comparable con la de un año completo.
    cerrados = [f for f in res["serie"] if not f.get("anio_parcial")]
    ult = (cerrados or res["serie"])[-1]
    v = res.get("validacion_osm", {})
    val = (f"Validado contra {v['referencia']} de OSM: recall {v['recall']}, "
           f"precisión {v['precision']}." if v.get("referencia")
           else "OSM no tiene las piletas digitalizadas acá: la validación es temporal, no cuantitativa.")
    marca = "" if ult.get("cuantitativo", True) else " (año sin cobertura suficiente)"
    tramos = "".join(
        f'<span style="display:inline-block;width:26px;height:10px;background:{c}"></span>'
        for c in RAMPA)
    return f"""
    <div style="position:fixed; bottom:22px; left:22px; z-index:9999;
                background:rgba(252,252,251,0.94); padding:11px 14px; max-width:390px;
                border-radius:6px; font:12px/1.45 system-ui,sans-serif; color:#0b0b0b;">
      <b>Año en que apareció la pileta</b><br>
      <div style="margin:5px 0 3px">{tramos}</div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#52514e">
        <span>{a0}</span><span>{a1}</span></div>
      <div style="margin-top:7px;font-size:11px;color:#52514e">
        <b>{ult['piletas_km2']} km²</b> de piletas en {ult['anio']}{marca}, contra una línea de base
        de años secos {res['anios_base'][0]}–{res['anios_base'][-1]}.<br>
        {val}<br>
        Superficie inundada agregada — no es producción.
      </div>
    </div>"""


def mapa(salar: str, resultados: list[dict]) -> Path | None:
    import folium

    tif = CACHE / salar / "piletas_anio.tif"
    if not tif.exists():
        print(f"  {salar}: falta piletas_anio.tif (corré 02_piletas.py)")
        return None
    res = next((r for r in resultados if r["salar"] == salar), None)
    if not res:
        return None

    a, (w, s, e, n) = _a_wgs84(tif)
    finitos = a[np.isfinite(a)]
    if finitos.size == 0:
        print(f"  {salar}: no se detectaron piletas")
        return None
    a0, a1 = int(finitos.min()), int(finitos.max())

    from matplotlib.colors import LinearSegmentedColormap, Normalize
    cmap = LinearSegmentedColormap.from_list("azules", RAMPA)
    rgba = cmap(Normalize(vmin=a0, vmax=max(a1, a0 + 1))(a))
    rgba[..., 3] = np.where(np.isfinite(a), 0.88, 0.0)

    m = folium.Map(location=[(s + n) / 2, (w + e) / 2], zoom_start=11, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satélite").add_to(m)
    folium.raster_layers.ImageOverlay(
        image=f"data:image/png;base64,{_png_b64(rgba)}",
        bounds=[[s, w], [n, e]], opacity=1.0,
        name=f"Año de aparición ({a0}–{a1})").add_to(m)

    osm = CACHE / salar / "osm_piletas.geojson"
    if osm.exists():
        fc = json.loads(osm.read_text())
        piletas = [f for f in fc["features"]
                   if f["properties"].get("tag") in ("landuse=salt_pond", "landuse=salt_works")]
        lagunas = [f for f in fc["features"] if f["properties"].get("tag") == "natural=water"]
        if piletas:
            folium.GeoJson({"type": "FeatureCollection", "features": piletas},
                           name=f"Piletas en OSM ({len(piletas)})",
                           style_function=lambda _f: {"fillOpacity": 0, "color": "#eb6834",
                                                      "weight": 1.0, "opacity": 0.9}).add_to(m)
        if lagunas:
            folium.GeoJson({"type": "FeatureCollection", "features": lagunas},
                           name=f"Lagunas naturales en OSM ({len(lagunas)}) — control negativo",
                           style_function=lambda _f: {"fillOpacity": 0, "color": "#1baf7a",
                                                      "weight": 1.0, "opacity": 0.9}).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_leyenda(a0, a1, res)))

    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"mapa_{salar}.html"
    m.save(str(out))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salar")
    ap.add_argument("--todos", action="store_true")
    args = ap.parse_args()

    f = RAIZ / "docs" / "data" / "piletas.json"
    if not f.exists():
        sys.exit("falta docs/data/piletas.json — corré antes 02_piletas.py")
    resultados = json.loads(f.read_text())["data"]

    salares = aoi.todos() if args.todos else [args.salar] if args.salar else None
    if not salares:
        ap.error("indicá --salar o --todos")

    for salar in salares:
        p = mapa(salar, resultados)
        if p:
            print(f"  {p.relative_to(RAIZ)}  ({p.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
