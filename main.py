#!/usr/bin/env python3
"""
Proyecto #1 - Analizador léxico
Teoría de la Computación (CC2019), Sección 30

Lee un archivo con una expresión regular por línea y, para cada una,
muestra la tokenización, el postfix, el árbol sintáctico, el AFN de
Thompson, el AFD por subconjuntos y el AFD mínimo de Hopcroft.

Si además se indica una cadena w, la simula sobre los tres autómatas y
reporta si pertenece al lenguaje.

Uso:
    python3 main.py [archivo] [cadena]

Si no se indica archivo se usa expresiones.txt. Para simular la cadena
vacía se pasa una cadena vacía explícita:

    python3 main.py expresiones.txt ""
"""

import sys
from pathlib import Path
from typing import List, Optional

# En Windows la consola suele usar cp1252, que no puede imprimir ε, ├, └, etc.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from analizador.arbol import a_texto, construir, numerar_posiciones
from analizador.errores import ErrorAnalizador
from analizador.shunting_yard import a_postfix
from analizador.hopcroft import construir_con_bloques, listado_de_bloques
from analizador.simulacion import formatear, simbolos_desconocidos, simular
from analizador.subconjuntos import construir as construir_afd, listado_de_estados
from analizador.thompson import construir as construir_afn
from analizador.tokens import alfabeto_de, preparar, tokens_a_texto

ANCHO = 72

# Carpeta donde vive main.py. El archivo de expresiones se busca aquí
# cuando no se encuentra en el directorio actual, para que el programa
# funcione igual sin importar desde dónde se invoque.
AQUI = Path(__file__).resolve().parent
ARCHIVO_POR_OMISION = "expresiones.txt"


def separador(caracter: str = "=") -> str:
    return caracter * ANCHO


def encabezado() -> None:
    print(separador())
    print("PROYECTO #1 - ANALIZADOR LÉXICO")
    print("Teoría de la Computación (CC2019), Sección 30")
    print(separador())
    print("Integrantes:")
    print("  Jorge Morales    - 24284")
    print("  Javier Castillo  - 24014")
    print("  Diego Gonzalez   - 24170")
    print(separador())


def procesar(expresion: str, numero: int, cadena: Optional[str] = None) -> None:
    """
    Ejecuta el pipeline completo sobre una expresión regular. Si se
    indica una cadena, además la simula sobre los tres autómatas.
    """
    print()
    print(separador())
    print(f"EXPRESIÓN #{numero}: {expresion}")
    print(separador())

    # Fase 1a: tokenización, concatenación implícita y validación.
    tokens = preparar(expresion)
    print(f"Con concatenación explícita : {tokens_a_texto(tokens)}")
    print(f"Alfabeto                    : {{{', '.join(sorted(alfabeto_de(tokens)))}}}")

    # Fase 1b: Shunting Yard.
    postfix = a_postfix(tokens, expresion)
    print(f"Postfix                     : {tokens_a_texto(postfix)}")

    # Fase 1c: árbol sintáctico y numeración de posiciones.
    raiz = construir(postfix)
    posiciones = numerar_posiciones(raiz)

    print()
    print("Árbol sintáctico:")
    print(a_texto(raiz))

    print()
    print("Posiciones de los símbolos:")
    if posiciones:
        for numero_posicion, simbolo in posiciones:
            print(f"  {numero_posicion}: '{simbolo}'")
    else:
        print("  (ninguna: la expresión solo genera la cadena vacía)")

    # Fase 2: construcción de Thompson (regex -> AFN).
    afn = construir_afn(raiz)
    print()
    print(f"AFN de Thompson: {afn!r}")
    print(afn.tabla_transiciones())

    # Fase 3: construcción de subconjuntos (AFN -> AFD).
    afd = construir_afd(afn)
    print()
    print(f"AFD por subconjuntos: {afd!r}")
    print(afd.tabla_transiciones())
    print()
    print("Estados del AFD y el subconjunto del AFN que los origina:")
    print(listado_de_estados(afd))

    # Fase 4: minimización con Hopcroft.
    minimo, bloques = construir_con_bloques(afd)
    print()
    print(f"AFD mínimo (Hopcroft): {minimo!r}")
    print(f"Reducción: {len(afd.estados)} estados -> {len(minimo.estados)}")
    print(minimo.tabla_transiciones())
    print()
    print("Estados del AFD mínimo y los estados del AFD que se fundieron:")
    print(listado_de_bloques(bloques))

    # Fase 5: simulación de la cadena w sobre los tres autómatas.
    if cadena is None:
        return

    print()
    print("Simulación:")

    desconocidos = simbolos_desconocidos(afn, cadena)
    if desconocidos:
        ajenos = ", ".join(repr(s) for s in sorted(desconocidos))
        print(f"  [aviso] w usa símbolos fuera del alfabeto: {ajenos}")

    print(formatear(simular(afn, afd, minimo, cadena)))


def resolver_ruta(nombre: str) -> Path:
    """
    Ubica el archivo de expresiones.

    Se prueba primero tal como se escribió, relativo al directorio desde
    el que se invocó el programa. Si ahí no está, se busca junto a
    main.py: así `python main.py` funciona aunque se ejecute desde otra
    carpeta o desde un IDE con otro directorio de trabajo.

    Si no aparece en ninguno de los dos lugares se devuelve la ruta
    original, para que el error mencione lo que el usuario escribió.
    """
    candidata = Path(nombre)
    if candidata.is_file():
        return candidata

    junto_al_programa = AQUI / candidata
    if junto_al_programa.is_file():
        return junto_al_programa

    return candidata


def leer_expresiones(ruta: Path) -> List[str]:
    """Lee el archivo y devuelve las líneas no vacías."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        return [linea.strip() for linea in archivo if linea.strip()]


def main() -> int:
    solicitado = sys.argv[1] if len(sys.argv) > 1 else ARCHIVO_POR_OMISION
    # Se distingue "no se pidió simular" de "simular la cadena vacía".
    cadena = sys.argv[2] if len(sys.argv) > 2 else None

    ruta = resolver_ruta(solicitado)

    encabezado()

    try:
        expresiones = leer_expresiones(ruta)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo '{solicitado}'.")
        desde_aqui = Path(solicitado).resolve()
        junto_al_programa = (AQUI / solicitado).resolve()
        print(f"        Se buscó en : {desde_aqui}")
        if junto_al_programa != desde_aqui:
            print(f"        y también en: {junto_al_programa}")
        return 1
    except OSError as error:
        print(f"[ERROR] No se pudo leer '{solicitado}': {error}")
        return 1

    print(f"Archivo    : {ruta}")
    print(f"Expresiones: {len(expresiones)}")
    if cadena is not None:
        print(f"Cadena w   : {cadena!r}" if cadena else "Cadena w   : (vacía)")

    fallidas = 0
    for numero, expresion in enumerate(expresiones, start=1):
        try:
            procesar(expresion, numero, cadena)
        except ErrorAnalizador as error:
            fallidas += 1
            print()
            print(separador())
            print(f"EXPRESIÓN #{numero}: {expresion}")
            print(separador())
            print(f"[ERROR] {error}")

    print()
    print(separador())
    print(f"Procesadas {len(expresiones) - fallidas} de {len(expresiones)} expresiones.")
    print(separador())

    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
