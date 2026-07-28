#!/usr/bin/env python
"""Figuras en alta resolución para proyectar en el congreso.

    python 05_figuras.py              # las dos variantes, claro y oscuro
    python 05_figuras.py --modo oscuro

Lee docs/data/piletas.json (lo escribe 02_piletas.py) y los rásters de año de
aparición, y escribe PNGs a 300 dpi en docs/assets/.

Se generan en dos variantes porque tienen dos destinos: el sitio usa tema oscuro,
pero una lámina en PowerPoint o un PDF impreso suelen ir sobre fondo claro.

Paleta: los slots 1-5 de la paleta categórica de referencia, en el orden de
aoi.todos(). Validada con el validador del skill dataviz en los dos modos
(separación CVD y de visión normal por encima del piso en ambos). Los colores
NO se eligieron por gusto: se corrió el chequeo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.lines import Line2D

import aoi

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "docs" / "data"
ASSETS = RAIZ / "docs" / "assets"
CACHE = RAIZ / "_data"

# Primer año con Landsat-8 en órbita: antes de esto, la costra de sal satura los
# sensores viejos y la serie deja de ser cuantitativa (ver docs/limites.md).
ANIO_CUANTITATIVO = 2013

TEMA = {
    "claro": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e",
              "grid": "#e5e4e0", "color": "color"},
    "oscuro": {"surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7",
               "grid": "#333331", "color": "color_oscuro"},
}


def _cerrados(serie: list[dict]) -> list[dict]:
    """Solo años calendario completos.

    El año en curso tiene menos pasadas y su frecuencia anual sale más baja, así que
    graficarlo al lado de años cerrados inventa una caída que no existe: en Atacama,
    30,3 km² en 2025 contra 11,0 en el 2026 incompleto.
    """
    return [f for f in serie if not f.get("anio_parcial")]


def _figura(t: dict, alto: float = 5.4, ancho: float = 9.6):
    fig, ax = plt.subplots(figsize=(ancho, alto))
    fig.patch.set_facecolor(t["surface"])
    ax.set_facecolor(t["surface"])
    ax.grid(True, color=t["grid"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(t["grid"])
    ax.tick_params(colors=t["ink2"], labelsize=9.5)
    return fig, ax


def _sombrear_no_cuantitativo(ax, t: dict, x0: int, texto: bool = True) -> None:
    """Marca la era Landsat-5/7, donde la serie es indicativa y no cuantitativa."""
    ax.axvspan(x0, ANIO_CUANTITATIVO, color=t["ink2"], alpha=0.07, zorder=0, lw=0)
    if texto:
        ax.text((x0 + ANIO_CUANTITATIVO) / 2, ax.get_ylim()[1] * 0.96,
                "Landsat 5/7: la sal satura el sensor\ny el dato se pierde — serie indicativa",
                ha="center", va="top", fontsize=8, color=t["ink2"], style="italic")


def _etiqueta_final(ax, x, y, texto, color, t, dy=0.0, ancho_x=1.0):
    """Marca de color al final de la línea + texto en tinta (no en el color de la serie).

    Si la etiqueta se corrió para no pisarse con otra, va una línea guía en el color
    de la serie: con dos salares terminando en 9,0 y 9,2 km², los puntos se
    superponen y sin guía no se sabe cuál etiqueta corresponde a cuál.
    """
    ax.plot([x], [y], "o", color=color, markersize=6, zorder=5,
            markeredgecolor=t["surface"], markeredgewidth=1.5)
    x_txt = x + ancho_x
    if abs(dy) > 1e-9:
        ax.plot([x, x_txt], [y, y + dy], color=color, linewidth=0.9,
                alpha=0.75, zorder=4, solid_capstyle="round")
    ax.annotate(f" {texto}", (x_txt, y + dy), color=t["ink"], fontsize=9,
                va="center", ha="left", zorder=5)


def fig_series(datos: list[dict], modo: str) -> Path:
    """Superficie de piletas por salar. Una línea por salar, etiquetada al final."""
    t = TEMA[modo]
    fig, ax = _figura(t)

    xmax = 0
    for r in datos:
        salar = r["salar"]
        col = aoi.SALARES[salar][t["color"]]
        s = [(f["anio"], f["piletas_km2"]) for f in _cerrados(r["serie"])]
        if not s:
            continue
        xs, ys = zip(*s)
        ax.plot(xs, ys, color=col, linewidth=2.0, zorder=3,
                solid_capstyle="round")
        xmax = max(xmax, max(xs))

    ax.set_ylim(bottom=0)
    _sombrear_no_cuantitativo(ax, t, min(f["anio"] for r in datos for f in _cerrados(r["serie"])))

    # Etiquetas al final, empujadas hacia abajo desde la más alta para que no se
    # pisen. Empujar hacia arriba acumula y termina mandando etiquetas al techo.
    finales = sorted(((_cerrados(r["serie"])[-1]["piletas_km2"], r)
                      for r in datos if _cerrados(r["serie"])), reverse=True)
    paso = ax.get_ylim()[1] * 0.06
    previo = None
    for y, r in finales:
        yy = y if previo is None else min(y, previo - paso)
        previo = yy
        nombre = (aoi.SALARES[r["salar"]]["nombre"]
                  .replace("Salar del ", "").replace("Salar de ", "")
                  .replace("Salar ", "").replace(" (sector piletas)", ""))
        _etiqueta_final(ax, _cerrados(r["serie"])[-1]["anio"], y, nombre,
                        aoi.SALARES[r["salar"]][t["color"]], t, dy=yy - y,
                        ancho_x=(xmax - ax.get_xlim()[0]) * 0.035)

    ax.set_xlim(right=xmax + (xmax - ax.get_xlim()[0]) * 0.28)
    ax.set_ylabel("Superficie de piletas (km²)", color=t["ink2"], fontsize=10)
    ax.set_title("Expansión de las piletas de evaporación de litio", color=t["ink"],
                 fontsize=13.5, pad=30, loc="left", weight="medium")
    ax.text(0, 1.02, "Superficie que pasó a estar permanentemente inundada y no lo estaba "
            "antes de la operación", transform=ax.transAxes,
            color=t["ink2"], fontsize=9.5, ha="left", va="bottom")
    fig.text(0.125, 0.005, "Landsat 5/7/8/9 (Collection-2 L2) vía Microsoft Planetary Computer · "
             "elaboración propia", color=t["ink2"], fontsize=8, ha="left")

    out = ASSETS / f"piletas_series_{modo}.png"
    fig.savefig(out, dpi=300, facecolor=t["surface"], bbox_inches="tight")
    plt.close(fig)
    return out


def fig_clima_vs_operacion(datos: list[dict], salar: str, modo: str) -> Path | None:
    """Las tres superficies del salar: la que hizo el hombre y las dos que hace el clima."""
    r = next((d for d in datos if d["salar"] == salar), None)
    if not r or not r["serie"]:
        return None
    t = TEMA[modo]
    fig, ax = _figura(t)

    cerr = _cerrados(r["serie"])
    xs = [f["anio"] for f in cerr]
    capas = [
        ("piletas_km2", "Piletas de evaporación", "#2a78d6" if modo == "claro" else "#3987e5"),
        ("agua_natural_permanente_km2", "Agua natural permanente",
         "#eb6834" if modo == "claro" else "#d95926"),
        ("agua_estacional_km2", "Agua estacional", "#1baf7a" if modo == "claro" else "#199e70"),
    ]
    for clave, etq, col in capas:
        ax.plot(xs, [f[clave] for f in cerr], color=col, linewidth=2.0, zorder=3,
                solid_capstyle="round", label=etq)

    ax.set_ylim(bottom=0)
    _sombrear_no_cuantitativo(ax, t, min(xs), texto=False)
    for _, anio in aoi.SALARES[salar]["operaciones"]:
        if min(xs) <= anio <= max(xs):
            ax.axvline(anio, color=t["ink2"], linewidth=1.0, linestyle=":", zorder=2)
            ax.text(anio, ax.get_ylim()[1] * 0.98, f" arranca {anio}", rotation=90,
                    va="top", ha="left", fontsize=8, color=t["ink2"])

    leg = ax.legend(frameon=False, fontsize=9.5, loc="upper left", labelcolor=t["ink"])
    for h in leg.legend_handles:
        h.set_linewidth(2.5)

    ax.set_ylabel("Superficie (km²)", color=t["ink2"], fontsize=10)
    ax.set_title(f"{aoi.SALARES[salar]['nombre']}: lo que decide el operador y lo que decide el clima",
                 color=t["ink"], fontsize=13.5, pad=14, loc="left", weight="medium")
    fig.text(0.125, 0.02, "El agua estacional sube y baja con las lluvias; las piletas solo crecen. "
             "Separarlas es todo el método.", color=t["ink2"], fontsize=8, ha="left")

    out = ASSETS / f"clima_vs_operacion_{salar}_{modo}.png"
    fig.savefig(out, dpi=300, facecolor=t["surface"], bbox_inches="tight")
    plt.close(fig)
    return out


def fig_anio_aparicion(salar: str, modo: str) -> Path | None:
    """Mapa: en qué año cada píxel se volvió pileta. Rampa secuencial de un solo tono."""
    tif = CACHE / salar / "piletas_anio.tif"
    if not tif.exists():
        return None
    t = TEMA[modo]
    with rasterio.open(tif) as ds:
        a = ds.read(1)
    if not np.isfinite(a).any():
        return None

    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    fig.patch.set_facecolor(t["surface"])
    ax.set_facecolor(t["surface"])
    # Rampa secuencial azul 100→700 de la paleta de referencia: claro = viejo, oscuro = nuevo.
    from matplotlib.colors import LinearSegmentedColormap
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = LinearSegmentedColormap.from_list("azules", ramp)
    im = ax.imshow(a, cmap=cmap)
    ax.axis("off")

    cb = fig.colorbar(im, ax=ax, shrink=0.55, pad=0.02)
    cb.set_label("Año en que apareció la pileta", color=t["ink2"], fontsize=10)
    cb.ax.tick_params(colors=t["ink2"], labelsize=9)
    cb.outline.set_visible(False)

    ax.set_title(f"{aoi.SALARES[salar]['nombre']}: historia de la expansión en un solo mapa",
                 color=t["ink"], fontsize=13, pad=12, loc="left", weight="medium")
    out = ASSETS / f"anio_aparicion_{salar}_{modo}.png"
    fig.savefig(out, dpi=300, facecolor=t["surface"], bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["claro", "oscuro", "ambos"], default="ambos")
    args = ap.parse_args()

    f = DATOS / "piletas.json"
    if not f.exists():
        sys.exit("falta docs/data/piletas.json — corré antes 02_piletas.py")
    datos = json.loads(f.read_text())["data"]
    ASSETS.mkdir(parents=True, exist_ok=True)

    modos = ["claro", "oscuro"] if args.modo == "ambos" else [args.modo]
    for modo in modos:
        hechas = [fig_series(datos, modo)]
        for salar in ("hombre_muerto", "atacama"):
            hechas += [fig_clima_vs_operacion(datos, salar, modo),
                       fig_anio_aparicion(salar, modo)]
        for p in filter(None, hechas):
            print(f"  {p.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
