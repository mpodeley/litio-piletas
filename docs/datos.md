# Datos y fuentes

Todo lo de este sitio sale de archivos públicos. Ninguna fuente requiere pagar, y
solo una requiere registrarse.

---

## Imágenes

| Fuente | Qué aporta | Período | Acceso |
|---|---|---|---|
| **Landsat 4/5/7/8/9 Collection-2 nivel 2** | Serie de superficie de agua y NDVI | 1985–2026 | [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) (STAC, sin credenciales) |
| **Sentinel-2 L2A** | Detalle a 10 m del estado actual | 2016–2026 | Planetary Computer / [Copernicus Data Space](https://dataspace.copernicus.eu/) |
| **Sentinel-1 SLC** | Interferometría (caso 2) | 2014–2026 | [ASF DAAC](https://search.asf.alaska.edu/) + procesamiento HyP3 |
| **ERA5** | Corrección troposférica del InSAR | — | [Copernicus CDS](https://cds.climate.copernicus.eu/) (registro gratuito) |

Volumen disponible sobre los salares del caso, con menos de 15 % de nubes:

| Salar | Escenas Landsat | Escenas Sentinel-2 |
|---|---|---|
| Hombre Muerto | 2.233 (1985–2026) | 1.510 (2016–2026) |
| Atacama | 2.386 (1985–2026) | 1.070 (2016–2026) |

## Vectores y referencia

| Fuente | Qué aporta |
|---|---|
| **OpenStreetMap** (Overpass) | Poligonales de piletas, industria y lagunas naturales. 388 `landuse=salt_pond` en Atacama; ninguna en los salares argentinos. |
| **Nominatim** | Bounding box de los salares por nombre |
| **Copernicus DEM GLO-30** | Elevación, desde bucket abierto de AWS |

## Producción declarada

`docs/data/produccion_litio.csv` — producción de Fénix en toneladas de LCE,
armada con reportes de Livent y Arcadium. **Seis años, ninguno verificado contra
fuente primaria**, y así está marcado en el propio archivo (columna `verificado`).
Alcanza para un cruce ilustrativo, no para una conclusión.

Para ampliarla harían falta: Secretaría de Minería e INDEC (exportaciones
argentinas), y los reportes anuales de SQM y Albemarle para Atacama.

---

## Reproducir

```bash
git clone https://github.com/mpodeley/litio-satelital
cd litio-satelital
mamba env create -f pipeline/environment.yml && conda activate litio-sat

cd pipeline
python overlay_osm.py                  # poligonales de referencia
python 01_composites.py --todos        # compuestos anuales (varias horas)
python 02_piletas.py --todos           # clasificación y series
python 03_agua_vegas.py --todos        # vegas y bofedales
python 05_figuras.py                   # PNGs a 300 dpi
python 06_mapas.py --todos             # mapas interactivos
```

`01_composites.py` es **idempotente**: cachea cada año en `_data/` y volver a
correrlo no recomputa nada. Se puede cortar y retomar sin perder trabajo.

El caché ronda los 15 GB y está fuera del repo. Los productos derivados —las
series en JSON, las figuras y los mapas— sí están versionados, así que el sitio se
reconstruye sin bajar una sola escena.

Para publicar:

```bash
mkdocs gh-deploy      # construye y empuja a la rama gh-pages
```

El workflow de GitHub Actions no está en el repo porque el token disponible no
tiene scope `workflow` y GitHub rechaza el push de archivos bajo
`.github/workflows/`. Con `mkdocs gh-deploy` alcanza el scope `repo`.

## Salidas

| Archivo | Contenido |
|---|---|
| `docs/data/piletas.json` | Series anuales por salar: piletas, agua natural permanente, estacional, banda de sensibilidad, validación |
| `docs/data/vegas.json` | Extensión e intensidad de vegas por salar, con tendencias |
| `_data/<salar>/<año>.tif` | Compuesto anual: wetfreq, n_obs, NDVI medio, NDVI máximo |
| `_data/<salar>/piletas_anio.tif` | Año en que cada píxel se volvió pileta |

Cada JSON lleva envoltorio con `generated_at`, `source` y `metodo`, así que un
número siempre se puede rastrear hasta cómo se calculó.
