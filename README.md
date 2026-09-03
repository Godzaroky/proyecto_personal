# Proyecto #1 — Analizador léxico

Universidad del Valle de Guatemala
Teoría de la Computación (CC2019) — Sección 30
Docente: Tomás Gálvez P. — Semestre 2, 2026

**Integrantes**

| Nombre | Carné |
|---|---|
| Jorge Morales | 24284 |
| Javier Castillo | 24014 |
| Diego Gonzales | 24170 |

---

## Estado actual

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Estructuras base: objetos `AFN` y `AFD` | Completa |
| 1 | Preprocesamiento, Shunting Yard y árbol sintáctico | Completa |
| 2 | Construcción de Thompson (regex → AFN) | Pendiente |
| 3 | Construcción de subconjuntos (AFN → AFD) | Pendiente |
| 4 | Minimización con Hopcroft | Pendiente |
| 5 | Simulación de AFN y AFD | Pendiente |
| 6 | Dibujo de autómatas | Pendiente |
| 7 | Procesamiento por lotes | Pendiente |
| 8 | Interfaz de usuario | Pendiente |
| 9 | Construcción directa de AFD (recuperación) | Pendiente |
| 10 | Pruebas | Parcial |
| 11 | Documentación y video | Pendiente |

## Ejecución

```bash
python3 main.py                 # usa expresiones.txt
python3 main.py otro_archivo.txt
```

Pruebas:

```bash
python3 -m unittest discover -s tests -v
```

No se requieren dependencias externas. Graphviz se agregará en la Fase 6.

## Convenciones de entrada

| Símbolo | Significado |
|---|---|
| `\|` | unión |
| `.` | concatenación explícita (normalmente es implícita) |
| `*` | cerradura de Kleene |
| `+` | cerradura positiva |
| `?` | opcional |
| `( )` | agrupación |
| `ε` o `&` | epsilon |
| `\x` | el carácter `x` como símbolo literal |

### El símbolo epsilon

Internamente epsilon se representa siempre con **`ε`**. En la entrada se
aceptan tanto `ε` como `&`, y ambos producen el mismo token: `ε` es la
notación del enunciado y `&` la que se usó en el Laboratorio 4, de modo
que los archivos de prueba de ambos laboratorios funcionan sin cambios.

Epsilon **no pertenece al alfabeto**: no consume entrada, no aparece como
columna del alfabeto en las tablas de transición del AFD y no recibe
número de posición en la construcción directa. Para usar el carácter `ε`
como símbolo literal del lenguaje se escribe `\ε`.

### Espacios y escapes

Los espacios en blanco se ignoran, así que `a b` y `ab` son la misma
expresión. Para un espacio literal se escribe `\ `. Cualquier operador
precedido de `\` se convierte en un símbolo del alfabeto: en `a\*b` el
asterisco es un carácter, no una cerradura.

## Arquitectura

```
analizador/
├── errores.py          Excepciones del proyecto
├── tokens.py           Fase 1a: tokenización, concatenación implícita, validación
├── shunting_yard.py    Fase 1b: infix → postfix
├── arbol.py            Fase 1c: árbol sintáctico y numeración de posiciones
└── automatas/
    ├── afn.py          Fase 0: objeto AFN
    └── afd.py          Fase 0: objeto AFD
```

El flujo de datos es lineal y cada módulo depende únicamente de los
anteriores:

```
texto → [tokens] → Token[] → [shunting_yard] → Token[] postfix → [arbol] → Nodo
                                                                            │
                                            ┌───────────────────────────────┴───┐
                                            ↓                                   ↓
                                    Thompson (Fase 2)              Construcción directa (Fase 9)
                                            ↓                                   ↓
                                           AFN ──── subconjuntos (Fase 3) ───→ AFD
                                                                                ↓
                                                                       Hopcroft (Fase 4)
```

### Protocolo entre módulos

El postfix viaja como **lista de `Token`**, no como cadena de texto. Esto
es deliberado: un símbolo escapado como `\*` ocupa dos caracteres, y una
representación en texto obliga al constructor del árbol a re-analizar el
escape y lo lleva a confundir el símbolo con el operador. Con tokens, la
decisión de si un carácter es operador o símbolo se toma una sola vez,
en el tokenizador.

### Objetos que codifican los autómatas

Ambos autómatas son la quíntupla (Q, Σ, δ, q₀, F). La diferencia está en δ:

| | `AFN` | `AFD` |
|---|---|---|
| δ | `dict[estado][símbolo] -> set[estado]` | `dict[estado][símbolo] -> estado` |
| Transiciones ε | sí | no |
| Función total | no | opcional (`completar()` agrega sumidero) |

Las transiciones se guardan en diccionarios anidados en vez de una lista
plana. En el Laboratorio 4 eran una lista y cada consulta la recorría
completa; con construcción de subconjuntos, que consulta una vez por cada
par (estado, símbolo), ese costo se vuelve cuadrático.

El `AFD` guarda además el diccionario `origen`, que asocia cada estado con
el conjunto del que salió: el subconjunto de estados del AFN en la
construcción por subconjuntos, o el conjunto de posiciones en la
construcción directa. No participa en el reconocimiento del lenguaje,
pero es lo que hay que mostrar en la documentación y en el video.
