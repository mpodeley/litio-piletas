# Método

Cómo se pasa de un archivo de escenas Landsat a una cifra de superficie de
piletas, y por qué cada decisión está donde está. Los dos problemas de fondo se
descubrieron mirando los datos, no antes.

---

## 1. Frecuencia de agua, no una escena

Una escena suelta no distingue una pileta de evaporación de una laguna natural:
las dos dan índice de agua alto. Lo que las separa es la **persistencia**.

Por cada salar y cada año se calcula, píxel por píxel:

$$
\text{wetfreq} = \frac{\text{observaciones con agua}}{\text{observaciones válidas}}
$$

Una pileta operada está bajo salmuera todo el año y da wetfreq ≈ 1. Una laguna
natural se llena y se seca con la estación, y da 0,2–0,6. Como es un cociente
sobre observaciones válidas, además tolera los huecos del SLC-off de Landsat-7 y
la cobertura parcial de escena.

**Hasta dos escenas por mes**, las menos nubladas. No es por velocidad: si se
toman todas las disponibles, los meses despejados (invierno seco) pesan más que
los nublados (verano húmedo), y entonces las lagunas naturales —que se llenan
justo en verano— quedan subestimadas de forma sistemática.

## 2. Agua es MNDWI alto **y** NIR bajo

El índice de agua habitual sobre un salar falla, porque la nieve y la costra de
sal seca dan MNDWI alto igual que el agua: las tres son brillantes en verde y
oscuras en SWIR. Lo que las separa es el infrarrojo cercano.

| Superficie | MNDWI | NIR |
|---|---|---|
| Salmuera / agua | alto | **< 0,15** |
| Nieve | alto | 0,4–0,8 |
| Costra de sal seca | alto | alta |

Por eso el criterio es `MNDWI > 0,15` **y** `NIR < 0,25`. El corte deja pasar
salmuera turbia y concentrada sin dejar entrar nieve.

## 3. No confiar en las banderas de nube sobre sal

La máscara de calidad de Landsat (CFMask) se equivoca de forma sistemática sobre
un salar: la costra es blanca y fría, y la marca como nube o como nieve casi
siempre. Con la máscara estricta, el interior del salar quedaba con menos de seis
observaciones válidas por año —**323 km² en 2005**— mientras los cerros de
alrededor tenían veinte. El contorno del salar aparecía calcado en el mapa de
observaciones, que es la firma inconfundible del problema.

Se descartan solo relleno, nube confirmada y sombra de nube. La nieve se maneja
por física, con el criterio del NIR.

## 4. Pileta = superficie **agregada**, no superficie mojada

Umbralar wetfreq y nada más cuenta como pileta la costra que ya estaba mojada
antes de que existiera la operación. Sobre Hombre Muerto en 2024 eso da **73,6 km²**,
bastante más que las piletas reales.

Una pileta no es "superficie mojada": es superficie que **pasó a estar mojada de
forma permanente y antes no lo estaba**.

```
pileta(año) = wetfreq(año) ≥ 0,80   Y   wetfreq_base < 0,20
```

El agua natural permanente estaba mojada también en la base, así que queda afuera
por construcción y no por elección de umbral. Y lo que se mide pasa a ser una
cantidad con sentido físico: superficie inundada agregada desde la línea de base.

### La línea de base se arma con los años secos

No alcanza con promediar los primeros años. La superficie húmeda natural del salar
varía muchísimo: en Hombre Muerto, 1987 y 1993 inundan unos 60 km² y 1998 casi
nada. Si la base incluye años húmedos, queda alta justo en el centro-sur del
salar — que es exactamente donde después se construyen las piletas, porque ahí la
salmuera está somera. Resultado: se descuentan piletas reales.

Por eso la base son los **años secos** previos a la operación. Lo que sigue mojado
hasta en un año seco es agua natural permanente de verdad.

## 5. Filtros de forma y de confianza

- **Limpieza morfológica** (apertura y cierre) y descarte de cuerpos menores a
  1,8 ha: las piletas son cuerpos grandes y compactos.
- **Mínimo de diez observaciones** por píxel y año. Con pocas pasadas la
  frecuencia está sesgada *hacia arriba*: con cuatro observaciones, wetfreq solo
  puede valer 0, 0,25, 0,5, 0,75 o 1, y llegar a 1 es fácil. Los píxeles peor
  observados son justo los que más se cuelan como "agua permanente".
- **Persistencia de dos años** para el mapa de año de aparición: una inundación
  puntual no cuenta como nacimiento de una pileta.

## 6. Qué se publica al lado de cada cifra

- **Banda de sensibilidad**: la misma superficie recalculada cortando en 0,65,
  0,75 y 0,85, para que se vea cuánto del resultado depende de dónde se corta.
- **Cota superior**: la superficie permanentemente mojada sin descontar la
  natural. La cifra real está entre las dos.
- **Rectangularidad**: qué fracción del área detectada cae en cuerpos que llenan
  su caja envolvente. Una pileta es un rectángulo; una laguna, no.
- **Marca de año cuantitativo**: si menos del 60 % del AOI llegó a diez
  observaciones, el año se reporta pero no se usa para conclusiones
  (ver [Límites](limites.md)).

---

## Validación

**Referencia positiva.** OpenStreetMap tiene **388 poligonales `landuse=salt_pond`**
sobre el Salar de Atacama: piletas de evaporación digitalizadas por terceros. Se
mide precisión, recall e IoU contra eso. Hombre Muerto **no** las tiene mapeadas
—solo la huella de la concesión y la mina de boratos de Tincalayu—, así que ahí la
validación cuantitativa contra OSM no corresponde y no se hace.

**Control negativo.** Las 95 lagunas naturales con nombre de Atacama (Chaxa,
Barros Negros, Burro Muerto) no tendrían que caer dentro de la máscara de piletas.
La fracción que sí cae es una medida directa de contaminación del método.

**Criterio temporal.** En Hombre Muerto la superficie de piletas tiene que ser
prácticamente nula antes de 1997, cuando arrancó Fénix. Es una prueba que el
método puede fallar, y por eso sirve.

**Coherencia cruzada.** La serie de superficie natural debería correlacionar entre
salares —comparten el clima regional— y la de piletas no, porque depende de la
decisión de cada operador. Que se comporten distinto es evidencia de que las dos
clases están realmente separadas.
