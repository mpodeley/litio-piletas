#!/usr/bin/env python
"""Vegas, bofedales y agua natural: ¿la expansión de piletas coincide con retracción?

    python 03_agua_vegas.py --todos

Es la pregunta de licencia social, y es la más fácil de contestar mal. Se puede
medir que las vegas retrocedieron y que las piletas crecieron en el mismo período
sin que una cosa cause la otra: en la Puna compiten al menos tres explicaciones
—extracción industrial, variabilidad de la precipitación andina, y pastoreo—.

Por eso el diseño es comparativo. Si la vegetación se retrae **igual** en salares
con operación grande y en salares casi vírgenes, el driver dominante es regional
(clima) y no la operación. Ese contraste es lo único que el satélite puede aportar
acá, y se reporta aunque dé nulo.

A 4.000 m de altura cualquier píxel con NDVI apreciable es vega o bofedal: no hay
otra vegetación. Por eso alcanza un umbral simple y no hace falta clasificar.

Salida: docs/data/vegas.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

import aoi

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "_data"
SALIDA = RAIZ / "docs" / "data"

# En la Puna sobre 3.500 m, NDVI por encima de esto es vega/bofedal.
NDVI_VEGA = 0.15
# Un píxel es vega estable si lo fue en esta fracción de los años medibles.
FRAC_ESTABLE = 0.5
MIN_OBS = 10


def serie_vegas(salar: str) -> dict | None:
    d = CACHE / salar
    tifs = sorted(d.glob("[0-9][0-9][0-9][0-9].tif"))
    if not tifs:
        return None

    anios, extension, ndvi_capas, mascaras = [], [], [], []
    for t in tifs:
        with rasterio.open(t) as ds:
            nobs = ds.read(2)
            ndvi_max = ds.read(4)
        if np.nanmedian(nobs) < MIN_OBS:
            continue
        medible = np.isfinite(ndvi_max) & (nobs >= MIN_OBS)
        vega = medible & (ndvi_max > NDVI_VEGA)
        anios.append(int(t.stem))
        extension.append(round(float(vega.sum()) * aoi.PIXEL_KM2, 2))
        ndvi_capas.append(np.where(vega, ndvi_max, np.nan))
        mascaras.append(vega)

    if len(anios) < 5:
        return None

    # Vega estable: donde hubo vegetación en al menos la mitad de los años medibles.
    # Sobre ese conjunto fijo se mide la INTENSIDAD, que es más sensible que la
    # extensión: un bofedal que se estresa pierde vigor antes que superficie.
    estable = np.mean(np.stack(mascaras), axis=0) >= FRAC_ESTABLE
    intensidad = [round(float(np.nanmean(np.where(estable, c, np.nan))), 4)
                  if estable.any() else None for c in ndvi_capas]

    return {
        "salar": salar,
        "nombre": aoi.SALARES[salar]["nombre"],
        "vega_estable_km2": round(float(estable.sum()) * aoi.PIXEL_KM2, 2),
        "serie": [{"anio": a, "vegas_km2": e, "ndvi_medio_vega_estable": i}
                  for a, e, i in zip(anios, extension, intensidad)],
    }


def tendencia(serie: list[dict], clave: str) -> float | None:
    """Pendiente por año, por mínimos cuadrados. Sin p-valor: la serie es corta
    y autocorrelacionada, y poner un p acá daría una falsa sensación de rigor."""
    pts = [(f["anio"], f[clave]) for f in serie if f.get(clave) is not None]
    if len(pts) < 5:
        return None
    x, y = np.array([p[0] for p in pts], float), np.array([p[1] for p in pts], float)
    return round(float(np.polyfit(x, y, 1)[0]), 5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salar")
    ap.add_argument("--todos", action="store_true")
    args = ap.parse_args()
    salares = aoi.todos() if args.todos else [args.salar] if args.salar else None
    if not salares:
        ap.error("indicá --salar o --todos")

    piletas = {}
    f = SALIDA / "piletas.json"
    if f.exists():
        piletas = {r["salar"]: r for r in json.loads(f.read_text())["data"]}

    resultados = []
    print(f"{'salar':>20} {'vega estable':>13} {'tend. sup.':>12} {'tend. NDVI':>12} {'piletas':>10}")
    for salar in salares:
        r = serie_vegas(salar)
        if not r:
            print(f"{salar:>20}   (sin años medibles suficientes)")
            continue
        r["tendencia_vegas_km2_por_anio"] = tendencia(r["serie"], "vegas_km2")
        r["tendencia_ndvi_por_anio"] = tendencia(r["serie"], "ndvi_medio_vega_estable")
        p = piletas.get(salar)
        r["piletas_km2_ultimo"] = p["serie"][-1]["piletas_km2"] if p else None
        resultados.append(r)
        print(f"{salar:>20} {r['vega_estable_km2']:>12.1f} "
              f"{r['tendencia_vegas_km2_por_anio'] or 0:>12.3f} "
              f"{r['tendencia_ndvi_por_anio'] or 0:>12.5f} "
              f"{r['piletas_km2_ultimo'] or 0:>10.1f}")

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "vegas.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Landsat 4/5/7/8/9 Collection-2 L2 vía Microsoft Planetary Computer",
        "metodo": f"vega = NDVI máximo anual > {NDVI_VEGA}; intensidad sobre el conjunto "
                  f"estable (vega en ≥{FRAC_ESTABLE:.0%} de los años medibles)",
        "advertencia": "Coincidencia temporal no es causalidad. La comparación entre "
                       "salares con y sin operación es lo único interpretable.",
        "data": resultados,
    }, ensure_ascii=False, indent=1))
    print(f"\n→ docs/data/vegas.json")

    if len(resultados) >= 3:
        print("\nLectura: si la tendencia de NDVI es parecida en salares con operación "
              "grande\ny en salares casi vírgenes, el driver es regional y no la operación.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
