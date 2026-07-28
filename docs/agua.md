# Caso 1b — Agua natural, vegas y bofedales

La pregunta que aparece siempre que se habla de litio en la Puna es si la
operación se está llevando el agua. Es la pregunta correcta, y es también la más
fácil de contestar mal desde un satélite.

---

## Por qué la coincidencia no alcanza

Se puede medir que las vegas retrocedieron y que las piletas crecieron en el mismo
período. **Eso no prueba nada sobre causalidad.** En la Puna compiten al menos tres
explicaciones para la retracción de un bofedal:

- extracción de agua industrial (la operación),
- variabilidad de la precipitación andina, que es enorme entre años,
- pastoreo.

Un gráfico con las dos curvas superpuestas es visualmente convincente y
argumentalmente vacío. Si se muestra sin más, se está haciendo trampa.

## El diseño que sí aporta algo

Lo único que el satélite puede resolver acá es un **contraste entre salares**. Si
la vegetación se retrae igual en un salar con operación grande y en uno casi
virgen, el driver dominante es regional y no la operación.

Por eso el conjunto incluye salares en etapas muy distintas:

| Salar | Estado de la operación | Rol en el contraste |
|---|---|---|
| Atacama (Chile) | Produce desde 1984 | Operación madura, cuatro décadas |
| Hombre Muerto | Produce desde 1997 | Operación madura argentina |
| Olaroz-Cauchari | Produce desde 2015 / 2023 | Intermedia: dos operaciones de distinta edad en la misma cuenca |
| Centenario-Ratones | Produce desde fines de 2024 | Prácticamente sin historia |
| Rincón | **Sin producción comercial** | **Control negativo** |

Rincón es la pieza clave del diseño, y conviene ser preciso sobre por qué. El
informe de la Secretaría de Minería de junio de 2025 lista **seis** proyectos
argentinos en producción, y el Rincón no es ninguno de ellos: aparece en
Construcción (Argosy Minerals) y en Factibilidad (Rio Tinto). Lo que hay en el
terreno es una planta piloto.

Eso lo convierte en la prueba que el método puede fallar. Si en el Rincón
aparecen piletas al mismo ritmo que en un salar que sí opera, entonces lo que se
está midiendo no son piletas. Y si sus vegas se retraen igual que las de Hombre
Muerto y Atacama, el driver es el clima y no la operación.

## Cómo se mide

A 4.000 m de altura cualquier píxel con NDVI apreciable es vega o bofedal — no hay
otra vegetación posible. Alcanza un umbral simple, sin clasificador.

Se miden dos cosas distintas:

- **Extensión** — superficie con NDVI máximo anual por encima de 0,15.
- **Intensidad** — NDVI medio sobre el conjunto de píxeles que fueron vega en al
  menos la mitad de los años. Es más sensible que la extensión: un bofedal
  estresado pierde vigor antes que superficie.

Se usa el NDVI **máximo** del año y no el medio, porque la vega se ve en el pico
de la temporada húmeda; promediar con los meses secos la diluye.

## Resultado: lo contrario de lo esperado

| Salar | Operación | Piletas (km²) | Vega estable (km²) | **Tendencia NDVI/año** |
|---|---|---|---|---|
| Hombre Muerto | desde 1997 | 9,0 | 13,3 | **+0,00088** |
| Atacama | desde 1984 | 30,3 | 15,8 | **+0,00085** |
| Olaroz-Cauchari | desde 2015 | 9,2 | 170,0 | **+0,00064** |
| Centenario-Ratones | desde fines 2024 | 0,0 | 15,7 | **+0,00140** |
| **Rincón** | **sin producción comercial** | 0,4 | 23,4 | **−0,00107** |

**El único salar donde la vegetación retrocede es el único que no tiene operación
comercial.** Los cuatro que producen —incluido Atacama, con cuatro décadas y el
triple de piletas que cualquier salar argentino— tienen tendencia positiva.

Eso no confirma la hipótesis de que la extracción de litio seca las vegas. La
contradice, al menos en la forma simple en que suele plantearse.

!!! warning "Qué significa y qué no"
    **No** significa que la minería de litio no tenga impacto hídrico. Significa
    que **la extensión y el vigor de las vegas, medidos desde el satélite, no
    ordenan a los salares por intensidad de operación**. Si hubiera un efecto
    dominante y de gran escala, debería verse acá y no se ve.

    Las tendencias además son chicas —del orden de 10⁻³ de NDVI por año— y las
    superficies de vega no son comparables entre salares: Olaroz-Cauchari tiene
    170 km² de vega estable y Hombre Muerto 13. Son cuencas distintas.

    Un efecto local, acotado a los alrededores inmediatos de un campo de pozos,
    podría existir y quedar diluido en un promedio de cuenca. Esto no lo descarta.

Este es exactamente el tipo de resultado que se publica igual. El diseño
comparativo se armó para poder fallar, y falló en la dirección opuesta a la
esperada: eso es información.

!!! danger "Lo que este análisis no puede decir"
    No mide caudal, no mide agua subterránea —GRACE-FO tiene 300 km de resolución,
    inútil a escala de salar— y no dice si alguien incumple una normativa. Mide
    superficie de vegetación y su vigor, nada más.
