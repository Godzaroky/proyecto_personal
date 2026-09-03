"""
Construcción de Thompson: árbol sintáctico -> AFN.

Cada nodo del árbol produce un fragmento con un único estado inicial y
un único estado de aceptación, siguiendo las reglas clásicas de
Thompson. Los fragmentos se combinan de abajo hacia arriba y comparten
un mismo contador de estados para que los números no se repitan.

Regla de los operadores unarios (portada de Main.java, ver CLAUDE.md):
    *   añade epsilon inicio->fin (para aceptar la cadena vacía) y
        fin->inicio (para repetir).
    +   igual que *, pero sin la epsilon inicio->fin: exige al menos
        una repetición.
    ?   igual que *, pero sin la epsilon fin->inicio: no repite.
"""

from __future__ import annotations

from itertools import count
from typing import Iterator

from .arbol import Nodo, TipoNodo
from .automatas.afn import AFN
from .errores import ErrorDeAutomata
from .tokens import EPSILON


class _Fragmento:
    """Un AFN parcial con un único estado inicial y uno de aceptación."""

    __slots__ = ("afn", "inicial", "final")

    def __init__(self, afn: AFN, inicial: int, final: int):
        self.afn = afn
        self.inicial = inicial
        self.final = final


def construir(raiz: Nodo) -> AFN:
    """Construye el AFN de Thompson a partir de la raíz del árbol sintáctico."""
    contador: Iterator[int] = count()

    def nuevo_estado() -> int:
        return next(contador)

    def visitar(nodo: Nodo) -> _Fragmento:
        if nodo.tipo == TipoNodo.SIMBOLO:
            return _fragmento_simbolo(nuevo_estado, nodo.valor)
        if nodo.tipo == TipoNodo.EPSILON:
            return _fragmento_simbolo(nuevo_estado, EPSILON)
        if nodo.tipo == TipoNodo.UNION:
            return _fragmento_union(nuevo_estado, visitar(nodo.izquierdo), visitar(nodo.derecho))
        if nodo.tipo == TipoNodo.CONCAT:
            return _fragmento_concat(visitar(nodo.izquierdo), visitar(nodo.derecho))
        if nodo.tipo == TipoNodo.KLEENE:
            return _fragmento_repeticion(nuevo_estado, visitar(nodo.izquierdo), permite_vacia=True, permite_repetir=True)
        if nodo.tipo == TipoNodo.PLUS:
            return _fragmento_repeticion(nuevo_estado, visitar(nodo.izquierdo), permite_vacia=False, permite_repetir=True)
        if nodo.tipo == TipoNodo.OPCIONAL:
            return _fragmento_repeticion(nuevo_estado, visitar(nodo.izquierdo), permite_vacia=True, permite_repetir=False)

        raise ErrorDeAutomata(f"Thompson no sabe construir el nodo {nodo.tipo}.")

    fragmento = visitar(raiz)
    fragmento.afn.inicial = fragmento.inicial
    fragmento.afn.aceptacion = {fragmento.final}
    return fragmento.afn


def _fragmento_simbolo(nuevo_estado, simbolo: str) -> _Fragmento:
    inicial = nuevo_estado()
    final = nuevo_estado()
    afn = AFN(inicial, [final])
    afn.agregar_transicion(inicial, simbolo, final)
    return _Fragmento(afn, inicial, final)


def _fusionar(afn: AFN, otro: AFN) -> None:
    """Copia estados, alfabeto y transiciones de `otro` dentro de `afn`."""
    afn.estados.update(otro.estados)
    afn.alfabeto.update(otro.alfabeto)
    for origen, transiciones in otro.transiciones.items():
        for simbolo, destinos in transiciones.items():
            for destino in destinos:
                afn.agregar_transicion(origen, simbolo, destino)


def _fragmento_union(nuevo_estado, izquierdo: _Fragmento, derecho: _Fragmento) -> _Fragmento:
    inicial = nuevo_estado()
    final = nuevo_estado()

    afn = AFN(inicial, [final])
    _fusionar(afn, izquierdo.afn)
    _fusionar(afn, derecho.afn)

    afn.agregar_transicion(inicial, EPSILON, izquierdo.inicial)
    afn.agregar_transicion(inicial, EPSILON, derecho.inicial)
    afn.agregar_transicion(izquierdo.final, EPSILON, final)
    afn.agregar_transicion(derecho.final, EPSILON, final)

    return _Fragmento(afn, inicial, final)


def _fragmento_concat(izquierdo: _Fragmento, derecho: _Fragmento) -> _Fragmento:
    afn = izquierdo.afn
    _fusionar(afn, derecho.afn)
    afn.agregar_transicion(izquierdo.final, EPSILON, derecho.inicial)
    return _Fragmento(afn, izquierdo.inicial, derecho.final)


def _fragmento_repeticion(
    nuevo_estado, interno: _Fragmento, *, permite_vacia: bool, permite_repetir: bool
) -> _Fragmento:
    inicial = nuevo_estado()
    final = nuevo_estado()

    afn = interno.afn
    afn.agregar_estado(inicial)
    afn.agregar_estado(final)

    afn.agregar_transicion(inicial, EPSILON, interno.inicial)
    afn.agregar_transicion(interno.final, EPSILON, final)

    if permite_vacia:
        afn.agregar_transicion(inicial, EPSILON, final)
    if permite_repetir:
        afn.agregar_transicion(interno.final, EPSILON, interno.inicial)

    return _Fragmento(afn, inicial, final)
