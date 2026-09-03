# CLAUDE.md

Contexto del proyecto para Claude Code. Leer completo antes de tocar código.

---

## 1. Qué es esto

Proyecto #1 del curso **Teoría de la Computación (CC2019), Sección 30**,
Universidad del Valle de Guatemala. Docente: Tomás Gálvez P. Semestre 2, 2026.

Es la parte inicial de un **analizador léxico**: dado una expresión regular `r`
y una cadena `w`, el programa debe convertir la regex a postfix, construir un
AFN por Thompson, convertirlo a AFD por subconjuntos, minimizarlo con Hopcroft,
simular `w` sobre cada autómata y dibujarlos.

**Integrantes**

| Nombre | Carné |
|---|---|
| Jorge Morales | 24284 |
| Javier Castillo | 24014 |
| Diego Gonzales | 24170 |

La entrega es un **repositorio privado** en GitHub o BitBucket con la
documentación en una carpeta dedicada, más un video **no listado** en YouTube
de máximo 10 minutos explicando el programa y la documentación.

## 2. Ponderación

| Requerimiento | Puntos |
|---|---|
| Documentación requerida | 1 |
| Shunting Yard para infix a postfix | 2 |
| Generación de AFN con Thompson | 3 |
| Generación de AFD con subconjuntos | 3 |
| Minimización de AFD | 3 |
| Simulación de AFN y AFD | 3 |
| **Total** | **15** |
| Construcción directa de AFD (recuperación) | 3 |
| **Total con recuperación** | **18** |

La documentación debe especificar: diseño o arquitectura con los módulos
definidos y los protocolos de comunicación entre ellos, la definición de los
objetos que codifican AFDs y AFNs, y el enlace al video.

El enunciado también exige **determinar claramente el símbolo que se considera
ε** y agregar facilidades para procesar un archivo de texto con una expresión
regular por línea.

## 3. Historia: de dónde viene este código

El proyecto es explícitamente una recopilación de laboratorios previos. Hay dos
labs con código, y **estaban en lenguajes distintos**:

- **Laboratorio 3 — Python.** Shunting Yard, árbol sintáctico y construcción
  directa de AFD con `nullable`/`firstpos`/`lastpos`/`followpos`.
  Archivos: `ejercicio1.py`, `ejercicio2.py`.
- **Laboratorio 4 — Java.** Repo `https://github.com/JRGMRLS/LAB4_Teoria_Computacion`.
  Un solo `Main.java` de 1007 líneas con Shunting Yard, árbol, Thompson
  completo (símbolo, concatenación, unión, `*`, `+`, `?`), cerradura epsilon y
  simulación de AFN. Video del lab: `https://youtu.be/FuVmXfjNYxc`.

**Decisión tomada: todo el proyecto se hace en Python.** El código de Lab 3 que
se conserva es el más caro de reescribir, Hopcroft y subconjuntos salen mucho
más cortos con `set`/`frozenset`, y Graphviz desde Python es trivial. La lógica
de Thompson de `Main.java` se porta a Python.

### Estado de verificación de los labs

El código de **Lab 4 está correcto**. Se portó su lógica a Python y se corrió
sobre las cuatro expresiones del curso: postfix y aceptación salen bien en los
cuatro casos, incluyendo la cadena vacía. Su manejo de epsilon es correcto y
elegante: `&` se trata como un literal en `crearFragmentoLiteral`, lo que
genera una transición etiquetada `&` que la cerradura ya reconoce como epsilon.

El código de **Lab 3 tiene cuatro bugs conocidos**. Todos ya están corregidos o
neutralizados en el código nuevo, pero conviene tenerlos presentes si alguien
vuelve a consultar ese archivo:

1. **`ε` no se maneja como epsilon.** Se trata como un símbolo cualquiera, así
   que `((ε|a)|b*)*` exige el carácter `ε` en la cadena.
2. **El árbol nunca se aumenta con `#`.** La aceptación se decide con
   `max(posición)`, que solo funciona si la última posición es realmente el
   marcador final. Con `(a|b)*abb(a|b)*` da estados de aceptación incorrectos.
3. **Falta `followpos` para el operador `+`.** Solo se calcula en el caso
   KLEENE. Esto rompe `(a*|b*)+`, que es la primera expresión de prueba.
4. **`_should_pop_operator` compara enums contra strings** en
   `left_associative`, así que siempre entra por la rama de asociatividad
   derecha. No cambia el lenguaje reconocido, pero el postfix sale distinto.

