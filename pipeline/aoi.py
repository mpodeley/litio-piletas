"""AOIs de los salares de litio: piletas de evaporación, agua natural y vegas.

Los bbox salen de Nominatim/OSM (consultados el 28-jul-2026) salvo donde se indica
`verificado=False`. La convención es (oeste, sur, este, norte) en grados decimales.

Todos los salares caen en la faja UTM 19 sur (EPSG:32719). El pipeline trabaja en
UTM a 30 m, no en grados: así el píxel mide exactamente 900 m² y las áreas no
dependen de la latitud.

Por qué Landsat y no Sentinel-2 para la serie: la pregunta es la expansión de las
piletas desde antes de que hubiera operación, y Sentinel-2 arranca en 2016 — tarde
para eso. Landsat 5/7/8/9 comparten resolución (30 m) y bandas equivalentes, así
que la serie 1985→2026 es homogénea. Sentinel-2 se usa aparte, para el detalle a
10 m del estado actual.
"""

from __future__ import annotations

# Resolución de trabajo. Nativa de Landsat; el píxel mide 900 m² exactos.
RES_M = 30
UTM_EPSG = "EPSG:32719"
PIXEL_KM2 = (RES_M / 1000.0) ** 2  # 0.0009 km²

# Serie completa: Landsat 5 arranca en 1984, pero la cobertura sobre la Puna se
# vuelve regular recién en 1985.
ANIO_INICIO = 1985
ANIO_FIN = 2026

# Umbrales del método (ver docs/metodo.md)
# Umbral de agua, calibrado contra las 388 poligonales `landuse=salt_pond` de OSM
# sobre el Salar de Atacama (ver docs/metodo.md). Se probaron cinco criterios:
#
#   MNDWI>0.15 y NIR<0.25   recall 38.3%   falsos+ 5k
#   MNDWI>0.15 y NIR<0.45   recall 46.6%   falsos+ 74k
#   MNDWI>0.30 solo         recall 74.8%   falsos+ 58k   <- elegido
#   MNDWI>0.15 solo         recall 81.6%   falsos+ 195k
#
# La condición sobre el NIR estaba puesta para descartar nieve, pero descartaba
# la salmuera concentrada: en las piletas de Atacama el NIR es tan alto que
# directamente satura. Un umbral de MNDWI más exigente hace el mismo trabajo
# mejor. La nieve, que es transitoria, la filtra después la frecuencia anual:
# no nieva el 80% del año.
MNDWI_AGUA = 0.30
WETFREQ_PILETA = 0.80  # fracción del año bajo agua: pileta operada
WETFREQ_NATURAL = 0.20  # entre 0.20 y 0.80: superficie natural que respira con la estación

