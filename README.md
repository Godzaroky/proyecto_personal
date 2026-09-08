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

Dada una expresión regular `r` y una cadena `w`, el programa convierte `r` a
notación postfix con Shunting Yard, construye un AFN por Thompson, lo convierte
a AFD por construcción de subconjuntos, lo minimiza con Hopcroft y simula `w`
sobre los tres autómatas.

## Ejecución

Requiere únicamente Python 3, sin dependencias externas.

```bash
python3 main.py                                  # usa expresiones.txt
python3 main.py otro_archivo.txt                 # otro archivo de expresiones
python3 main.py expresiones.txt abba             # además simula w = "abba"
python3 main.py expresiones.txt ""               # simula la cadena vacía
```

El archivo de entrada lleva una expresión regular por línea.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

91 pruebas, todas pasando.

## Sintaxis de entrada

| Notación | Significado |
|---|---|
| `\|` | unión |
| `.` | concatenación explícita (normalmente es implícita) |
| `*` | cerradura de Kleene |
| `+` | cerradura positiva |
| `?` | opcional |
| `( )` | agrupación |
| `ε` o `&` | epsilon |
| `\x` | el carácter `x` como símbolo literal |

Epsilon se representa internamente con `ε` y **no pertenece al alfabeto**: no
consume entrada ni aparece en las tablas de transición del AFD. Para usar `ε`
como carácter literal se escribe `\ε`.

## Documentación

La documentación completa —arquitectura, protocolos de comunicación entre
módulos, definición de los objetos que codifican el AFN y el AFD, algoritmos
implementados y resultados verificados— está en:

**[`docs/DISEÑO.md`](docs/DISEÑO.md)**
