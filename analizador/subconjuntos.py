"""
Construcción de subconjuntos: AFN -> AFD.

Cada estado del AFD es un subconjunto de estados del AFN cerrado bajo
transiciones epsilon. El algoritmo parte de la cerradura epsilon del
estado inicial del AFN y, por cada símbolo del alfabeto, calcula el
subconjunto destino con `cerradura_epsilon(mover(T, a))`. Los
subconjuntos nuevos entran a una cola y el proceso termina cuando no
aparecen más.

Un subconjunto del AFD es de aceptación si contiene **algún** estado de
aceptación del AFN.

Si `cerradura_epsilon(mover(T, a))` sale vacío no se crea ningún estado:
el AFD queda parcial y la simulación rechaza al no encontrar transición.
Para los algoritmos que necesitan un autómata total —la minimización de
Hopcroft, por ejemplo— existe `AFD.completar()`, que agrega el sumidero.

El recorrido es en anchura y los símbolos se visitan en orden, así que
la numeración de los estados es estable entre corridas. Esto importa
porque las tablas y los dibujos del reporte deben poder regenerarse
iguales.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, FrozenSet

from .automatas.afd import AFD
from .automatas.afn import AFN


def construir(afn: AFN) -> AFD:
    """Convierte un AFN en el AFD equivalente por construcción de subconjuntos."""
    alfabeto = sorted(afn.alfabeto)

    inicial = afn.cerradura_epsilon({afn.inicial})
    numero: Dict[FrozenSet[int], int] = {inicial: 0}

    afd = AFD(inicial=0)
    # El alfabeto se fija de una vez: aunque algún símbolo no llegue a
    # usarse, debe aparecer como columna en la tabla de transiciones.
    afd.alfabeto.update(alfabeto)
    afd.origen[0] = inicial
    if afn.es_aceptacion(inicial):
        afd.aceptacion.add(0)

    pendientes: Deque[FrozenSet[int]] = deque([inicial])

    while pendientes:
        conjunto = pendientes.popleft()
        origen = numero[conjunto]

        for simbolo in alfabeto:
            destino = afn.cerradura_epsilon(afn.mover(conjunto, simbolo))

            # Subconjunto vacío: el AFD se queda parcial a propósito.
            if not destino:
                continue

            if destino not in numero:
                identificador = len(numero)
                numero[destino] = identificador
                afd.origen[identificador] = destino
                afd.agregar_estado(
                    identificador, de_aceptacion=afn.es_aceptacion(destino)
                )
                pendientes.append(destino)

            afd.agregar_transicion(origen, simbolo, numero[destino])

    return afd


def listado_de_estados(afd: AFD) -> str:
    """
    Texto con cada estado del AFD y el subconjunto de estados del AFN
    que lo originó. Es el "listado de estados y las posiciones que
    conforma cada uno" que pide el enunciado.
    """
    lineas = []
    for estado in sorted(afd.estados):
        marca = ""
        if estado == afd.inicial:
            marca += "->"
        if estado in afd.aceptacion:
            marca += "*"

        conjunto = afd.origen.get(estado)
        if conjunto is None:
            detalle = "(sin origen registrado)"
        else:
            detalle = "{" + ", ".join(f"q{n}" for n in sorted(conjunto)) + "}"

        lineas.append(f"  {marca + 'A' + str(estado):>8} = {detalle}")

    return "\n".join(lineas)
