# Documentación de diseño

**Proyecto #1 — Analizador léxico**
Teoría de la Computación (CC2019), Sección 30
Universidad del Valle de Guatemala — Semestre 2, 2026
Docente: Tomás Gálvez P.

## Integrantes

| Nombre | Carné |
|---|---|
| Jorge Morales | 24284 |
| Javier Castillo | 24014 |
| Diego Gonzales | 24170 |

## Video

> **Pendiente:** agregar aquí el enlace al video no listado de YouTube
> (máximo 10 minutos) explicando el programa y esta documentación.

---

## 1. Qué hace el programa

Dada una expresión regular `r` y una cadena `w`, el programa:

1. Convierte `r` de notación infix a **postfix** con el algoritmo Shunting Yard.
2. Construye el **árbol sintáctico** de la expresión.
3. Genera un **AFN** por la construcción de Thompson.
4. Convierte el AFN en un **AFD** por la construcción de subconjuntos.
5. **Minimiza** el AFD con el algoritmo de Hopcroft.
6. **Simula** `w` sobre los tres autómatas y reporta si pertenece al lenguaje.

Acepta un archivo de texto con una expresión regular por línea y procesa todas
en una sola corrida.

## 2. Ejecución

Requiere únicamente Python 3. No tiene dependencias externas.

```bash
python3 main.py                                  # usa expresiones.txt
python3 main.py otro_archivo.txt                 # otro archivo de expresiones
python3 main.py expresiones.txt abba             # además simula w = "abba"
python3 main.py expresiones.txt ""               # simula la cadena vacía
python3 main.py --html                           # reporte HTML en salida/reporte.html
python3 main.py --salida reporte.html            # reporte en otra ruta
python3 -m unittest discover -s tests -v         # ejecuta las 109 pruebas
```

Para cada expresión el programa imprime la tokenización, el postfix, el árbol
sintáctico con sus posiciones numeradas, las tablas de transiciones del AFN, del
AFD y del AFD mínimo, el listado de estados con su subconjunto de origen y —si se
indicó una cadena— el resultado de la simulación en los tres autómatas.

### Reporte HTML

Con `--html` esa misma información se escribe como página web en lugar de
volcarse a la consola, con las tablas de transiciones como tablas reales y una
sección por expresión. El archivo es autocontenido —el CSS va incrustado y no
carga ningún recurso externo—, así que funciona sin conexión y se puede mover
o enviar solo.

El documento incluye reglas `@media print`, de modo que **abrirlo en el navegador
y usar Imprimir → Guardar como PDF** produce un PDF con una página por expresión.
Se optó por esta vía en lugar de generar el PDF directamente porque no agrega
ninguna dependencia al proyecto.

Con `--html` la consola solo muestra un resumen de una línea por expresión y la
ruta del archivo generado.

## 3. Arquitectura

El programa está organizado como una **tubería de transformaciones**: cada módulo
recibe la estructura que produjo el anterior y entrega la siguiente. Ningún módulo
conoce la representación interna de otro; se comunican solo a través de los objetos
descritos en la sección 4.

```
proyecto1_teoria_computacion/
├── analizador/
│   ├── errores.py          Excepciones del proyecto
│   ├── tokens.py           Tokenización, concatenación implícita, validación
│   ├── shunting_yard.py    Infix → postfix
│   ├── arbol.py            Postfix → árbol sintáctico
│   ├── thompson.py         Árbol sintáctico → AFN
│   ├── subconjuntos.py     AFN → AFD
│   ├── hopcroft.py         AFD → AFD mínimo
│   ├── simulacion.py       Simulación de AFN y AFD sobre una cadena
│   ├── reporte.py          Pipeline completo y generación del reporte HTML
│   └── automatas/
│       ├── afn.py          Objeto AFN
│       └── afd.py          Objeto AFD
├── docs/
│   └── DISEÑO.md           Este documento
├── tests/                  109 pruebas unitarias
├── main.py                 Interfaz de línea de comandos
└── expresiones.txt         Las cuatro expresiones del curso
```

### Responsabilidad de cada módulo

