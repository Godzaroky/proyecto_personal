"""
Objeto que codifica un AFN.

Un AFN se representa con la quíntupla (Q, Σ, δ, q0, F):

    estados      Q   conjunto de enteros
    alfabeto     Σ   conjunto de símbolos, NUNCA incluye epsilon
    transiciones δ   dict[estado][símbolo] -> conjunto de estados destino
    inicial      q0  un estado
    aceptacion   F   conjunto de estados

La construcción de Thompson produce siempre un único estado de
aceptación, pero F se guarda como conjunto para que el objeto siga
sirviendo si más adelante se combinan autómatas.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Set

from ..errores import ErrorDeAutomata
from ..tokens import EPSILON


class AFN:
    """Autómata finito no determinista con transiciones epsilon."""

    def __init__(self, inicial: int, aceptacion: Iterable[int]):
        self.estados: Set[int] = set()
        self.alfabeto: Set[str] = set()
        self.transiciones: Dict[int, Dict[str, Set[int]]] = {}
        self.inicial: int = inicial
        self.aceptacion: Set[int] = set(aceptacion)

        self.estados.add(inicial)
        self.estados.update(self.aceptacion)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def agregar_estado(self, estado: int) -> None:
        self.estados.add(estado)

    def agregar_transicion(self, origen: int, simbolo: str, destino: int) -> None:
        """
        Registra una transición. Si el símbolo es epsilon no se agrega al
        alfabeto, porque epsilon no es parte del lenguaje de entrada.
        """
        self.estados.add(origen)
        self.estados.add(destino)

        if simbolo != EPSILON:
            self.alfabeto.add(simbolo)

        self.transiciones.setdefault(origen, {}).setdefault(simbolo, set()).add(destino)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def destinos(self, estado: int, simbolo: str) -> Set[int]:
        """Estados alcanzables desde `estado` consumiendo `simbolo`."""
        return set(self.transiciones.get(estado, {}).get(simbolo, set()))

    def cerradura_epsilon(self, estados: Iterable[int]) -> FrozenSet[int]:
        """
        Cerradura epsilon: todos los estados alcanzables desde el conjunto
        dado usando únicamente transiciones epsilon, incluyendo los
        estados de partida.

        Se devuelve un frozenset para que el resultado pueda usarse
        directamente como clave de diccionario en la construcción de
        subconjuntos.
        """
        resultado: Set[int] = set(estados)
        pendientes: List[int] = list(resultado)

        while pendientes:
            actual = pendientes.pop()
            for destino in self.transiciones.get(actual, {}).get(EPSILON, set()):
                if destino not in resultado:
                    resultado.add(destino)
                    pendientes.append(destino)

        return frozenset(resultado)

    def mover(self, estados: Iterable[int], simbolo: str) -> FrozenSet[int]:
        """
        Función move: estados alcanzables desde el conjunto dado
        consumiendo exactamente un `simbolo`, sin aplicar cerradura.
        """
        if simbolo == EPSILON:
            raise ErrorDeAutomata(
                "mover() no acepta epsilon; use cerradura_epsilon()."
            )

        resultado: Set[int] = set()
        for estado in estados:
            resultado |= self.transiciones.get(estado, {}).get(simbolo, set())

        return frozenset(resultado)

    def es_aceptacion(self, estados: Iterable[int]) -> bool:
        """True si alguno de los estados dados es de aceptación."""
        return bool(set(estados) & self.aceptacion)

    # ------------------------------------------------------------------
    # Presentación y serialización
    # ------------------------------------------------------------------

    def simbolos_de(self, estado: int) -> List[str]:
        """Símbolos con transición saliente desde un estado, ordenados."""
        return sorted(self.transiciones.get(estado, {}).keys())

    def a_diccionario(self) -> dict:
        """
        Representación serializable del AFN, apta para volcarse a JSON.
        Los conjuntos se convierten a listas ordenadas para que la salida
        sea estable entre corridas.
        """
        return {
            "tipo": "AFN",
            "estados": sorted(self.estados),
            "alfabeto": sorted(self.alfabeto),
            "inicial": self.inicial,
            "aceptacion": sorted(self.aceptacion),
            "transiciones": [
                {"origen": origen, "simbolo": simbolo, "destinos": sorted(destinos)}
                for origen in sorted(self.transiciones)
                for simbolo, destinos in sorted(self.transiciones[origen].items())
            ],
        }

    def tabla_transiciones(self) -> str:
        """Tabla de transiciones en texto, con epsilon en su propia columna."""
        columnas = sorted(self.alfabeto) + [EPSILON]
        ancho = max(12, max((len(c) for c in columnas), default=1) + 2)

        encabezado = f"{'Estado':>8} |" + "".join(f"{c:^{ancho}}|" for c in columnas)
        lineas = [encabezado, "-" * len(encabezado)]

        for estado in sorted(self.estados):
            marca = ""
            if estado == self.inicial:
                marca += "->"
            if estado in self.aceptacion:
                marca += "*"

            fila = f"{marca + 'q' + str(estado):>8} |"
            for simbolo in columnas:
                destinos = sorted(self.transiciones.get(estado, {}).get(simbolo, set()))
                celda = "{" + ",".join(f"q{d}" for d in destinos) + "}" if destinos else "-"
                fila += f"{celda:^{ancho}}|"
            lineas.append(fila)

        lineas.append("-" * len(encabezado))
        lineas.append("-> estado inicial    * estado de aceptación")
        return "\n".join(lineas)

    def __repr__(self) -> str:
        return (
            f"AFN(estados={len(self.estados)}, "
            f"alfabeto={sorted(self.alfabeto)}, "
            f"inicial=q{self.inicial}, "
            f"aceptacion={sorted(self.aceptacion)})"
        )
