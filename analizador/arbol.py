"""
Árbol sintáctico.

Construye el árbol sintáctico de una expresión regular a partir de su
notación postfix.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from .errores import ErrorDeSintaxis
from .tokens import EPSILON, TIPOS_UNARIOS, Token, TipoToken


class TipoNodo(Enum):
    """Tipos de nodo del árbol sintáctico."""

    SIMBOLO = "SIMBOLO"    # hoja: un carácter del alfabeto
    EPSILON = "EPSILON"    # hoja: la cadena vacía
    UNION = "UNION"        # binario: |
    CONCAT = "CONCAT"      # binario: .
    KLEENE = "KLEENE"      # unario: *
    PLUS = "PLUS"          # unario: +
    OPCIONAL = "OPCIONAL"  # unario: ?
    AUMENTO = "AUMENTO"    # hoja: marcador # de la construcción directa


# Traducción de tipos de token a tipos de nodo.
TOKEN_A_NODO = {
    TipoToken.SIMBOLO: TipoNodo.SIMBOLO,
    TipoToken.EPSILON: TipoNodo.EPSILON,
    TipoToken.UNION: TipoNodo.UNION,
    TipoToken.CONCAT: TipoNodo.CONCAT,
    TipoToken.KLEENE: TipoNodo.KLEENE,
    TipoToken.PLUS: TipoNodo.PLUS,
    TipoToken.OPCIONAL: TipoNodo.OPCIONAL,
}

TIPOS_NODO_HOJA = {TipoNodo.SIMBOLO, TipoNodo.EPSILON, TipoNodo.AUMENTO}
TIPOS_NODO_UNARIO = {TipoNodo.KLEENE, TipoNodo.PLUS, TipoNodo.OPCIONAL}
TIPOS_NODO_BINARIO = {TipoNodo.UNION, TipoNodo.CONCAT}


class Nodo:
    """
    Nodo del árbol sintáctico.

    Atributos:
        tipo:      categoría del nodo.
        valor:     para hojas SIMBOLO, el carácter que representan.
        izquierdo: subárbol izquierdo (el único hijo en los unarios).
        derecho:   subárbol derecho (solo en nodos binarios).
        posicion:  número de posición de la hoja. Lo asigna
                   numerar_posiciones() y solo lo usa la Fase 9.
    """

    __slots__ = ("tipo", "valor", "izquierdo", "derecho", "posicion")

    def __init__(
        self,
        tipo: TipoNodo,
        valor: str = "",
        izquierdo: Optional["Nodo"] = None,
        derecho: Optional["Nodo"] = None,
    ):
        self.tipo = tipo
        self.valor = valor
        self.izquierdo = izquierdo
        self.derecho = derecho
        self.posicion: Optional[int] = None

    def es_hoja(self) -> bool:
        return self.tipo in TIPOS_NODO_HOJA

    def hijos(self) -> List["Nodo"]:
        """Hijos existentes, de izquierda a derecha."""
        return [h for h in (self.izquierdo, self.derecho) if h is not None]

    def etiqueta(self) -> str:
        """Texto corto para mostrar el nodo al dibujarlo o imprimirlo."""
        if self.tipo == TipoNodo.SIMBOLO:
            base = self.valor
        elif self.tipo == TipoNodo.EPSILON:
            base = EPSILON
        elif self.tipo == TipoNodo.AUMENTO:
            base = "#"
        elif self.tipo == TipoNodo.UNION:
            return "|"
        elif self.tipo == TipoNodo.CONCAT:
            return "."
        elif self.tipo == TipoNodo.KLEENE:
            return "*"
        elif self.tipo == TipoNodo.PLUS:
            return "+"
        else:
            return "?"

        # Las hojas muestran su número de posición cuando lo tienen.
        if self.posicion is not None:
            return f"{base}{chr(0x2080 + self.posicion)}" if self.posicion < 10 else f"{base}({self.posicion})"
        return base

    def __repr__(self) -> str:
        return f"Nodo({self.tipo.name}, {self.etiqueta()!r})"


def construir(postfix: List[Token]) -> Nodo:
    """
    Construye el árbol sintáctico recorriendo la expresión postfix con
    una pila de subárboles.

    Cada operando empuja una hoja; cada operador desapila tantos
    subárboles como operandos necesite y empuja el nodo resultante.
    """
    pila: List[Nodo] = []

    for token in postfix:
        tipo_nodo = TOKEN_A_NODO[token.tipo]

        if token.es_operando():
            pila.append(Nodo(tipo_nodo, token.valor))

        elif token.tipo in TIPOS_UNARIOS:
            if not pila:
                raise ErrorDeSintaxis(
                    f"Falta el operando del operador '{token.valor}'."
                )
            hijo = pila.pop()
            pila.append(Nodo(tipo_nodo, token.valor, izquierdo=hijo))

        else:  # operador binario
            if len(pila) < 2:
                raise ErrorDeSintaxis(
                    f"Faltan operandos para el operador '{token.valor}'."
                )
            derecho = pila.pop()
            izquierdo = pila.pop()
            pila.append(Nodo(tipo_nodo, token.valor, izquierdo, derecho))

    if len(pila) != 1:
        raise ErrorDeSintaxis(
            "La expresión regular no es válida: sobran operandos sin combinar."
        )

    return pila[0]


def numerar_posiciones(raiz: Nodo) -> List[Tuple[int, str]]:
    """
    Asigna números de posición a las hojas, de izquierda a derecha.

    Las hojas EPSILON no reciben número: no ocupan posición en la
    construcción directa porque no consumen entrada.

    Devuelve la lista de pares (posición, símbolo).
    """
    posiciones: List[Tuple[int, str]] = []
    contador = 0

    def recorrer(nodo: Optional[Nodo]) -> None:
        nonlocal contador
        if nodo is None:
            return

        if nodo.tipo == TipoNodo.EPSILON:
            nodo.posicion = None
            return

        if nodo.es_hoja():
            contador += 1
            nodo.posicion = contador
            posiciones.append((contador, nodo.valor))
            return

        recorrer(nodo.izquierdo)
        recorrer(nodo.derecho)

    recorrer(raiz)
    return posiciones


def a_texto(raiz: Nodo, prefijo: str = "", es_ultimo: bool = True) -> str:
    """
    Representación ASCII del árbol, útil para la consola y para el video.
    """
    lineas: List[str] = []

    conector = "└── " if es_ultimo else "├── "
    lineas.append(f"{prefijo}{conector}{raiz.etiqueta()}")

    hijos = raiz.hijos()
    extension = "    " if es_ultimo else "│   "

    for indice, hijo in enumerate(hijos):
        lineas.append(
            a_texto(hijo, prefijo + extension, indice == len(hijos) - 1)
        )

    return "\n".join(lineas)


def a_postfix_texto(postfix: List[Token]) -> str:
    """Cadena legible de la expresión postfix, para mostrarla en pantalla."""
    return "".join(token.texto() for token in postfix)
