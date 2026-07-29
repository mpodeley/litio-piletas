# Límites

Lo que este trabajo **no** puede sostener. Va acá y no en una nota al pie porque
condiciona cómo se lee todo lo demás.

---

## 1. La serie cuantitativa arranca en 2013, no en 1985

Es la limitación más importante y no estaba prevista.

**Landsat 5 y 7 se saturan sobre la costra de sal.** El salar es una de las
superficies más brillantes del planeta, y los sensores TM y ETM+ no tienen rango
dinámico para eso. El producto de nivel 2 marca esos píxeles como sin dato, así
que el interior del salar directamente no llega.

Medido sobre una región fija de piletas en el Salar del Hombre Muerto:

| Año | Observaciones válidas | % de píxeles con ≥10 | Sensor |
|---|---|---|---|
| 1986 | 0 | 15% | Landsat-5 |
| 1998 | 7 | 31% | Landsat-5 |
| 2005 | 10 | 53% | Landsat-5, 7 |
| 2010 | 5 | 15% | Landsat-5, 7 |
| 2016 | 15 | 89% | Landsat-7, 8 |
| 2024 | 19 | 100% | Landsat-8, 9 |

Landsat-8 (2013) trae 12 bits contra los 8 de sus antecesores, y ahí el problema
desaparece.

**Consecuencia práctica.** Las cifras de superficie se sostienen desde 2013. Los
años anteriores se muestran como contexto cualitativo —sirven para ver que el
salar estaba vacío antes de la operación— pero no para afirmar tasas de
crecimiento. Los años que no llegan al umbral de cobertura están marcados en los
datos con `cuantitativo: false`.

## 2. Superficie de piletas no es producción

El área es un proxy, y con varios eslabones flojos en el medio:

- La salmuera tarda **entre 12 y 24 meses** en recorrer la cadena de piletas, así
  que el área adelanta a la producción por un desfasaje que además cambia con la
  operación y con el clima.
- La productividad por hectárea depende de la concentración de la salmuera de cada
  salar, que varía en un factor grande entre Atacama y la Puna argentina.
- Las plantas de **extracción directa** (DLE) producen con mucha menos superficie
  de piletas. A medida que se adopten, la relación entre área y producción se
  rompe. Esto ya afecta a los proyectos nuevos.

## 3. No se puede atribuir causalidad sobre el agua

Se puede medir que las vegas retrocedieron y que las piletas crecieron en el
mismo período. **Eso no prueba que una cosa causó la otra.** En la Puna hay al
menos tres explicaciones que compiten: la extracción de agua industrial, la
variabilidad climática de la precipitación andina, y el pastoreo. Separarlas
necesita datos que no son satelitales.

Lo que sí aporta el satélite es la magnitud y la geometría del cambio, y descartar
hipótesis: si la retracción es igual en salares con y sin operación, la operación
no es el driver dominante.

## 4. El bbox de Centenario-Ratones no está verificado

OpenStreetMap no tiene ese salar por nombre, ni en Nominatim ni en Overpass. La
caja se armó con la ubicación publicada de la planta de Eramet y **está marcada
como no verificada** en los datos. Antes de citar su cifra hay que recortarla
contra imagen reciente.

## 5. Validación desigual entre salares

Solo Atacama tiene piletas digitalizadas en OpenStreetMap (388 poligonales). En
los salares argentinos la validación es temporal y visual, no cuantitativa. Una
métrica de precisión medida en Atacama **no se transfiere automáticamente** a
Hombre Muerto: la salmuera tiene otra concentración, otro color y otro contraste
contra la costra.

## 6. Sobre el caso InSAR

Los límites de la parte de subsidencia están en su propia página, pero el
principal se repite acá porque es fácil de pasar por alto: **la señal está en el
piso de ruido atmosférico** y el signo del movimiento no está confirmado. Es un
indicio sostenido en el tiempo, no una medición cerrada.
[Detalle](subsidencia.md#los-limites-sin-maquillar).

## 7. Lo que directamente no se midió

- **Volumen** de salmuera extraída. El satélite ve superficie, no caudal.
- **Química** de la salmuera. El color de las piletas se correlaciona con la
  concentración, pero acá no se calibró contra ningún análisis.
- **Agua subterránea.** GRACE-FO mide masa a ~300 km de resolución, demasiado
  grueso para un salar.
- **Cumplimiento normativo.** Este trabajo no dice si alguien incumple nada.
