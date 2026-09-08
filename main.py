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
    python3 main.py [archivo] [cadena] [--html] [--salida RUTA]

Si no se indica archivo se usa expresiones.txt. Para simular la cadena
vacía se pasa una cadena vacía explícita:

    python3 main.py expresiones.txt ""

Con --html el resultado se escribe como página web en vez de volcarse a
la consola. Ese archivo se abre en cualquier navegador y desde ahí se
obtiene un PDF con "Imprimir → Guardar como PDF".
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# En Windows la consola suele usar cp1252, que no puede imprimir ε, ├, └, etc.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from analizador.hopcroft import listado_de_bloques
from analizador.reporte import Analisis, a_html, analizar
from analizador.simulacion import formatear
from analizador.subconjuntos import listado_de_estados

ANCHO = 72

# Carpeta donde vive main.py. El archivo de expresiones se busca aquí
# cuando no se encuentra en el directorio actual, para que el programa
# funcione igual sin importar desde dónde se invoque.
AQUI = Path(__file__).resolve().parent
ARCHIVO_POR_OMISION = "expresiones.txt"
REPORTE_POR_OMISION = "salida/reporte.html"


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


def imprimir(analisis: Analisis, numero: int) -> None:
    """Vuelca a la consola todo lo que el pipeline produjo."""
    print()
    print(separador())
    print(f"EXPRESIÓN #{numero}: {analisis.expresion}")
    print(separador())

    if not analisis.valido:
        print(f"[ERROR] {analisis.error}")
        return

    print(f"Con concatenación explícita : {analisis.con_concatenacion}")
    print(f"Alfabeto                    : {{{', '.join(analisis.alfabeto)}}}")
    print(f"Postfix                     : {analisis.postfix}")

    print()
    print("Árbol sintáctico:")
    print(analisis.arbol)

    print()
    print("Posiciones de los símbolos:")
    if analisis.posiciones:
        for posicion, simbolo in analisis.posiciones:
            print(f"  {posicion}: '{simbolo}'")
    else:
        print("  (ninguna: la expresión solo genera la cadena vacía)")

    print()
    print(f"AFN de Thompson: {analisis.afn!r}")
    print(analisis.afn.tabla_transiciones())

    print()
    print(f"AFD por subconjuntos: {analisis.afd!r}")
    print(analisis.afd.tabla_transiciones())
    print()
    print("Estados del AFD y el subconjunto del AFN que los origina:")
    print(listado_de_estados(analisis.afd))

    print()
    print(f"AFD mínimo (Hopcroft): {analisis.minimo!r}")
    print(
        f"Reducción: {len(analisis.afd.estados)} estados -> "
        f"{len(analisis.minimo.estados)}"
    )
    print(analisis.minimo.tabla_transiciones())
    print()
    print("Estados del AFD mínimo y los estados del AFD que se fundieron:")
    print(listado_de_bloques(analisis.bloques))

    if analisis.resultado is None:
        return

    print()
    print("Simulación:")
    if analisis.desconocidos:
        ajenos = ", ".join(repr(s) for s in analisis.desconocidos)
        print(f"  [aviso] w usa símbolos fuera del alfabeto: {ajenos}")
    print(formatear(analisis.resultado))


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


def escribir_reporte(
    destino: str,
    analisis: List[Analisis],
    cadena: Optional[str],
    archivo: str,
) -> Path:
    """Genera el reporte HTML y lo guarda, creando la carpeta si hace falta."""
    ruta = Path(destino)
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(a_html(analisis, cadena, archivo), encoding="utf-8")
    return ruta


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analizador léxico: expresión regular -> AFN -> AFD -> AFD mínimo.",
        epilog="Con --html el reporte se abre en el navegador y de ahí se "
        'obtiene un PDF con "Imprimir -> Guardar como PDF".',
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        default=ARCHIVO_POR_OMISION,
        help="archivo con una expresión regular por línea (por omisión: expresiones.txt)",
    )
    parser.add_argument(
        "cadena",
        nargs="?",
        default=None,
        help='cadena w a simular; para la cadena vacía se pasa ""',
    )
    # Son dos banderas y no una con valor opcional a propósito: con
    # `--html [RUTA]` argparse no puede distinguir la ruta del reporte
    # del archivo de expresiones, y el orden de los argumentos pasaría a
    # cambiar el significado del comando.
    parser.add_argument(
        "--html",
        action="store_true",
        help=f"escribe un reporte HTML en vez de volcar todo a la consola "
        f"(por omisión en {REPORTE_POR_OMISION})",
    )
    parser.add_argument(
        "--salida",
        default=None,
        metavar="RUTA",
        help="ruta del reporte HTML; implica --html",
    )
    return parser


def main() -> int:
    argumentos = construir_parser().parse_args()
    solicitado = argumentos.archivo
    ruta = resolver_ruta(solicitado)

    # Indicar la ruta de salida implica querer el reporte.
    destino_html = argumentos.salida or (
        REPORTE_POR_OMISION if argumentos.html else None
    )

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
    if argumentos.cadena is not None:
        print(
            f"Cadena w   : {argumentos.cadena!r}"
            if argumentos.cadena
            else "Cadena w   : (vacía)"
        )

    analisis = [analizar(expresion, argumentos.cadena) for expresion in expresiones]
    fallidas = sum(1 for uno in analisis if not uno.valido)

    if destino_html is None:
        for numero, uno in enumerate(analisis, start=1):
            imprimir(uno, numero)
    else:
        # Con --html la consola solo resume; el detalle va al archivo.
        print()
        for numero, uno in enumerate(analisis, start=1):
            if uno.valido:
                print(
                    f"  #{numero} {uno.expresion:<24} "
                    f"AFN {len(uno.afn.estados):>3}  "
                    f"AFD {len(uno.afd.estados):>3}  "
                    f"mínimo {len(uno.minimo.estados):>3}"
                )
            else:
                print(f"  #{numero} {uno.expresion:<24} error de sintaxis")

        try:
            destino = escribir_reporte(
                destino_html, analisis, argumentos.cadena, str(ruta)
            )
        except OSError as error:
            print(f"\n[ERROR] No se pudo escribir el reporte: {error}")
            return 1

        print()
        print(f"Reporte escrito en: {destino}")
        print("Ábrelo en el navegador; para PDF usa Imprimir -> Guardar como PDF.")

    print()
    print(separador())
    print(f"Procesadas {len(expresiones) - fallidas} de {len(expresiones)} expresiones.")
    print(separador())

    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
