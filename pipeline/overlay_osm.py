#!/usr/bin/env python
"""Trae de OpenStreetMap las poligonales de piletas e industria de cada salar.

    python overlay_osm.py              # los 5 salares
    python overlay_osm.py --salar rincon

Escribe `_data/<salar>/osm_piletas.geojson`, que 02_piletas.py usa como referencia
independiente para medir precisión y recall, y los mapas dibujan como contorno.

La cobertura de OSM en la Puna es despareja: Hombre Muerto está bien mapeado y los
salares nuevos casi no tienen nada. Donde no hay polígonos, la validación cuantitativa
no se puede hacer y hay que decirlo en vez de inventar una referencia.

Adaptado de litio-subsidencia/docs/pipeline/overlay_osm.py (que cubría un solo AOI).
Sin dependencias externas: urllib de la stdlib.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import aoi

CACHE = Path(__file__).resolve().parent.parent / "_data"
# Espejos: el principal tira 504 seguido cuando está cargado.
ESPEJOS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

TAGS = [
    ("man_made", "salt_pond"),
    ("landuse", "salt_pond"),
    ("landuse", "salt_works"),
    ("landuse", "industrial"),
    ("landuse", "quarry"),
    ("natural", "water"),
    ("water", "pond"),
    ("water", "reservoir"),
    ("water", "salt_pool"),
]


def _query(salar: str) -> str:
    w, s, e, n = aoi.bbox(salar)
    bb = f"{s},{w},{n},{e}"
    partes = []
    for k, v in TAGS:
        partes.append(f'way["{k}"="{v}"]({bb});')
        partes.append(f'relation["{k}"="{v}"]({bb});')
    return f"[out:json][timeout:180];({''.join(partes)});out geom;"


def _consultar(q: str) -> dict:
    ultimo = None
    for url in ESPEJOS:
        for intento in range(2):
            try:
                req = urllib.request.Request(
                    url, data=b"data=" + urllib.parse.quote(q).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded",
                             "User-Agent": "litio-piletas/0.1 (github.com/mpodeley)"})
                with urllib.request.urlopen(req, timeout=200) as r:
                    return json.load(r)
            except Exception as ex:
                ultimo = ex
                time.sleep(5 * (intento + 1))
    raise RuntimeError(f"Overpass no respondió: {ultimo}")


def _anillo(el: dict) -> list | None:
    geom = el.get("geometry")
    if not geom or len(geom) < 4:
        return None
    anillo = [[p["lon"], p["lat"]] for p in geom]
    if anillo[0] != anillo[-1]:
        anillo.append(anillo[0])
    return [anillo]


def traer(salar: str) -> int:
    datos = _consultar(_query(salar))
    feats = []
    for el in datos.get("elements", []):
        if el["type"] != "way":
            continue
        coords = _anillo(el)
        if not coords:
            continue
        tags = el.get("tags", {})
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {"osm_id": el["id"], "name": tags.get("name", ""),
                           "tag": next((f"{k}={v}" for k, v in TAGS if tags.get(k) == v), "")},
        })

    destino = CACHE / salar / "osm_piletas.geojson"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"type": "FeatureCollection", "features": feats}),
                       encoding="utf-8")
    return len(feats)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salar")
    args = ap.parse_args()
    salares = [args.salar] if args.salar else aoi.todos()

    for salar in salares:
        try:
            n = traer(salar)
        except Exception as ex:
            print(f"{salar:20s} ERROR {str(ex)[:70]}")
            continue
        marca = "" if n else "   ← sin referencia: acá no se puede validar contra OSM"
        print(f"{salar:20s} {n:4d} polígonos{marca}")
        time.sleep(3)  # no castigar a Overpass
    return 0


if __name__ == "__main__":
    sys.exit(main())
