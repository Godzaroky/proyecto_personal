"""
Objeto que codifica un AFD.

Un AFD se representa con la quíntupla (Q, Σ, δ, q0, F), igual que el AFN,
salvo que δ es una función y no una relación:

    transiciones δ   dict[estado][símbolo] -> un solo estado destino

El AFD puede ser parcial: si un estado no tiene transición definida para
un símbolo, la simulación rechaza la cadena en ese punto. La minimización
de Hopcroft sí necesita un autómata completo, así que para eso
existe completar(), que agrega un estado sumidero.

Además se guarda `origen`, un diccionario opcional que dice de qué
conjunto salió cada estado: el subconjunto de estados del AFN en la
construcción por subconjuntos, o el conjunto de posiciones en la
construcción directa.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from ..errores import ErrorDeAutomata

# Nombre del estado sumidero cuando se completa un AFD parcial.
ESTADO_SUMIDERO = -1


class AFD:
    """Autómata finito determinista."""

    def __init__(self, inicial: int, aceptacion: Iterable[int] = ()):
        self.estados: Set[int] = set()
        self.alfabeto: Set[str] = set()
        self.transiciones: Dict[int, Dict[str, int]] = {}
        self.inicial: int = inicial
        self.aceptacion: Set[int] = set(aceptacion)
        self.origen: Dict[int, frozenset] = {}

        self.estados.add(inicial)
        self.estados.update(self.aceptacion)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def agregar_estado(self, estado: int, de_aceptacion: bool = False) -> None:
        self.estados.add(estado)
        if de_aceptacion:
            self.aceptacion.add(estado)

    def agregar_transicion(self, origen: int, simbolo: str, destino: int) -> None:
        existente = self.transiciones.get(origen, {}).get(simbolo)
        if existente is not None and existente != destino:
            raise ErrorDeAutomata(
                f"Transición no determinista: q{origen} con '{simbolo}' "
                f"ya apunta a q{existente} y se intentó apuntar a q{destino}."
            )

        self.estados.add(origen)
        self.estados.add(destino)
        self.alfabeto.add(simbolo)
        self.transiciones.setdefault(origen, {})[simbolo] = destino

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def delta(self, estado: int, simbolo: str) -> Optional[int]:
        """Estado destino, o None si la transición no está definida."""
        return self.transiciones.get(estado, {}).get(simbolo)

    def es_completo(self) -> bool:
        """True si todo estado tiene transición para todo símbolo."""
        return all(
            self.delta(estado, simbolo) is not None
            for estado in self.estados
            for simbolo in self.alfabeto
        )

    def estados_alcanzables(self) -> Set[int]:
        """Estados alcanzables desde el inicial mediante alguna cadena."""
        alcanzables: Set[int] = {self.inicial}
        pendientes: List[int] = [self.inicial]

        while pendientes:
            actual = pendientes.pop()
            for destino in self.transiciones.get(actual, {}).values():
                if destino not in alcanzables:
                    alcanzables.add(destino)
                    pendientes.append(destino)

        return alcanzables

    # ------------------------------------------------------------------
    # Transformaciones
    # ------------------------------------------------------------------

    def completar(self, sumidero: int = ESTADO_SUMIDERO) -> "AFD":
        """
        Devuelve una copia completa del AFD, agregando un estado sumidero
        no final que absorbe todas las transiciones faltantes.

        Si el autómata ya es completo se devuelve una copia sin sumidero,
        para no ensuciarlo con un estado inútil.
        """
        copia = self.copiar()
        if copia.es_completo():
            return copia

        copia.agregar_estado(sumidero)
        for estado in sorted(copia.estados):
            for simbolo in sorted(copia.alfabeto):
                if copia.delta(estado, simbolo) is None:
                    copia.agregar_transicion(estado, simbolo, sumidero)

        return copia

    def copiar(self) -> "AFD":
        """Copia profunda del autómata."""
        nuevo = AFD(self.inicial, self.aceptacion)
        nuevo.estados = set(self.estados)
        nuevo.alfabeto = set(self.alfabeto)
        nuevo.transiciones = {
            origen: dict(destinos) for origen, destinos in self.transiciones.items()
        }
        nuevo.origen = dict(self.origen)
        return nuevo

    # ------------------------------------------------------------------
    # Presentación y serialización
    # ------------------------------------------------------------------

    def a_diccionario(self) -> dict:
        """Representación serializable del AFD, apta para volcarse a JSON."""
        datos = {
            "tipo": "AFD",
            "estados": sorted(self.estados),
            "alfabeto": sorted(self.alfabeto),
            "inicial": self.inicial,
            "aceptacion": sorted(self.aceptacion),
            "transiciones": [
                {"origen": origen, "simbolo": simbolo, "destino": destino}
                for origen in sorted(self.transiciones)
                for simbolo, destino in sorted(self.transiciones[origen].items())
            ],
        }

        if self.origen:
            datos["origen"] = {
                str(estado): sorted(conjunto)
                for estado, conjunto in sorted(self.origen.items())
            }

        return datos

    def tabla_transiciones(self) -> str:
        """Tabla de transiciones en texto."""
        columnas = sorted(self.alfabeto)
        ancho = max(8, max((len(c) for c in columnas), default=1) + 2)

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
                destino = self.delta(estado, simbolo)
                celda = f"q{destino}" if destino is not None else "-"
                fila += f"{celda:^{ancho}}|"
            lineas.append(fila)

        lineas.append("-" * len(encabezado))
        lineas.append("-> estado inicial    * estado de aceptación")
        return "\n".join(lineas)

    def __repr__(self) -> str:
        return (
            f"AFD(estados={len(self.estados)}, "
            f"alfabeto={sorted(self.alfabeto)}, "
            f"inicial=q{self.inicial}, "
            f"aceptacion={sorted(self.aceptacion)})"
        )