Además, `Main.java` no maneja escapes con `\` (Lab 3 sí lo hacía) y guarda las
transiciones en una `List` plana que se recorre completa en cada consulta.

## 4. Decisiones de diseño ya tomadas

**No revertir estas sin razón fuerte.**

### Epsilon

Internamente epsilon es siempre `ε` (constante `EPSILON` en `tokens.py`). En la
entrada se aceptan **tanto `ε` como `&`** y ambos producen el mismo token: `ε`
es la notación del enunciado y `&` la que usó el Lab 4, así que los archivos de
prueba de ambos labs funcionan sin cambios.

Epsilon **no pertenece al alfabeto**: no consume entrada, no aparece como
columna en las tablas de transición del AFD y **no recibe número de posición**
en la construcción directa. Para el carácter literal se escribe `\ε`.

### El postfix es una lista de Token, no un string

Este es el cambio estructural más importante respecto a los labs, que ambos
devolvían `str`. Un símbolo escapado como `\*` ocupa dos caracteres, y en
representación de texto el constructor del árbol lo lee como dos cosas
distintas y confunde el símbolo con el operador. Con tokens, la decisión de si
un carácter es operador o símbolo se toma una sola vez, en el tokenizador.
Hay una prueba dedicada a esto (`test_simbolo_escapado_no_se_confunde_con_operador`).

### Transiciones en diccionarios anidados

`AFN.transiciones` es `dict[estado][símbolo] -> set[estado]` y
`AFD.transiciones` es `dict[estado][símbolo] -> estado`. No listas planas: la
construcción de subconjuntos consulta una vez por cada par (estado, símbolo) y
con lista eso se vuelve cuadrático.

### Operadores unarios en Shunting Yard

`*`, `+` y `?` se envían **directamente a la salida** en lugar de pasar por la
pila. Es correcto porque en infix un operador postfijo aparece inmediatamente
después de su operando, y ese operando —un símbolo o un grupo entre
paréntesis— ya fue emitido por completo cuando se llega al operador. Verificado
contra las cuatro expresiones del curso.

### Construcción de Thompson (Fase 2)

`analizador/thompson.py` recorre el árbol sintáctico de abajo hacia arriba.
Cada nodo produce un `_Fragmento` (AFN parcial + estado inicial + estado
final propios); los fragmentos se combinan y comparten un único contador
de estados (`itertools.count`) para que los números nunca se repitan entre
subárboles. Al final el AFN completo queda con `inicial`/`aceptacion`
tomados del fragmento raíz, y **un único estado de aceptación**, como pide
la construcción clásica de Thompson.

Reglas de los operadores unarios, portadas de `Main.java`:

- `*` — nuevo inicio y nuevo final; epsilon inicio→interno.inicio,
  interno.final→final, **y además** inicio→final (acepta vacía) e
  interno.final→interno.inicio (repite).
- `+` — igual que `*` pero **sin** la epsilon inicio→final: exige al menos
  una repetición.
- `?` — igual que `*` pero **sin** la epsilon interno.final→interno.inicio:
  no repite.

Detalle importante ya corregido una vez: el back-edge de la repetición sale
de `interno.final` (el final del fragmento hijo), **no** del nuevo estado
`final` del fragmento compuesto. Confundir esos dos estados rompe la
repetición silenciosamente (el AFN deja de aceptar `aa`, `aaa`, etc.) sin
que ningún otro chequeo lo detecte, así que si se vuelve a tocar este
archivo conviene revisar `test_kleene_acepta_vacia_y_repite` y
`test_plus_exige_al_menos_una_repeticion` en `tests/test_fase02.py`.

### Construcción de subconjuntos (Fase 3)

`analizador/subconjuntos.py` parte de `cerradura_epsilon({afn.inicial})` y
recorre en anchura: por cada subconjunto y cada símbolo calcula
`cerradura_epsilon(mover(T, a))`. Un estado del AFD es de aceptación si su
subconjunto contiene **algún** estado de aceptación del AFN.

Dos decisiones que conviene no revertir:

- **El AFD queda parcial a propósito.** Si `cerradura_epsilon(mover(T, a))`
  sale vacío no se crea estado ni transición; la simulación rechaza al no
  encontrar a dónde ir. El sumidero solo aparece cuando alguien llama
  `AFD.completar()`, que es lo que necesita Hopcroft. Así las tablas del
  reporte no se llenan de un estado basura que el enunciado no pide.
- **El alfabeto se fija de una vez** con el del AFN, aunque algún símbolo
  no llegue a usarse, para que la tabla de transiciones tenga una columna
  por símbolo de la expresión.

La numeración de estados es estable entre corridas (recorrido en anchura
con `deque` y símbolos ordenados). Esto importa porque las tablas y los
dibujos del reporte deben poder regenerarse idénticos; hay una prueba que
lo fija (`test_numeracion_estable_entre_corridas`).

`listado_de_estados(afd)` produce el "listado de estados y las posiciones
que conforma cada uno" que pide el enunciado, leyendo `AFD.origen`.

### Otras convenciones

- Nombres de código, comentarios y docstrings **en español**, consistente con
  los labs previos.
- Los espacios en blanco se ignoran; `\ ` para un espacio literal.
- `.` en la entrada es concatenación explícita; `\.` es el punto literal.
- El `AFD` guarda `origen: dict[estado, frozenset]`, que asocia cada estado con
  el conjunto del que salió (subconjunto de estados del AFN, o conjunto de
  posiciones en construcción directa). No participa en el reconocimiento, pero
  es lo que el enunciado pide mostrar como "listado de estados y las posiciones
  que conforma cada uno".
- `main.py` fuerza `sys.stdout.reconfigure(encoding="utf-8")` porque la
  consola de Windows suele venir en cp1252, que no puede imprimir `ε`, `├`,
  `└`, etc. Sin esto el driver truena con `UnicodeEncodeError` en Windows
  aunque las pruebas (que no imprimen a consola) pasen sin problema.

## 5. Estado actual

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Estructuras base: objetos `AFN` y `AFD` | **Completa** |
| 1 | Preprocesamiento, Shunting Yard, árbol sintáctico | **Completa** |
| 2 | Construcción de Thompson (regex → AFN) | **Completa** |
| 3 | Construcción de subconjuntos (AFN → AFD) | **Completa** |
| 4 | Minimización con Hopcroft | Pendiente |
| 5 | Simulación de AFN y AFD | Pendiente |
| 6 | Dibujo de autómatas | Pendiente |
| 7 | Procesamiento por lotes | Pendiente |
| 8 | Interfaz de usuario | Pendiente |
| 9 | Construcción directa de AFD (recuperación) | Pendiente |
| 10 | Pruebas | Parcial (54 pruebas, fases 0-3) |
| 11 | Documentación y video | Pendiente |

### Estructura

```
proyecto1_teoria_computacion/
├── analizador/
│   ├── errores.py          Excepciones. ErrorDeSintaxis señala la posición del error
│   ├── tokens.py           Fase 1a: tokenización, concatenación implícita, validación
│   ├── shunting_yard.py    Fase 1b: infix → postfix
│   ├── arbol.py            Fase 1c: árbol sintáctico y numeración de posiciones
│   ├── thompson.py         Fase 2: árbol sintáctico → AFN (construcción de Thompson)
│   ├── subconjuntos.py     Fase 3: AFN → AFD (construcción de subconjuntos)
│   └── automatas/
│       ├── afn.py          Fase 0: AFN con cerradura_epsilon, mover
│       └── afd.py          Fase 0: AFD con delta, completar, estados_alcanzables
├── tests/
│   ├── apoyo.py            Simulación de AFN/AFD y generación de cadenas (andamio)
│   ├── test_fase01.py      34 pruebas: tokens, shunting yard, árbol, AFN/AFD base
│   ├── test_fase02.py      9 pruebas: Thompson, incluyendo las 4 expresiones del curso
│   └── test_fase03.py      11 pruebas: subconjuntos y equivalencia AFN ↔ AFD
├── main.py                 Driver de demostración
├── expresiones.txt         Las cuatro expresiones del curso
└── README.md
```

Nota: hasta hace poco los módulos de `analizador/` estaban planos en la raíz
del proyecto (sin el paquete), lo cual rompía los imports relativos de
`afn.py`/`afd.py` (`from ..errores import ...`) y hacía fallar
`python -m unittest discover -s tests`. Ya se reorganizó al layout de arriba;
si algo vuelve a aparecer plano en la raíz es una regresión, no una variante
válida.

### Flujo de datos

```
texto → [tokens] → Token[] → [shunting_yard] → Token[] postfix → [arbol] → Nodo
                                                                            │
                                            ┌───────────────────────────────┴───┐
                                            ↓                                   ↓
                                    Thompson (Fase 2, completa)      Construcción directa (Fase 9)
                                            ↓                                   ↓
                                           AFN ── subconjuntos (Fase 3, ok) ──→ AFD
                                                                                ↓
                                                                       Hopcroft (Fase 4)
