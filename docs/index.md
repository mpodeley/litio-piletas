# Litio desde el espacio

Una operación de litio es, vista desde arriba, un objeto que cambia: piletas que
aparecen y se multiplican, lagunas que crecen o se retraen, terreno que se mueve
unos milímetros por año. Todo eso lo registran satélites públicos, gratis, con
archivo de cuatro décadas.

!!! info "Demo comercial"
    [Litio desde el espacio](https://podeley.github.io/sat-litio/) — `podeley/sat-litio`.
    Este sitio es el trabajo de fondo; la demo es la versión de una página para cliente.

Este sitio recorre **qué se puede medir de verdad** — y, con el mismo cuidado, qué
no. Primero el panorama de técnicas y sensores. Después dos casos trabajados de
punta a punta, con los datos y el código a la vista.

!!! note "Cómo leer esto"
    Cada resultado va con su límite al lado. Cuando una medición no alcanza para
    sostener una afirmación, lo dice. Un resultado nulo o una señal chica se
    publican igual: si no, el resto no es creíble.

---

## Qué se puede mirar, y con qué

### Salares de salmuera

| Qué se mide | Cómo | Sensor | Resolución | Estado acá |
|---|---|---|---|---|
| **Expansión de piletas de evaporación** | Frecuencia anual de inundación contra línea de base | Landsat 5/7/8/9 | 30 m | ✅ [Caso 1](piletas.md) |
| **Agua natural y estacionalidad** | Índices de agua sobre serie larga | Landsat, Sentinel-2 | 10–30 m | ✅ [Caso 1b](agua.md) |
| **Vegas y bofedales** | NDVI en el anillo periférico | Sentinel-2 | 10 m | ✅ [Caso 1b](agua.md) |
| **Respuesta del salar a la extracción** | InSAR / SBAS | Sentinel-1 (banda C) | 80 m | ✅ [Caso 2](subsidencia.md) — sirve sobre halita seca, no sobre salar con arcilla |
| **Concentración de salmuera por color** | Reflectancia por pileta a lo largo de la cadena | Sentinel-2 | 10 m | Factible, no hecho |
| **Mineralogía de la costra** | Cocientes de bandas SWIR+TIR, SAM | ASTER, EMIT, PRISMA | 15–60 m | Factible[^1] |
| **Balance hídrico regional** | Nieve, precipitación, masa de agua | MODIS, IMERG, GRACE-FO | 500 m – 300 km | Factible |
| **Nivel de lagunas** | Altimetría | ICESat-2, Sentinel-3 | Traza | Factible |

[^1]: El motor espectral ya existe, aplicado a alteración hidrotermal en
    [Rinconada](https://mpodeley.github.io/rinconada-espectrometria/) y
    [San Juan](https://mpodeley.github.io/sanjuan-espectrometria/). Reapuntarlo a
    facies evaporíticas es trabajo de días, no de meses.

### Litio en roca dura (pegmatitas)

| Qué se mide | Cómo | Sensor | Nota |
|---|---|---|---|
| **Targeting de pegmatitas LCT** | Discriminación de micas de litio | EMIT, PRISMA, EnMAP | La lepidolita corre su absorción Al-OH a ~2.19 µm contra 2.20 de la moscovita: es una diferencia chica pero real, y necesita hiperespectral. Con ASTER no se separa. |
| **Control estructural** | Lineamientos sobre DEM | Copernicus GLO-30 | Gratis, sin registro |
| **Volumen movido** | Diferencia de DEMs | SRTM 2000 vs GLO-30 vs estéreo ASTER | Método ya validado en [Veladero](https://mpodeley.github.io/mineria-dem/) |

---

## Los dos casos

<div class="grid cards" markdown>

- :material-water: **[Piletas y agua](piletas.md)**

    Cuánta superficie sumaron las operaciones de litio, salar por salar, y cómo
    se separa eso de lo que hace la lluvia. Landsat sobre los salares argentinos,
    con Atacama de referencia.

- :material-arrow-collapse-vertical: **[Subsidencia del salar](subsidencia.md)**

    Si el bombeo deja huella medible en la superficie. Dos salares, mismo sensor y
    mismo procesamiento: en Hombre Muerto hay señal —chica, en el piso de ruido—;
    en Cauchari-Olaroz la banda C no aguanta la superficie y el resultado es nulo.
    Una medición publicada sobre ese salar no se reproduce.

</div>

---

## Por qué esto se puede hacer sin pedirle permiso a nadie

Todo lo de acá sale de archivos públicos y sin credenciales:

- **Landsat 1985→hoy** y **Sentinel-2 2016→hoy**, vía el catálogo STAC de Microsoft
  Planetary Computer. Sobre el Salar del Hombre Muerto hay 2,233 escenas Landsat
  con menos de 15% de nubes; sobre Atacama, 2,386.
- **Sentinel-1** vía ASF, con interferogramas procesados en la nube de HyP3.
- **Modelos de elevación** Copernicus GLO-30 desde un bucket abierto de AWS.
- **Poligonales** de piletas e infraestructura desde OpenStreetMap.

Eso significa que una operación se puede auditar desde afuera. No reemplaza el
trabajo de campo, pero acota mucho dónde conviene gastarlo — y permite verificar
lo que se declara.
