#!/usr/bin/env python
"""Cruzar la superficie de piletas medida contra la producción declarada.

    python 04_validar.py

Suma la superficie de piletas de los salares argentinos y la compara con las
exportaciones nacionales de litio en toneladas LCE. Reporta la correlación con
desfasaje de 0, 1 y 2 años.

POR QUÉ CON DESFASAJE. La salmuera tarda entre 12 y 24 meses en recorrer la cadena
de piletas: se bombea, se evapora, se concentra, y recién después sale como
producto. La superficie construida **adelanta** a la producción declarada, así que
la correlación sin desfasaje subestima la relación. Si el máximo cae en 1 o 2 años
de adelanto, eso es evidencia a favor; si cae en 0 o en negativo, es evidencia en
contra y hay que decirlo.

QUÉ NO PRUEBA ESTO. Correlación entre dos series anuales cortas —una docena de
puntos como mucho— no establece causalidad, y menos con dos series que crecen las
dos en el tiempo. Con tan pocos puntos no se reporta p-valor: daría una falsa
sensación de rigor. Se reporta el coeficiente, el n, y nada más.

Salida: docs/data/validacion_produccion.json
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import aoi

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "docs" / "data"

# Solo los salares argentinos con producción comercial y serie medible. Se dejan
# afuera el Rincón (sin producción comercial: figura en Construcción y Factibilidad
# en el informe de la Secretaría de Minería) y Centenario-Ratones (arrancó a fines
# de 2024 y casi no tiene años que superen el mínimo de observaciones). Los dos
# aportan ~0 km² de piletas, así que excluirlos no cambia la suma — pero exigir que
# estuvieran medidos vaciaba la serie entera.
SALARES_AR = ["hombre_muerto", "olaroz_cauchari"]
DESFASAJES = (0, 1, 2)


def leer_produccion() -> dict[int, float]:
    """Exportaciones nacionales argentinas en toneladas LCE, por año."""
    f = DATOS / "produccion_litio.csv"
    if not f.exists():
        sys.exit("falta docs/data/produccion_litio.csv")
    serie = {}
    with f.open(encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            if fila["ambito"] != "AR" or not fila["exportaciones_t_lce"]:
                continue
            serie[int(fila["anio"])] = float(fila["exportaciones_t_lce"])
    return serie


def superficie_argentina(datos: list[dict]) -> dict[int, float]:
    """Suma de piletas de los salares argentinos, solo en años cuantitativos."""
    por_anio: dict[int, list[float]] = {}
    for r in datos:
        if r["salar"] not in SALARES_AR:
            continue
        for f in r["serie"]:
            if not f.get("cuantitativo", True):
                continue
            por_anio.setdefault(f["anio"], []).append(f["piletas_km2"])
    # Solo años en que están medidos TODOS los salares argentinos disponibles:
    # sumar un subconjunto variable haría que la serie salte por composición.
    completos = max((len(v) for v in por_anio.values()), default=0)
    return {a: round(sum(v), 2) for a, v in por_anio.items() if len(v) == completos}


def correlacion(area: dict[int, float], prod: dict[int, float], desfase: int) -> dict:
    """Área del año Y contra producción del año Y+desfase."""
    pares = [(area[a], prod[a + desfase]) for a in sorted(area)
             if a + desfase in prod]
    if len(pares) < 5:
        return {"desfase_anios": desfase, "n": len(pares), "r": None,
                "nota": "menos de 5 años en común: no se calcula"}
    x, y = np.array([p[0] for p in pares]), np.array([p[1] for p in pares])
    if x.std() == 0 or y.std() == 0:
        return {"desfase_anios": desfase, "n": len(pares), "r": None,
                "nota": "una de las series es constante"}
    return {"desfase_anios": desfase, "n": len(pares),
            "r": round(float(np.corrcoef(x, y)[0, 1]), 3),
            "anios": [a for a in sorted(area) if a + desfase in prod]}


def main() -> int:
    f = DATOS / "piletas.json"
    if not f.exists():
        sys.exit("falta docs/data/piletas.json — corré antes 02_piletas.py")
    datos = json.loads(f.read_text())["data"]

    area = superficie_argentina(datos)
    prod = leer_produccion()
    if not area:
        sys.exit("no hay años cuantitativos con todos los salares argentinos medidos")

    print("Superficie de piletas en salares argentinos vs exportaciones nacionales\n")
    print(f"{'año':>6} {'piletas km²':>12} {'export t LCE':>13}")
    for a in sorted(area):
        p = prod.get(a)
        print(f"{a:>6} {area[a]:>12.1f} {(f'{p:,.0f}' if p else '—'):>13}")

    resultados = [correlacion(area, prod, d) for d in DESFASAJES]
    print(f"\n{'desfase':>8} {'n':>4} {'r':>8}")
    for r in resultados:
        rr = f"{r['r']:+.3f}" if r["r"] is not None else r.get("nota", "—")
        print(f"{r['desfase_anios']:>7}a {r['n']:>4} {rr:>8}")

    validos = [r for r in resultados if r["r"] is not None]
    mejor = max(validos, key=lambda r: abs(r["r"])) if validos else None
    if mejor:
        signo = "adelanta" if mejor["desfase_anios"] > 0 else "coincide con"
        print(f"\nMáximo en desfasaje {mejor['desfase_anios']} año(s): la superficie "
              f"{signo} la producción.")
        if mejor["desfase_anios"] == 0:
            print("Eso NO es lo esperado: la salmuera tarda 12-24 meses en la cadena.")
        if abs(mejor["r"]) < 0.5:
            print("Correlación débil. Se publica igual: el resultado es que el área "
                  "no explica bien la producción declarada.")

    salida = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Piletas: Landsat vía Planetary Computer, elaboración propia. "
                  "Producción: Secretaría de Minería de la Nación, Informe Litio jun-2025.",
        "advertencia": "Series anuales cortas y las dos crecientes en el tiempo. "
                       "La correlación no establece causalidad y no se reporta p-valor.",
        "salares_incluidos": SALARES_AR,
        "serie_area_km2": area,
        "serie_exportaciones_t_lce": {a: prod[a] for a in sorted(prod)},
        "correlaciones": resultados,
    }
    (DATOS / "validacion_produccion.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1))
    print(f"\n→ docs/data/validacion_produccion.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
