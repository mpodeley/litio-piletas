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

| Salar | Arranque de la operación | Rol en el contraste |
|---|---|---|
| Atacama (Chile) | 1984 | Operación madura, cuatro décadas |
| Hombre Muerto | 1997 | Operación madura argentina |
| Olaroz-Cauchari | 2015 / 2023 | Intermedia, dos operaciones de distinta edad en la misma cuenca |
| Rincón | 2022 | Reciente |
| Centenario-Ratones | 2024 | Prácticamente sin historia — **control negativo natural** |

Rincón y Centenario son la clave del diseño: si sus vegas se comportan igual que
las de Hombre Muerto y Atacama, el clima explica lo que se ve.

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

## Resultado

Se reporta la tendencia de ambas métricas por salar, y el contraste entre ellos.
**Se publica igual si da nulo**: que no se detecte impacto atribuible es un
resultado, y probablemente el más honesto que el dato admite.

!!! info "Estado"
    Las series de vegas se calculan con `pipeline/03_agua_vegas.py` sobre los
    mismos compuestos anuales del caso 1, así que salen del mismo dato y con la
    misma máscara. Los resultados se publican junto con las tendencias por salar.

!!! danger "Lo que este análisis no puede decir"
    No mide caudal, no mide agua subterránea —GRACE-FO tiene 300 km de resolución,
    inútil a escala de salar— y no dice si alguien incumple una normativa. Mide
    superficie de vegetación y su vigor, nada más.
