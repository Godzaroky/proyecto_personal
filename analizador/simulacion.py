"""
Simulación de autómatas.

Dada una cadena `w`, decide si cada autómata la acepta. Son las
funciones que responden la pregunta del enunciado: "¿pertenece `w` al
lenguaje de la expresión regular `r`?".

La diferencia entre los dos modos de simulación:

    AFN   se sigue un **conjunto** de estados a la vez. En cada símbolo
          se aplica `cerradura_epsilon(mover(actuales, símbolo))`. La
          cadena se acepta si el conjunto final toca algún estado de
          aceptación.
    AFD   se sigue **un solo** estado. En cada símbolo se consulta
          `delta`, y si devuelve `None` la cadena se rechaza ahí mismo.

Ese `None` no es un caso de borde sino parte del diseño: tanto el AFD de
la construcción de subconjuntos como el mínimo de Hopcroft se dejan
**parciales** a propósito (ver CLAUDE.md), así que la ausencia de
transición **es** el rechazo.

Los tres autómatas del pipeline reconocen el mismo lenguaje, de modo que
correr `w` sobre los tres y comparar es la verificación más fuerte que
tiene el proyecto. `simular()` la hace explícita.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Set

from .automatas.afd import AFD
from .automatas.afn import AFN


# ----------------------------------------------------------------------
# Recorridos: la traza completa, útil para explicar la simulación
# ----------------------------------------------------------------------


def recorrido_afn(afn: AFN, cadena: str) -> List[FrozenSet[int]]:
    """
    Conjuntos de estados por los que pasa el AFN, empezando por la
    cerradura epsilon del inicial. Tiene `len(cadena) + 1` elementos; un
    conjunto vacío marca el punto donde la simulación se quedó sin
    estados.

    Un símbolo que no está en el alfabeto no puede consumirse y deja el
    conjunto vacío. El caso hay que atajarlo antes de llamar a `mover`
    porque `w` puede traer el carácter `ε` —el usuario que lo teclea
    creyendo que significa "cadena vacía"— y `mover` lo rechaza con una
    excepción. Para la simulación no es un error del programa sino una
    cadena que no pertenece al lenguaje.
    """
    actuales = afn.cerradura_epsilon({afn.inicial})
    pasos = [actuales]

    for caracter in cadena:
        if caracter in afn.alfabeto:
            actuales = afn.cerradura_epsilon(afn.mover(actuales, caracter))
        else:
            actuales = frozenset()
        pasos.append(actuales)

    return pasos


def recorrido_afd(afd: AFD, cadena: str) -> List[Optional[int]]:
    """
    Estados por los que pasa el AFD. Un `None` marca el punto donde la
    transición no existía y la simulación murió; a partir de ahí no se
    agregan más pasos.
    """
    actual: Optional[int] = afd.inicial
    pasos: List[Optional[int]] = [actual]

    for caracter in cadena:
        actual = afd.delta(actual, caracter)
        pasos.append(actual)
        if actual is None:
            break

    return pasos


# ----------------------------------------------------------------------
# Aceptación
# ----------------------------------------------------------------------


def acepta_afn(afn: AFN, cadena: str) -> bool:
    """True si el AFN acepta la cadena."""
    return afn.es_aceptacion(recorrido_afn(afn, cadena)[-1])


def acepta_afd(afd: AFD, cadena: str) -> bool:
    """
    True si el AFD acepta la cadena. Si la simulación murió por falta de
    transición —el AFD es parcial— la respuesta es False.
    """
    final = recorrido_afd(afd, cadena)[-1]
    return final is not None and final in afd.aceptacion


def simbolos_desconocidos(automata, cadena: str) -> Set[str]:
    """
    Símbolos de la cadena que no pertenecen al alfabeto del autómata.
    No cambian el resultado —la cadena se rechaza igual— pero permiten
    avisarle al usuario que se equivocó al escribirla.
    """
    return {caracter for caracter in cadena if caracter not in automata.alfabeto}


# ----------------------------------------------------------------------
# Comparación de los tres autómatas
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Resultado:
    """Veredicto de cada autómata sobre una misma cadena."""

    cadena: str
    afn: bool
    afd: bool
    minimo: bool

    @property
    def coinciden(self) -> bool:
        """
        True si los tres autómatas dieron la misma respuesta. Como los
        tres deben reconocer el mismo lenguaje, un False aquí es un bug.
        """
        return self.afn == self.afd == self.minimo

    @property
    def acepta(self) -> bool:
        """Veredicto final; solo es de fiar cuando `coinciden` es True."""
        return self.afn


def simular(afn: AFN, afd: AFD, minimo: AFD, cadena: str) -> Resultado:
    """Corre la cadena sobre los tres autómatas del pipeline."""
    return Resultado(
        cadena=cadena,
        afn=acepta_afn(afn, cadena),
        afd=acepta_afd(afd, cadena),
        minimo=acepta_afd(minimo, cadena),
    )


def formatear(resultado: Resultado) -> str:
    """Texto del resultado de la simulación, para consola y para el reporte."""
    def marca(valor: bool) -> str:
        return "sí" if valor else "no"

    mostrada = repr(resultado.cadena) if resultado.cadena else "(vacía)"
    lineas = [
        f"  Cadena w = {mostrada}",
        f"    AFN (Thompson)      : {marca(resultado.afn)}",
        f"    AFD (subconjuntos)  : {marca(resultado.afd)}",
        f"    AFD mínimo          : {marca(resultado.minimo)}",
    ]

    if resultado.coinciden:
        veredicto = "PERTENECE" if resultado.acepta else "NO pertenece"
        lineas.append(f"    -> w {veredicto} al lenguaje (los tres coinciden)")
    else:
        lineas.append("    -> ¡DISCREPANCIA! Los autómatas no coinciden: hay un bug.")

    return "\n".join(lineas)
