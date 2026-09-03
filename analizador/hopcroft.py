"""
Minimización de AFD por el algoritmo de Hopcroft.

El algoritmo parte de la partición gruesa {finales, no finales} y la va
refinando: mientras exista un bloque `A` en la lista de pendientes y un
símbolo `c` tales que los predecesores de `A` por `c` parten en dos a
algún bloque `Y` de la partición, se reemplaza `Y` por sus dos mitades.
Cuando ningún símbolo distingue estados dentro de un bloque, cada bloque
es una clase de equivalencia de Myhill-Nerode y se vuelve un estado del
AFD mínimo.

Refinar exige que `delta` esté definida siempre, así que se trabaja
sobre `AFD.completar()`. Antes de completar se podan los estados
inalcanzables: un estado que no se alcanza desde el inicial no pertenece
a ninguna clase útil y solo ensuciaría la partición.

El detalle que hace a esto Hopcroft y no Moore está en el refinamiento:
cuando un bloque `Y` se parte y `Y` no estaba pendiente, se encola
únicamente **la mitad más pequeña**. Es lo que da la cota O(n log n) en
lugar de O(n²).

Sobre el sumidero: el AFD mínimo se devuelve **parcial**, igual que el
que produce la construcción de subconjuntos. El estado de error que
agregó `completar()` —y cualquier estado desde el cual ya no se puede
llegar a un final— se elimina al final. El lenguaje no cambia (la
simulación rechaza igual al no encontrar transición) y las tablas del
reporte no cargan un estado que el enunciado no pide.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, FrozenSet, List, Set, Tuple

from .automatas.afd import AFD


def construir(afd: AFD) -> AFD:
    """Devuelve el AFD mínimo equivalente al AFD dado."""
    minimo, _ = construir_con_bloques(afd)
    return minimo


def construir_con_bloques(afd: AFD) -> Tuple[AFD, Dict[int, FrozenSet[int]]]:
    """
    Igual que `construir`, pero además devuelve el mapeo
    `estado del AFD mínimo -> conjunto de estados del AFD original`
    que se fundieron en él. Es lo que el reporte necesita para mostrar
    qué estados resultaron equivalentes.
    """
    podado = _podar(afd)
    completo = podado.completar()

    particion = _refinar(completo)
    return _construir_minimo(completo, particion)


# ----------------------------------------------------------------------
# Etapas
# ----------------------------------------------------------------------


def _podar(afd: AFD) -> AFD:
    """Copia del AFD que conserva solo los estados alcanzables."""
    alcanzables = afd.estados_alcanzables()

    podado = AFD(afd.inicial)
    podado.alfabeto.update(afd.alfabeto)

    for estado in alcanzables:
        podado.agregar_estado(estado, de_aceptacion=estado in afd.aceptacion)
        if estado in afd.origen:
            podado.origen[estado] = afd.origen[estado]

    for estado in alcanzables:
        for simbolo, destino in afd.transiciones.get(estado, {}).items():
            podado.agregar_transicion(estado, simbolo, destino)

    return podado


def _refinar(afd: AFD) -> Set[FrozenSet[int]]:
    """
    Refinamiento de particiones de Hopcroft sobre un AFD **completo**.
    Devuelve el conjunto de bloques de la partición final.
    """
    # inversa[símbolo][destino] = estados que llegan a `destino` con `símbolo`.
    inversa: Dict[str, Dict[int, Set[int]]] = {}
    for origen, transiciones in afd.transiciones.items():
        for simbolo, destino in transiciones.items():
            inversa.setdefault(simbolo, {}).setdefault(destino, set()).add(origen)

    finales = frozenset(afd.estados & afd.aceptacion)
    no_finales = frozenset(afd.estados - finales)

    particion: Set[FrozenSet[int]] = {b for b in (finales, no_finales) if b}
    pendientes: Set[FrozenSet[int]] = set(particion)

    while pendientes:
        bloque = pendientes.pop()

        for simbolo in sorted(afd.alfabeto):
            predecesores: Set[int] = set()
            for estado in bloque:
                predecesores |= inversa.get(simbolo, {}).get(estado, set())

            if not predecesores:
                continue

            for grupo in list(particion):
                dentro = grupo & predecesores
                fuera = grupo - predecesores

                # El símbolo no distingue nada dentro de este bloque.
                if not dentro or not fuera:
                    continue

                dentro, fuera = frozenset(dentro), frozenset(fuera)
                particion.discard(grupo)
                particion.update((dentro, fuera))

                if grupo in pendientes:
                    pendientes.discard(grupo)
                    pendientes.update((dentro, fuera))
                else:
                    # Solo la mitad más pequeña: esto es lo que hace que
                    # el algoritmo sea O(n log n).
                    pendientes.add(dentro if len(dentro) <= len(fuera) else fuera)

    return particion


def _construir_minimo(
    afd: AFD, particion: Set[FrozenSet[int]]
) -> Tuple[AFD, Dict[int, FrozenSet[int]]]:
    """
    Arma el AFD mínimo a partir de la partición, descartando los bloques
    desde los que ya no se puede llegar a un estado de aceptación.

    Los estados se numeran recorriendo en anchura desde el bloque
    inicial y visitando los símbolos en orden, igual que en la
    construcción de subconjuntos, para que la numeración sea estable
    entre corridas.
    """
    bloque_de: Dict[int, FrozenSet[int]] = {
        estado: bloque for bloque in particion for estado in bloque
    }

    alfabeto = sorted(afd.alfabeto)

    def destino_de(bloque: FrozenSet[int], simbolo: str) -> FrozenSet[int]:
        # Todos los estados del bloque van al mismo bloque destino; con
        # el AFD completo basta consultar cualquiera de ellos.
        representante = next(iter(bloque))
        return bloque_de[afd.transiciones[representante][simbolo]]

    productivos = _bloques_productivos(afd, particion, bloque_de, alfabeto)
    bloque_inicial = bloque_de[afd.inicial]

    minimo = AFD(inicial=0)
    minimo.alfabeto.update(alfabeto)

    # Lenguaje vacío: no hay ningún final alcanzable.
    if bloque_inicial not in productivos:
        return minimo, {0: frozenset()}

    numero: Dict[FrozenSet[int], int] = {bloque_inicial: 0}
    minimo.agregar_estado(0, de_aceptacion=bool(bloque_inicial & afd.aceptacion))
    _registrar_origen(minimo, afd, 0, bloque_inicial)

    pendientes: Deque[FrozenSet[int]] = deque([bloque_inicial])

    while pendientes:
        bloque = pendientes.popleft()
        origen = numero[bloque]

        for simbolo in alfabeto:
            destino = destino_de(bloque, simbolo)

            # Se omite la transición hacia un bloque estéril: así el AFD
            # mínimo queda parcial, sin el sumidero.
            if destino not in productivos:
                continue

            if destino not in numero:
                identificador = len(numero)
                numero[destino] = identificador
                minimo.agregar_estado(
                    identificador, de_aceptacion=bool(destino & afd.aceptacion)
                )
                _registrar_origen(minimo, afd, identificador, destino)
                pendientes.append(destino)

            minimo.agregar_transicion(origen, simbolo, numero[destino])

    bloques = {identificador: bloque for bloque, identificador in numero.items()}
    return minimo, bloques


def _bloques_productivos(
    afd: AFD,
    particion: Set[FrozenSet[int]],
    bloque_de: Dict[int, FrozenSet[int]],
    alfabeto: List[str],
) -> Set[FrozenSet[int]]:
    """
    Bloques desde los que se puede llegar a un estado de aceptación.
    Se calcula por alcanzabilidad inversa desde los bloques finales.
    """
    predecesores: Dict[FrozenSet[int], Set[FrozenSet[int]]] = {
        bloque: set() for bloque in particion
    }

    for bloque in particion:
        representante = next(iter(bloque))
        for simbolo in alfabeto:
            destino = bloque_de[afd.transiciones[representante][simbolo]]
            predecesores[destino].add(bloque)

    productivos: Set[FrozenSet[int]] = {
        bloque for bloque in particion if bloque & afd.aceptacion
    }
    pila = list(productivos)

    while pila:
        bloque = pila.pop()
        for anterior in predecesores[bloque]:
            if anterior not in productivos:
                productivos.add(anterior)
                pila.append(anterior)

    return productivos


def _registrar_origen(
    minimo: AFD, afd: AFD, identificador: int, bloque: FrozenSet[int]
) -> None:
    """
    El `origen` del estado mínimo es la unión de los subconjuntos del AFN
    de los estados que se fundieron. El sumidero no tiene origen y por
    eso se omite.
    """
    union: Set[int] = set()
    for estado in bloque:
        union |= afd.origen.get(estado, frozenset())
    if union:
        minimo.origen[identificador] = frozenset(union)


def listado_de_bloques(bloques: Dict[int, FrozenSet[int]]) -> str:
    """
    Texto con cada estado del AFD mínimo y los estados del AFD original
    que se fundieron en él.
    """
    lineas = []
    for identificador in sorted(bloques):
        miembros = ", ".join(f"A{n}" for n in sorted(bloques[identificador]))
        lineas.append(f"  {'M' + str(identificador):>8} = {{{miembros}}}")
    return "\n".join(lineas)
