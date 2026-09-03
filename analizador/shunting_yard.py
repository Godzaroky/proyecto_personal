"""
Algoritmo Shunting Yard.

Convierte una expresión regular de notación infix a notación postfix,
trabajando sobre listas de Token en vez de cadenas de texto.

Precedencias, de menor a mayor:

    1   |            unión
    2   .            concatenación
    3   *  +  ?      operadores unarios

La unión y la concatenación son asociativas por la izquierda.
"""

from __future__ import annotations

from typing import List

from .errores import ErrorDeSintaxis
from .tokens import (
    TIPOS_BINARIOS,
    TIPOS_UNARIOS,
    Token,
    TipoToken,
    preparar,
)

# Precedencia de los operadores binarios. Los unarios no entran a la pila
# (ver a_postfix), así que no necesitan una entrada aquí.
PRECEDENCIA = {
    TipoToken.UNION: 1,
    TipoToken.CONCAT: 2,
}


def a_postfix(tokens: List[Token], expresion: str = "") -> List[Token]:
    """
    Aplica Shunting Yard sobre una lista de tokens ya preparada.
    
    """
    salida: List[Token] = []
    pila: List[Token] = []

    for token in tokens:
        if token.es_operando():
            salida.append(token)

        elif token.tipo in TIPOS_UNARIOS:
            salida.append(token)

        elif token.tipo in TIPOS_BINARIOS:
            # Se desapila mientras el tope tenga precedencia mayor o igual,
            # que es la regla para operadores asociativos por la izquierda.
            while (
                pila
                and pila[-1].tipo != TipoToken.PAREN_IZQ
                and PRECEDENCIA[pila[-1].tipo] >= PRECEDENCIA[token.tipo]
            ):
                salida.append(pila.pop())
            pila.append(token)

        elif token.tipo == TipoToken.PAREN_IZQ:
            pila.append(token)

        elif token.tipo == TipoToken.PAREN_DER:
            encontro_apertura = False
            while pila:
                tope = pila.pop()
                if tope.tipo == TipoToken.PAREN_IZQ:
                    encontro_apertura = True
                    break
                salida.append(tope)

            if not encontro_apertura:
                raise ErrorDeSintaxis(
                    "Los paréntesis no están balanceados.",
                    expresion,
                    token.posicion,
                )

    while pila:
        tope = pila.pop()
        if tope.tipo == TipoToken.PAREN_IZQ:
            raise ErrorDeSintaxis(
                "Los paréntesis no están balanceados.",
                expresion,
                tope.posicion,
            )
        salida.append(tope)

    return salida


def convertir(expresion: str) -> List[Token]:
    """
    Atajo que va del texto crudo al postfix en un solo paso.

    Encadena preparar() —tokenizar, concatenación implícita, validar— con
    a_postfix().
    """
    tokens = preparar(expresion)
    return a_postfix(tokens, expresion)