| Módulo | Entrada | Salida | Responsabilidad |
|---|---|---|---|
| `tokens` | `str` | `list[Token]` | Clasificar cada carácter, resolver escapes, insertar la concatenación implícita y validar la sintaxis |
| `shunting_yard` | `list[Token]` | `list[Token]` | Reordenar de infix a postfix respetando precedencias |
| `arbol` | `list[Token]` | `Nodo` | Armar el árbol sintáctico y numerar las posiciones de las hojas |
| `thompson` | `Nodo` | `AFN` | Construir el AFN combinando fragmentos |
| `subconjuntos` | `AFN` | `AFD` | Determinizar agrupando estados en subconjuntos |
| `hopcroft` | `AFD` | `AFD` | Fundir estados equivalentes |
| `simulacion` | `AFN`/`AFD` + `str` | `bool` | Decidir la pertenencia de la cadena al lenguaje |
| `reporte` | `str` | `Analisis` / HTML | Encadenar el pipeline y generar el reporte |
| `errores` | — | — | Excepciones comunes a todos los módulos |

## 4. Protocolos de comunicación entre módulos

Los módulos se comunican mediante cuatro estructuras. El flujo es:

```
texto ──[tokens]──► list[Token] ──[shunting_yard]──► list[Token] postfix
                                                              │
                                                        [arbol]│
                                                              ▼
                                                            Nodo
                                                              │
                                                       [thompson]
                                                              ▼
                                                             AFN
                                                              │
                                                    [subconjuntos]
                                                              ▼
                                                             AFD
                                                              │
                                                       [hopcroft]
                                                              ▼
                                                        AFD mínimo
```

`simulacion` se conecta transversalmente: recibe cualquiera de los tres autómatas
y una cadena, y devuelve un veredicto.

### 4.1 `Token`

Unidad léxica producida por `tokens.tokenizar()`. Es inmutable
(`@dataclass(frozen=True)`).

