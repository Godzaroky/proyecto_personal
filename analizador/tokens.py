"""
Tokenización de expresiones regulares.

Convierte el texto crudo de una expresión regular en una lista de objetos
Token. Este es el único módulo del proyecto que trabaja con caracteres
sueltos; de aquí en adelante todo el pipeline opera sobre tokens.

Convenciones de entrada (documentadas también en el README):

    |        unión
    .        concatenación explícita (normalmente es implícita)
    *        cerradura de Kleene
    +        cerradura positiva
    ?        opcional
    ( )      agrupación
    ε  &     epsilon (ambos se aceptan y se normalizan al mismo token)
    \\x       el carácter x como literal, incluso si es un operador

Los espacios en blanco se ignoran; para un espacio literal se usa "\\ ".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .errores import ErrorDeSintaxis

# Representación canónica de epsilon dentro del programa.
EPSILON = "ε"

# Símbolos que el usuario puede escribir para referirse a epsilon.
ALIAS_EPSILON = {"ε", "&"}

# Caracteres reservados como operadores.
OPERADORES_UNARIOS = {"*", "+", "?"}
OPERADORES_BINARIOS = {"|", "."}
AGRUPADORES = {"(", ")"}
RESERVADOS = OPERADORES_UNARIOS | OPERADORES_BINARIOS | AGRUPADORES | ALIAS_EPSILON


class TipoToken(Enum):
    """Categorías de token producidas por el tokenizador."""

    SIMBOLO = "SIMBOLO"      # un carácter del alfabeto
    EPSILON = "EPSILON"      # la cadena vacía
    UNION = "UNION"          # |
    CONCAT = "CONCAT"        # .
    KLEENE = "KLEENE"        # *
    PLUS = "PLUS"            # +
    OPCIONAL = "OPCIONAL"    # ?
    PAREN_IZQ = "PAREN_IZQ"  # (
    PAREN_DER = "PAREN_DER"  # )


# Conjuntos auxiliares usados por el validador y por el insertor de
# concatenación implícita.
TIPOS_UNARIOS = {TipoToken.KLEENE, TipoToken.PLUS, TipoToken.OPCIONAL}
TIPOS_BINARIOS = {TipoToken.UNION, TipoToken.CONCAT}

# Un token "cierra" una expresión si puede ser el final de un operando:
# un símbolo, epsilon, un paréntesis derecho o un operador unario ya aplicado.
TIPOS_QUE_CIERRAN = {TipoToken.SIMBOLO, TipoToken.EPSILON, TipoToken.PAREN_DER} | TIPOS_UNARIOS

# Un token "abre" una expresión si puede ser el inicio de un operando.
TIPOS_QUE_ABREN = {TipoToken.SIMBOLO, TipoToken.EPSILON, TipoToken.PAREN_IZQ}


@dataclass(frozen=True)
class Token:

    tipo: TipoToken
    valor: str
    posicion: int = -1
    escapado: bool = False
    implicito: bool = False

    def es_operando(self) -> bool:
        """True si el token representa un valor y no una operación."""
        return self.tipo in (TipoToken.SIMBOLO, TipoToken.EPSILON)

    def texto(self) -> str:
        """Representación legible del token, reinsertando el escape."""
        if self.escapado:
            return "\\" + self.valor
        if self.tipo == TipoToken.EPSILON:
            return EPSILON
        return self.valor

    def __str__(self) -> str:
        return self.texto()


def tokenizar(expresion: str) -> List[Token]:
    """
    Convierte una expresión regular en una lista de tokens.
    """
    tokens: List[Token] = []
    i = 0
    n = len(expresion)

    while i < n:
        caracter = expresion[i]

        # Los espacios no significan nada; para un espacio literal, "\ ".
        if caracter.isspace():
            i += 1
            continue

        # Escape: el siguiente carácter es siempre un símbolo del alfabeto.
        if caracter == "\\":
            if i + 1 >= n:
                raise ErrorDeSintaxis(
                    "La expresión termina con una barra invertida suelta.",
                    expresion,
                    i,
                )
            tokens.append(
                Token(TipoToken.SIMBOLO, expresion[i + 1], i, escapado=True)
            )
            i += 2
            continue

        if caracter in ALIAS_EPSILON:
            tokens.append(Token(TipoToken.EPSILON, EPSILON, i))
        elif caracter == "|":
            tokens.append(Token(TipoToken.UNION, "|", i))
        elif caracter == ".":
            tokens.append(Token(TipoToken.CONCAT, ".", i))
        elif caracter == "*":
            tokens.append(Token(TipoToken.KLEENE, "*", i))
        elif caracter == "+":
            tokens.append(Token(TipoToken.PLUS, "+", i))
        elif caracter == "?":
            tokens.append(Token(TipoToken.OPCIONAL, "?", i))
        elif caracter == "(":
            tokens.append(Token(TipoToken.PAREN_IZQ, "(", i))
        elif caracter == ")":
            tokens.append(Token(TipoToken.PAREN_DER, ")", i))
        else:
            tokens.append(Token(TipoToken.SIMBOLO, caracter, i))

        i += 1

    if not tokens:
        raise ErrorDeSintaxis("La expresión regular está vacía.", expresion, 0)

    return tokens


def insertar_concatenacion(tokens: List[Token]) -> List[Token]:
    """
    Inserta el operador de concatenación donde está implícito.
    """
    resultado: List[Token] = []

    for token in tokens:
        if resultado:
            anterior = resultado[-1]
            if anterior.tipo in TIPOS_QUE_CIERRAN and token.tipo in TIPOS_QUE_ABREN:
                resultado.append(
                    Token(TipoToken.CONCAT, ".", token.posicion, implicito=True)
                )
        resultado.append(token)

    return resultado


def validar(tokens: List[Token], expresion: str = "") -> None:
    """
    Verifica que la secuencia de tokens forme una expresión bien construida.
    """
    profundidad = 0

    for indice, token in enumerate(tokens):
        anterior = tokens[indice - 1] if indice > 0 else None
        siguiente = tokens[indice + 1] if indice + 1 < len(tokens) else None

        if token.tipo == TipoToken.PAREN_IZQ:
            profundidad += 1
            if siguiente is not None and siguiente.tipo == TipoToken.PAREN_DER:
                raise ErrorDeSintaxis(
                    "Grupo vacío: '()' no es una expresión válida.",
                    expresion,
                    token.posicion,
                )

        elif token.tipo == TipoToken.PAREN_DER:
            profundidad -= 1
            if profundidad < 0:
                raise ErrorDeSintaxis(
                    "Hay un paréntesis de cierre sin su pareja de apertura.",
                    expresion,
                    token.posicion,
                )

        elif token.tipo in TIPOS_UNARIOS:
            # Un operador unario necesita un operando a su izquierda.
            if anterior is None or anterior.tipo not in TIPOS_QUE_CIERRAN:
                raise ErrorDeSintaxis(
                    f"El operador '{token.valor}' no tiene un operando a su izquierda.",
                    expresion,
                    token.posicion,
                )

        elif token.tipo in TIPOS_BINARIOS:
            # Un operador binario necesita operandos a ambos lados.
            if anterior is None or anterior.tipo not in TIPOS_QUE_CIERRAN:
                raise ErrorDeSintaxis(
                    f"El operador '{token.valor}' no tiene un operando a su izquierda.",
                    expresion,
                    token.posicion,
                )
            if siguiente is None or siguiente.tipo not in TIPOS_QUE_ABREN:
                raise ErrorDeSintaxis(
                    f"El operador '{token.valor}' no tiene un operando a su derecha.",
                    expresion,
                    token.posicion,
                )

    if profundidad > 0:
        raise ErrorDeSintaxis(
            f"Quedaron {profundidad} paréntesis sin cerrar.",
            expresion,
            len(expresion) - 1 if expresion else -1,
        )


def preparar(expresion: str) -> List[Token]:
    """
    Ejecuta las tres etapas léxicas en orden: tokenizar, insertar
    concatenación implícita y validar.
    """
    tokens = tokenizar(expresion)
    tokens = insertar_concatenacion(tokens)
    validar(tokens, expresion)
    return tokens


def tokens_a_texto(tokens: List[Token]) -> str:
    """Reconstruye una cadena legible a partir de una lista de tokens."""
    return "".join(token.texto() for token in tokens)


def alfabeto_de(tokens: List[Token]) -> set:
    """
    Devuelve el alfabeto de la expresión: los símbolos que realmente
    consumen entrada. Epsilon queda excluido por definición.
    """
    return {token.valor for token in tokens if token.tipo == TipoToken.SIMBOLO}
