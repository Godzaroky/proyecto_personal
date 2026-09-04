"""
Utilidades compartidas por las pruebas.

Los atajos que van de una expresión regular a cada autómata del
pipeline, más un generador de cadenas para las pruebas exhaustivas.

`acepta_afn` y `acepta_afd` se reexportan desde
`analizador.simulacion`: vivieron aquí como andamio hasta la Fase 5 y
ahora son código de producción, así que las pruebas deben ejercitar esa
versión y no una copia.
"""

import os
import sys
from itertools import product
from typing import Iterator, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analizador.arbol import construir as construir_arbol  # noqa: E402
from analizador.automatas.afd import AFD  # noqa: E402
from analizador.automatas.afn import AFN  # noqa: E402
from analizador.shunting_yard import convertir  # noqa: E402
from analizador.hopcroft import construir as construir_minimo  # noqa: E402
from analizador.simulacion import acepta_afd, acepta_afn  # noqa: E402,F401
from analizador.subconjuntos import construir as construir_afd  # noqa: E402
from analizador.thompson import construir as construir_afn  # noqa: E402

# Las cuatro expresiones que piden el Lab 3, el Lab 4 y el proyecto.
EXPRESIONES_DEL_CURSO = [
    "(a*|b*)+",
    "((ε|a)|b*)*",
    "(a|b)*abb(a|b)*",
    "0?(1?)?0*",
]


def afn_de(expresion: str) -> AFN:
    """Atajo: expresión regular -> AFN de Thompson."""
    return construir_afn(construir_arbol(convertir(expresion)))


def afd_de(expresion: str) -> AFD:
    """Atajo: expresión regular -> AFD por subconjuntos."""
    return construir_afd(afn_de(expresion))


def minimo_de(expresion: str) -> AFD:
    """Atajo: expresión regular -> AFD mínimo por Hopcroft."""
    return construir_minimo(afd_de(expresion))


def cadenas_hasta(alfabeto: List[str], longitud_maxima: int) -> Iterator[str]:
    """
    Genera todas las cadenas sobre `alfabeto` de longitud 0 hasta
    `longitud_maxima`, empezando por la cadena vacía.
    """
    for longitud in range(longitud_maxima + 1):
        for combinacion in product(sorted(alfabeto), repeat=longitud):
            yield "".join(combinacion)