```

## 6. Comandos

```bash
python3 main.py                                  # usa expresiones.txt
python3 main.py otro_archivo.txt
python3 -m unittest discover -s tests -v         # 54 pruebas, todas pasando
```

Sin dependencias externas por ahora. Graphviz entra en la Fase 6 y requiere el
binario del sistema (no instalado todavía en la máquina de desarrollo), no
solo el paquete de Python.

## 7. Expresiones de prueba y resultados esperados

Las cuatro expresiones aparecen idénticas en Lab 3, Lab 4 y el proyecto. El
postfix actual coincide con el que produjo el Lab 4, lo cual da continuidad con
lo ya entregado:

```
(a*|b*)+          →  a*b*|+
((ε|a)|b*)*       →  εa|b*|*
(a|b)*abb(a|b)*   →  ab|*a.b.b.ab|*.
0?(1?)?0*         →  0?1??.0*.
```

Aceptación verificada con el AFN de Thompson ya implementado (`test_fase02.py`,
`test_expresiones_del_curso_aceptan_lo_esperado`):

| Expresión | Cadena | Acepta | Acepta `""` |
|---|---|---|---|
| `(a*\|b*)+` | `abba` | sí | sí |
| `((ε\|a)\|b*)*` | `abba` | sí | sí |
| `(a\|b)*abb(a\|b)*` | `aabbab` | sí | no |
| `0?(1?)?0*` | `0100` | sí | sí |

Posiciones esperadas: `(a|b)*abb(a|b)*` da 7 posiciones. `((ε|a)|b*)*` da solo
**2** (`a` y `b`), porque epsilon no ocupa posición.

Tamaños de los autómatas ya generados (útiles como referencia rápida para
detectar regresiones y para comparar contra el AFD mínimo de la Fase 4):

| Expresión | Estados AFN | Estados AFD | Nota |
|---|---|---|---|
| `(a*\|b*)+` | 12 | 3 | los 3 son de aceptación: el lenguaje es Σ* |
| `((ε\|a)\|b*)*` | 14 | 3 | también reconoce Σ* |
| `(a\|b)*abb(a\|b)*` | 22 | 9 | el AFD clásico del libro para `abb` |
| `0?(1?)?0*` | 14 | 4 | |

Que las dos primeras expresiones reconozcan Σ* no es un error: `a*` y `b*`
aceptan la cadena vacía, así que la unión bajo `+` (o bajo `*`) puede
descomponer cualquier cadena en bloques de `a`s y de `b`s.

## 8. Qué sigue y qué vigilar

**Detalle conocido del árbol.** `0?(1?)?0*` produce un nodo `?` anidado dentro
de otro `?`, porque así está escrita la expresión. Es correcto pero genera
estados redundantes en Thompson. No simplificar: alteraría el árbol que pide el
enunciado. Conviene mencionarlo en el video.

**Fase 4 (Hopcroft), lo que sigue.** Requiere el AFD completo; usar
`AFD.completar()`, que agrega estado sumidero `-1`. Conviene eliminar estados
inalcanzables antes de particionar (`AFD.estados_alcanzables()` ya existe).
Hay dos AFDs de referencia para comprobar que la minimización realmente
reduce y no rompe nada:

- `(a*|b*)+` genera un AFD de **3 estados, todos de aceptación**, que
  reconoce Σ*. Debe minimizar a **1 estado** con un bucle a sí mismo.
- `(a|b)*abb(a|b)*` genera el AFD clásico de **9 estados** (0-3 rastrean el
  progreso hacia `abb`, 4-8 son absorbentes de aceptación). Debe minimizar a
  **4**: `{0,2}`, `{1}`, `{3}` y `{4..8}` fundidos.

La prueba `test_completar_no_cambia_el_lenguaje` en `tests/test_fase03.py`
ya verifica que agregar el sumidero no altera el lenguaje, así que el punto
de partida de Hopcroft está cubierto.

**Fase 5 (Simulación).** Debe comparar los resultados de los cuatro autómatas
(AFN, AFD, AFD mínimo y, si se hace, AFD directo) y verificar que coincidan.
Es la mejor prueba de regresión que tiene el proyecto, y ya hay media hecha:
`tests/apoyo.py` tiene `acepta_afn`, `acepta_afd` y `cadenas_hasta`, y
`test_afn_y_afd_reconocen_el_mismo_lenguaje` compara AFN contra AFD sobre
todas las cadenas de longitud 0 a 5. La Fase 5 debe **promover esas
funciones a `analizador/simulacion.py`** (dejando de ser andamio de pruebas)
y extender la comparación al AFD mínimo.

**Fase 9 (Construcción directa).** Aumentar el árbol con `#` y usar su posición
para decidir aceptación — no `max(posición)`. Y calcular `followpos` para `+`,
no solo para `*`.

**Documentación.** El README ya tiene arquitectura, protocolos, definición de
los objetos y convenciones. La Fase 11 debe moverlo a una carpeta dedicada y
agregar el enlace al video nuevo.

**Control de versiones.** El repo local se inicializó con `git init` pero
todavía no tiene commits ni remoto. El enunciado exige un repositorio
**privado** en GitHub o BitBucket — falta crear el remoto y decidir si se
sube con el historial actual o se aplasta en un commit inicial.