SALARES: dict[str, dict] = {
    "hombre_muerto": {
        "nombre": "Salar del Hombre Muerto",
        "jurisdiccion": "Catamarca / Salta, Argentina",
        "bbox": (-67.25, -25.55, -66.85, -25.15),
        "verificado": True,
        "operaciones": [
            ("Fénix (FMC → Livent → Arcadium → Rio Tinto)", 1997),
            ("Sal de Oro (POSCO)", 2024),
        ],
        # Capacidades declaradas (Secretaría de Minería, informe litio jun-2025):
        # Fénix ~60.000 Tn LCE con las ampliaciones proyectadas a 10 años;
        # Sal de Oro 25.000 Tn de hidróxido en operación (21.990 Tn LCE) + planta
        # de carbonato en construcción.
        "color": "#2a78d6",
        "color_oscuro": "#3987e5",
        "nota": "Donde ya está medido el InSAR. Fénix es la operación de salmuera "
                "más antigua de Argentina.",
    },
    "olaroz_cauchari": {
        "nombre": "Salar de Olaroz-Cauchari",
        "jurisdiccion": "Jujuy, Argentina",
        # Une los dos bbox de Nominatim (Olaroz -23.564..-23.382 / Cauchari
        # -23.835..-23.632) con margen para las piletas del borde.
        "bbox": (-66.86, -23.90, -66.58, -23.32),
        "verificado": True,
        "operaciones": [
            ("Olaroz (Sales de Jujuy — Allkem → Arcadium → Rio Tinto / Toyota Tsusho)", 2015),
            ("Cauchari-Olaroz (Exar — Ganfeng / Lithium Argentina / JEMSE)", 2023),
        ],
        # Capacidades: Olaroz ~43.000 Tn LCE proyectadas; Cauchari-Olaroz planta de
        # 40.000 Tn LCE, con piloto DLE anunciado (Secretaría de Minería, jun-2025).
        "color": "#1baf7a",
        "color_oscuro": "#199e70",
        "nota": "Dos operaciones de edades muy distintas en la misma cuenca: sirve "
                "para ver si la señal separa una de otra.",
    },
    "rincon": {
        "nombre": "Salar del Rincón",
        "jurisdiccion": "Salta, Argentina",
        "bbox": (-67.27, -24.26, -66.92, -23.86),
        "verificado": True,
        # OJO: el Rincón NO está entre los seis proyectos argentinos en producción.
        # El informe de la Secretaría de Minería (jun-2025) lo lista en dos entradas
        # y ninguna es operación comercial: "Rincón" (Argosy Minerals) en Construcción,
        # y "Salar del Rincón" (Rio Tinto) en Factibilidad. Lo que hay en el terreno es
        # una planta piloto. La fecha de abajo es el arranque del piloto, no de una
        # operación, y por eso este salar vale sobre todo como CONTROL NEGATIVO.
        "operaciones": [
            ("Rincón (Argosy, planta piloto — no comercial)", 2022),
        ],
        "color": "#eda100",
        "color_oscuro": "#c98500",
        "nota": "Sin producción comercial al 1er semestre de 2025. Es el control "
                "negativo: si acá aparecen piletas al mismo ritmo que en un salar que "
                "sí opera, el método está midiendo otra cosa.",
    },
    "centenario_ratones": {
        "nombre": "Salar Centenario-Ratones",
        "jurisdiccion": "Salta, Argentina",
        # OSM no tiene el salar por nombre (ni Nominatim ni Overpass lo devuelven).
        # Caja aproximada a partir de la ubicación publicada de la planta de Eramet.
        # PENDIENTE: recortar contra imagen Sentinel-2 reciente antes de publicar.
        "bbox": (-67.05, -25.15, -66.70, -24.80),
        "verificado": False,
        "operaciones": [
            ("Centenario (Eramet)", 2024),
        ],
        "color": "#e87ba4",
        "color_oscuro": "#d55181",
        "nota": "La más nueva de todas (2024). Bbox sin verificar contra OSM.",
    },
    "atacama": {
        "nombre": "Salar de Atacama (sector piletas)",
        "jurisdiccion": "Antofagasta, Chile",
        # El salar entero va de -23.786..-22.982 / -68.573..-68.064 (Nominatim),
        # pero las piletas de SQM y Albemarle están en el núcleo sur. Se recorta ahí:
        # el salar completo cuadruplicaría el cómputo sin agregar piletas.
        "bbox": (-68.45, -23.80, -68.05, -23.20),
        "verificado": True,
        "operaciones": [
            ("SQM (Salar)", 1984),
            ("Albemarle (ex Rockwood / SCL)", 1984),
        ],
        "color": "#eb6834",
        "color_oscuro": "#d95926",
        "nota": "Control maduro: opera desde los 80, así que la serie Landsat cubre "
                "casi toda su historia. Es la referencia contra la cual se leen los "
                "salares argentinos.",
    },
}


def bbox(salar: str) -> tuple[float, float, float, float]:
    """(oeste, sur, este, norte) en EPSG:4326."""
    return SALARES[salar]["bbox"]


def center_lonlat(salar: str) -> tuple[float, float]:
    w, s, e, n = bbox(salar)
    return ((w + e) / 2.0, (s + n) / 2.0)


def inicio_operacion(salar: str) -> int:
    """Año en que arrancó la primera operación. Antes de esto no debería haber piletas."""
    return min(anio for _, anio in SALARES[salar]["operaciones"])


def todos() -> list[str]:
    """Claves ordenadas por prioridad para la demo: primero los dos que sostienen el caso."""
    return ["hombre_muerto", "atacama", "olaroz_cauchari", "rincon", "centenario_ratones"]