| Campo | Tipo | Significado |
|---|---|---|
| `tipo` | `TipoToken` | `SIMBOLO`, `EPSILON`, `UNION`, `CONCAT`, `KLEENE`, `PLUS`, `OPCIONAL`, `PAREN_IZQ`, `PAREN_DER` |
| `valor` | `str` | El carácter que representa |
| `posicion` | `int` | Índice en el texto original, para señalar errores |
| `escapado` | `bool` | `True` si venía precedido de `\` |
| `implicito` | `bool` | `True` si es una concatenación insertada por el programa |

### 4.2 `Nodo`

Nodo del árbol sintáctico producido por `arbol.construir()`.

| Campo | Tipo | Significado |
|---|---|---|
| `tipo` | `TipoNodo` | `SIMBOLO`, `EPSILON`, `UNION`, `CONCAT`, `KLEENE`, `PLUS`, `OPCIONAL`, `AUMENTO` |
| `valor` | `str` | Carácter, en las hojas |
| `izquierdo` | `Nodo` | Subárbol izquierdo; único hijo en los operadores unarios |
| `derecho` | `Nodo` | Subárbol derecho; solo en operadores binarios |
| `posicion` | `int` | Número de posición de la hoja |

### 4.3 Objeto `AFN`

Autómata finito no determinista con transiciones epsilon. Codifica la quíntupla
(Q, Σ, δ, q₀, F):

| Atributo | Tipo | Corresponde a |
|---|---|---|
| `estados` | `set[int]` | Q — conjunto de estados |
| `alfabeto` | `set[str]` | Σ — **nunca** incluye epsilon |
| `transiciones` | `dict[int, dict[str, set[int]]]` | δ — `transiciones[estado][símbolo]` es un **conjunto** de destinos |
| `inicial` | `int` | q₀ — estado inicial |
| `aceptacion` | `set[int]` | F — estados de aceptación |

Operaciones:

| Método | Descripción |
|---|---|
| `agregar_transicion(origen, simbolo, destino)` | Registra una transición. Si el símbolo es epsilon, no lo agrega al alfabeto |
| `destinos(estado, simbolo)` | Estados alcanzables desde un estado con un símbolo |
| `cerradura_epsilon(estados)` | Todos los estados alcanzables usando solo transiciones epsilon, incluidos los de partida. Devuelve `frozenset` para poder usarse como clave |
| `mover(estados, simbolo)` | Función *move*: destinos consumiendo exactamente un símbolo, sin aplicar cerradura |
| `es_aceptacion(estados)` | `True` si algún estado del conjunto es final |
| `tabla_transiciones()` | Tabla en texto, con epsilon en su propia columna |
| `a_diccionario()` | Representación serializable a JSON |

La construcción de Thompson produce siempre **un único estado de aceptación**, pero
`aceptacion` se guarda como conjunto para que el objeto siga sirviendo si más
adelante se combinan autómatas.

### 4.4 Objeto `AFD`

Autómata finito determinista. Misma quíntupla, salvo que δ es una **función** y no
una relación:

| Atributo | Tipo | Corresponde a |
|---|---|---|
| `estados` | `set[int]` | Q |
| `alfabeto` | `set[str]` | Σ |
| `transiciones` | `dict[int, dict[str, int]]` | δ — `transiciones[estado][símbolo]` es **un solo** destino |
| `inicial` | `int` | q₀ |
| `aceptacion` | `set[int]` | F |
| `origen` | `dict[int, frozenset]` | Conjunto del que salió cada estado |

`origen` no participa en el reconocimiento. Asocia cada estado del AFD con el
subconjunto de estados del AFN que lo generó, y es lo que permite mostrar el
*listado de estados y las posiciones que conforma cada uno* que pide el enunciado.

Operaciones:

| Método | Descripción |
|---|---|
| `agregar_transicion(origen, simbolo, destino)` | Registra una transición; lanza error si introduce no determinismo |
| `delta(estado, simbolo)` | Estado destino, o `None` si la transición no está definida |
| `es_completo()` | `True` si todo estado tiene transición para todo símbolo |
| `estados_alcanzables()` | Estados alcanzables desde el inicial |
| `completar(sumidero=-1)` | Copia total del AFD, con un estado sumidero que absorbe las transiciones faltantes |
| `copiar()` | Copia profunda |
| `tabla_transiciones()` | Tabla en texto |
| `a_diccionario()` | Representación serializable a JSON |

**El AFD puede ser parcial.** Si un estado no tiene transición para un símbolo, la
simulación rechaza la cadena en ese punto. Esta decisión se explica en la sección 7.1.

### 4.5 Errores

Todos los módulos reportan fallas con excepciones que derivan de `ErrorAnalizador`,
de modo que la interfaz pueda distinguir un error del usuario de un error interno:

- `ErrorDeSintaxis` — la expresión regular no está bien formada. Guarda la posición
  del carácter culpable y la señala con una flecha al imprimirse.
- `ErrorDeAutomata` — se intentó una operación inválida sobre un AFN o un AFD.

## 5. El símbolo epsilon

El enunciado exige determinar claramente qué símbolo se considera ε.

**Internamente epsilon es siempre el carácter `ε`**, definido como la constante
`EPSILON` en `analizador/tokens.py`.

**En la entrada se aceptan dos notaciones**, y ambas producen exactamente el mismo
token: `ε` y `&`. La primera es la notación del enunciado; la segunda es la que se
usó en el Laboratorio 4, de modo que los archivos de prueba de ambos funcionan sin
modificaciones.

**Epsilon no pertenece al alfabeto.** No consume entrada, no aparece como columna en
las tablas de transición del AFD y no recibe número de posición en el árbol
sintáctico. En consecuencia:

- Una expresión como `((ε|a)|b*)*` tiene alfabeto `{a, b}` y solo **2** posiciones.
- Si el usuario escribe el carácter `ε` dentro de la cadena `w`, esa cadena se
  **rechaza**: `ε` no es un símbolo consumible. Para expresar la cadena vacía se
  pasa una cadena vacía, no el carácter.

**Para usar `ε` como carácter literal del alfabeto se escribe `\ε`.**

## 6. Sintaxis de entrada aceptada

| Notación | Significado |
|---|---|
| `\|` | Unión |
| `.` | Concatenación explícita |
| `*` | Cerradura de Kleene |
| `+` | Cerradura positiva (una o más) |
| `?` | Opcional (cero o una) |
| `( )` | Agrupación |
| `ε` o `&` | Epsilon |
| `\x` | El carácter `x` como literal, aunque sea un operador |

Precedencias, de menor a mayor: unión (1), concatenación (2), operadores unarios (3).
La unión y la concatenación son asociativas por la izquierda.

La concatenación es normalmente implícita: `abb` se interpreta como `a.b.b`. Los
espacios en blanco se ignoran; para un espacio literal se escribe `\ `. Para un punto
literal, `\.`.

## 7. Algoritmos implementados

### 7.1 Shunting Yard (infix → postfix)

Implementado en `analizador/shunting_yard.py`.

**El postfix se representa como `list[Token]`, no como `str`.** Esta es la decisión
estructural más importante del proyecto. Un símbolo escapado como `\*` ocupa dos
caracteres en texto, y al reconstruir el árbol desde una cadena el constructor lo
lee como dos cosas distintas y confunde el símbolo con el operador. Trabajando con
tokens, la decisión de si un carácter es operador o símbolo se toma **una sola vez**,
en el tokenizador, y ya no se puede perder.

**Los operadores unarios `*`, `+` y `?` se envían directamente a la salida** en lugar
de pasar por la pila. Es correcto porque en notación infix un operador postfijo
aparece inmediatamente después de su operando, y ese operando —un símbolo o un grupo
entre paréntesis— ya fue emitido por completo cuando se llega al operador.

### 7.2 Construcción de Thompson (árbol → AFN)

Implementado en `analizador/thompson.py`.

El árbol se recorre de abajo hacia arriba. Cada nodo produce un **fragmento**: un AFN
parcial con su propio estado inicial y su propio estado final. Los fragmentos se
combinan según el operador del nodo padre y comparten un único contador de estados,
de modo que los números nunca se repiten entre subárboles. El AFN final toma el
estado inicial y el final del fragmento de la raíz.

Reglas de los operadores unarios, donde *interno* es el fragmento del hijo:

| Operador | Transiciones epsilon que agrega |
|---|---|
| `*` | inicio→interno.inicio, interno.final→final, inicio→final (acepta la vacía), interno.final→interno.inicio (repite) |
| `+` | Igual que `*` **sin** inicio→final: exige al menos una repetición |
| `?` | Igual que `*` **sin** interno.final→interno.inicio: no repite |

La transición de regreso de la repetición sale de `interno.final` —el final del
fragmento hijo— y no del nuevo estado final del fragmento compuesto. Confundir esos
dos estados rompe la repetición de forma silenciosa: el autómata deja de aceptar
`aa`, `aaa`, etc., y ninguna otra comprobación lo detecta.

### 7.3 Construcción de subconjuntos (AFN → AFD)

Implementado en `analizador/subconjuntos.py`.

Se parte de `cerradura_epsilon({inicial})` y se recorre en anchura: por cada
subconjunto y cada símbolo se calcula `cerradura_epsilon(mover(T, a))`. Los
subconjuntos nuevos entran a una cola. Un estado del AFD es de aceptación si su
subconjunto contiene **algún** estado de aceptación del AFN.

**El AFD resultante queda parcial a propósito.** Si `cerradura_epsilon(mover(T, a))`
resulta vacío, no se crea estado ni transición; la simulación rechaza al no encontrar
a dónde ir. El estado sumidero solo aparece cuando se invoca `AFD.completar()`, que es
lo que necesita la minimización. De este modo las tablas del reporte no se llenan de
un estado de error que el enunciado no pide mostrar.

**El alfabeto se fija de una vez** con el del AFN, aunque algún símbolo no llegue a
usarse, para que la tabla de transiciones tenga una columna por cada símbolo de la
expresión.

La numeración de los estados es **estable entre corridas**: el recorrido es en anchura
y los símbolos se visitan en orden. Esto permite regenerar las tablas y los dibujos de
forma idéntica.

`listado_de_estados(afd)` produce el listado de estados con el subconjunto que originó
cada uno, leyendo `AFD.origen`.

### 7.4 Minimización de Hopcroft (AFD → AFD mínimo)

Implementado en `analizador/hopcroft.py`.

Se parte de la partición gruesa `{finales, no finales}` y se refina: mientras exista un
bloque `A` pendiente y un símbolo `c` tales que los predecesores de `A` por `c` parten
en dos a algún bloque de la partición, ese bloque se reemplaza por sus dos mitades.
Cuando ningún símbolo distingue estados dentro de un bloque, cada bloque es una clase
de equivalencia de Myhill-Nerode y se convierte en un estado del AFD mínimo.

**El orden de las etapas importa:** primero se podan los estados inalcanzables y
**después** se completa el autómata. En el orden inverso, el sumidero absorbería las
transiciones faltantes de estados que ni siquiera deberían existir.

**Lo que distingue a Hopcroft de Moore** está en el refinamiento: cuando un bloque se
parte y no estaba en la lista de pendientes, se encola únicamente **la mitad más
pequeña**. Eso es lo que da la cota O(n log n) en lugar de O(n²).

**El AFD mínimo se devuelve parcial**, igual que el de la construcción de subconjuntos:
al final se descartan los bloques estériles —aquellos desde los que ya no se puede
llegar a un estado final, incluido el sumidero que agregó `completar()`. El lenguaje
reconocido no cambia.

`construir_con_bloques(afd)` devuelve además el mapeo de cada estado mínimo a los
estados del AFD original que se fundieron en él, que es lo que permite explicar la
minimización; `listado_de_bloques()` lo formatea.

### 7.5 Simulación

Implementado en `analizador/simulacion.py`.

La diferencia entre los dos modos:

- **AFN:** se sigue un **conjunto** de estados a la vez. En cada símbolo se aplica
  `cerradura_epsilon(mover(actuales, símbolo))`. La cadena se acepta si el conjunto
  final toca algún estado de aceptación.
- **AFD:** se sigue **un solo** estado. En cada símbolo se consulta `delta`, y si
  devuelve `None` la cadena se rechaza en ese punto.

Ese `None` no es un caso de borde sino parte del diseño: los AFD son parciales a
propósito, así que **la ausencia de transición es la forma normal de rechazar**.

`recorrido_afn` y `recorrido_afd` devuelven la traza completa del recorrido, y las
funciones de aceptación se construyen sobre ellas, de modo que no existan dos
implementaciones del mismo recorrido que puedan divergir.

Un símbolo que no está en el alfabeto se ataja **antes** de llamar a `mover`, porque
`AFN.mover` rechaza epsilon con una excepción y la cadena `w` puede contener
perfectamente el carácter `ε`. Para la simulación eso no es un error del programa
sino una cadena que no pertenece al lenguaje.

**La comparación entre los tres autómatas es visible, no solo interna.** `simular()`
devuelve un `Resultado` con el veredicto de cada autómata y la propiedad `coinciden`.
Como los tres reconocen el mismo lenguaje, una discrepancia señalaría un error en
alguna etapa anterior, y el programa lo reporta explícitamente.

`simbolos_desconocidos()` no cambia el veredicto —la cadena se rechaza igual— pero
permite avisar al usuario que escribió símbolos ajenos al alfabeto de la expresión.

## 8. Decisiones de diseño transversales

**Transiciones en diccionarios anidados.** `AFN.transiciones` es
`dict[estado][símbolo] -> set[estado]` y `AFD.transiciones` es
`dict[estado][símbolo] -> estado`, en lugar de listas planas de tripletas. La
construcción de subconjuntos consulta una vez por cada par (estado, símbolo), y con
una lista plana esa búsqueda se vuelve cuadrática.

**Numeración estable.** Todos los recorridos que numeran estados son en anchura y con
los símbolos ordenados, para que dos corridas sobre la misma expresión produzcan
autómatas idénticos.

**Nombres, comentarios y docstrings en español**, consistente con los laboratorios
previos del curso.

**Codificación de salida.** `main.py` fuerza `sys.stdout.reconfigure(encoding="utf-8")`
porque la consola de Windows suele venir configurada en cp1252, que no puede imprimir
`ε` ni los caracteres de dibujo del árbol.

## 9. Resultados verificados

Las cuatro expresiones de prueba del curso y su conversión a postfix:

```
(a*|b*)+          →  a*b*|+
((ε|a)|b*)*       →  εa|b*|*
(a|b)*abb(a|b)*   →  ab|*a.b.b.ab|*.
0?(1?)?0*         →  0?1??.0*.
```

Aceptación:

| Expresión | Cadena | Acepta | Acepta `""` |
|---|---|---|---|
| `(a*\|b*)+` | `abba` | sí | sí |
| `((ε\|a)\|b*)*` | `abba` | sí | sí |
| `(a\|b)*abb(a\|b)*` | `aabbab` | sí | no |
| `0?(1?)?0*` | `0100` | sí | sí |

Tamaño de los autómatas en cada etapa:

| Expresión | AFN | AFD | AFD mínimo | Observación |
|---|---|---|---|---|
| `(a*\|b*)+` | 12 | 3 | 1 | los 3 estados son de aceptación: el lenguaje es Σ* |
| `((ε\|a)\|b*)*` | 14 | 3 | 1 | también reconoce Σ* |
| `(a\|b)*abb(a\|b)*` | 22 | 9 | 4 | el AFD clásico para `abb` |
| `0?(1?)?0*` | 14 | 4 | 3 | |

Dos observaciones sobre estos resultados:

**Que las dos primeras expresiones reconozcan Σ\* no es un error.** Tanto `a*` como
`b*` aceptan la cadena vacía, de modo que la unión bajo `+` (o bajo `*`) puede
descomponer cualquier cadena en bloques de `a` y bloques de `b`.

**El AFD mínimo de `(a|b)*abb(a|b)*` es el autómata clásico:** `q0` sin progreso, `q1`
ha visto `a`, `q2` ha visto `ab`, `q3` absorbente de aceptación. La partición
resultante es `{A0,A2}`, `{A1}`, `{A3}`, `{A4..A8}`.

**Sobre el árbol de `0?(1?)?0*`:** produce un nodo `?` anidado dentro de otro `?`,
porque así está escrita la expresión. Es correcto, aunque genera estados redundantes
en la construcción de Thompson. No se simplifica deliberadamente, porque hacerlo
alteraría el árbol sintáctico que corresponde a la expresión dada.

## 10. Pruebas

109 pruebas unitarias, todas pasando:

| Archivo | Pruebas | Cubre |
|---|---|---|
| `test_fase01.py` | 34 | Tokenización, validación, Shunting Yard, árbol, objetos AFN y AFD |
| `test_fase02.py` | 9 | Construcción de Thompson |
| `test_fase03.py` | 11 | Construcción de subconjuntos y equivalencia AFN ↔ AFD |
| `test_fase04.py` | 14 | Minimización, tamaños y partición esperados |
| `test_fase05.py` | 15 | Simulación, recorridos y comparación entre autómatas |
| `test_main.py` | 8 | Interfaz de línea de comandos: ubicación del archivo, simulación y manejo de errores |
| `test_reporte.py` | 18 | Generación del reporte HTML, escapado y manejo de expresiones inválidas |

La verificación más fuerte del proyecto es la **equivalencia exhaustiva**: para cada
expresión del curso se generan todas las cadenas de longitud 0 a 5 sobre su alfabeto
y se exige que el AFN, el AFD y el AFD mínimo den la misma respuesta en cada una. Si
alguna etapa introdujera un error, esa comparación lo detectaría.

```bash
python3 -m unittest discover -s tests -v
```

## 11. Estado de implementación

| Componente | Estado |
|---|---|
| Objetos AFN y AFD | Completo |
| Shunting Yard y árbol sintáctico | Completo |
| Construcción de Thompson | Completo |
| Construcción de subconjuntos | Completo |
| Minimización de Hopcroft | Completo |
| Simulación de AFN y AFD | Completo |
| Procesamiento por lotes | Completo |
| Dibujo de autómatas | Pendiente |
| Construcción directa de AFD | Pendiente |

## 12. Origen del código

El proyecto es una recopilación de laboratorios previos del curso, que estaban
escritos en lenguajes distintos:

- **Laboratorio 3 (Python)** — Shunting Yard, árbol sintáctico y construcción directa
  de AFD con `nullable`, `firstpos`, `lastpos` y `followpos`.
- **Laboratorio 4 (Java)** — Shunting Yard, árbol, construcción de Thompson completa,
  cerradura epsilon y simulación de AFN.

**Se decidió unificar todo en Python.** El código de Lab 3 que se conserva es el más
costoso de reescribir, la construcción de subconjuntos y Hopcroft resultan mucho más
compactas con `set` y `frozenset`, y la generación de gráficos desde Python es
directa. La lógica de Thompson del Lab 4 se portó a Python.

### Correcciones aplicadas respecto a los laboratorios

Al integrar el código se detectaron y corrigieron los siguientes problemas:

1. **`ε` no se trataba como epsilon** en Lab 3: se manejaba como un símbolo cualquiera,
   por lo que `((ε|a)|b*)*` exigía el carácter `ε` en la cadena de entrada.
2. **El árbol no se aumentaba con `#`** en la construcción directa. La aceptación se
   decidía con `max(posición)`, lo cual solo funciona si la última posición resulta ser
   el marcador final; con `(a|b)*abb(a|b)*` producía estados de aceptación incorrectos.
3. **Faltaba `followpos` para el operador `+`**: solo se calculaba para `*`, lo que
   rompía `(a*|b*)+`.
4. **Comparación de enums contra cadenas** en la decisión de asociatividad del Shunting
   Yard, que hacía que siempre se tomara la rama de asociatividad derecha. No alteraba
   el lenguaje reconocido, pero producía un postfix distinto del esperado.
5. **Falta de soporte para escapes con `\`** en el código Java, que Lab 3 sí manejaba.
6. **Transiciones almacenadas en una lista plana** en el código Java, recorrida
   completa en cada consulta.

Los puntos 1, 4, 5 y 6 están resueltos en la implementación actual. Los puntos 2 y 3
corresponden a la construcción directa de AFD, que queda pendiente.
