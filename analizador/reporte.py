"""
Reporte HTML.

Ejecuta el pipeline completo sobre una expresión regular y arma un
documento HTML autocontenido con todos los resultados: postfix, árbol
sintáctico, tablas de transiciones del AFN, del AFD y del AFD mínimo, y
la simulación de la cadena.

El HTML se genera sin dependencias externas y con el CSS incrustado, de
modo que el archivo funciona solo, sin conexión y sin carpeta de
recursos al lado. Trae además reglas `@media print`, así que el navegador
produce un PDF decente con "Imprimir → Guardar como PDF", una página por
expresión.

`analizar()` es también el punto único donde se encadena el pipeline:
`main.py` lo usa tanto para la salida de consola como para el reporte, de
modo que las dos vistas no puedan desincronizarse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Dict, FrozenSet, List, Optional, Tuple

from .arbol import a_texto, construir as construir_arbol, numerar_posiciones
from .automatas.afd import AFD
from .automatas.afn import AFN
from .errores import ErrorAnalizador
from .hopcroft import construir_con_bloques
from .shunting_yard import a_postfix
from .simulacion import Resultado, simbolos_desconocidos, simular
from .subconjuntos import construir as construir_afd
from .thompson import construir as construir_afn
from .tokens import EPSILON, alfabeto_de, preparar, tokens_a_texto


@dataclass
class Analisis:
    """
    Todo lo que el pipeline produce para una expresión regular.

    Si la expresión estaba mal escrita, `error` trae el mensaje y el
    resto de los campos quedan vacíos.
    """

    expresion: str
    error: Optional[str] = None

    con_concatenacion: str = ""
    alfabeto: List[str] = field(default_factory=list)
    postfix: str = ""
    arbol: str = ""
    posiciones: List[Tuple[int, str]] = field(default_factory=list)

    afn: Optional[AFN] = None
    afd: Optional[AFD] = None
    minimo: Optional[AFD] = None
    bloques: Dict[int, FrozenSet[int]] = field(default_factory=dict)

    resultado: Optional[Resultado] = None
    desconocidos: List[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        return self.error is None


def analizar(expresion: str, cadena: Optional[str] = None) -> Analisis:
    """
    Corre el pipeline completo sobre una expresión regular. Si se indica
    una cadena, además la simula sobre los tres autómatas.

    Los errores de sintaxis no se propagan: quedan registrados en el
    campo `error` para que un archivo con una expresión mala no detenga
    el procesamiento de las demás.
    """
    try:
        tokens = preparar(expresion)
        postfix = a_postfix(tokens, expresion)
        raiz = construir_arbol(postfix)
        posiciones = numerar_posiciones(raiz)

        afn = construir_afn(raiz)
        afd = construir_afd(afn)
        minimo, bloques = construir_con_bloques(afd)

        analisis = Analisis(
            expresion=expresion,
            con_concatenacion=tokens_a_texto(tokens),
            alfabeto=sorted(alfabeto_de(tokens)),
            postfix=tokens_a_texto(postfix),
            arbol=a_texto(raiz),
            posiciones=posiciones,
            afn=afn,
            afd=afd,
            minimo=minimo,
            bloques=bloques,
        )

        if cadena is not None:
            analisis.resultado = simular(afn, afd, minimo, cadena)
            analisis.desconocidos = sorted(simbolos_desconocidos(afn, cadena))

        return analisis

    except ErrorAnalizador as error:
        return Analisis(expresion=expresion, error=str(error))


# ----------------------------------------------------------------------
# Generación del HTML
# ----------------------------------------------------------------------


ESTILO = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0 auto; padding: 2.5rem 1.5rem; max-width: 62rem;
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.55; color: #1a1a1a; background: #fff;
}
h1 { font-size: 1.7rem; margin: 0 0 .3rem; }
h2 {
  font-size: 1.25rem; margin: 2.5rem 0 .8rem;
  padding-bottom: .35rem; border-bottom: 2px solid #1a1a1a;
}
h3 { font-size: 1rem; margin: 1.6rem 0 .5rem; color: #333; }
.sub { color: #555; margin: 0 0 .15rem; }
.encabezado { border-bottom: 3px solid #1a1a1a; padding-bottom: 1.2rem; margin-bottom: 1.5rem; }
table { border-collapse: collapse; margin: .6rem 0 1rem; font-size: .88rem; }
th, td { border: 1px solid #c4c4c4; padding: .3rem .6rem; text-align: left; }
th { background: #f0f0f0; font-weight: 600; }
td.centro, th.centro { text-align: center; }
.mono, pre, code { font-family: "Cascadia Code", Consolas, "SF Mono", Menlo, monospace; }
pre {
  background: #f7f7f7; border: 1px solid #e0e0e0; border-radius: 4px;
  padding: .8rem 1rem; overflow-x: auto; font-size: .85rem; line-height: 1.45;
}
.campo { margin: .25rem 0; }
.campo .etiqueta { display: inline-block; min-width: 13rem; color: #555; }
.vacio { color: #888; }
.inicial { font-weight: 700; }
.final { background: #eef6ee; }
.leyenda { font-size: .8rem; color: #666; margin-top: -.6rem; }
.error {
  background: #fdf0f0; border-left: 4px solid #c0392b;
  padding: .8rem 1rem; border-radius: 0 4px 4px 0;
}
.veredicto {
  padding: .7rem 1rem; border-radius: 4px; margin: .8rem 0;
  border-left: 4px solid #2d7a3e; background: #eef6ee;
}
.veredicto.rechaza { border-left-color: #b06a1e; background: #fdf6ec; }
.veredicto.discrepa { border-left-color: #c0392b; background: #fdf0f0; }
.aviso { color: #8a5a00; font-size: .88rem; }
.expresion-titulo { font-family: "Cascadia Code", Consolas, monospace; }
@media print {
  body { padding: 0; max-width: none; font-size: 10.5pt; }
  h2 { page-break-before: always; }
  h2:first-of-type { page-break-before: avoid; }
  h3, table, pre, .veredicto { page-break-inside: avoid; }
  pre { background: #fafafa; }
}
"""


def _estados(cantidad: int) -> str:
    """'1 estado' / '4 estados', para que los títulos no queden mal escritos."""
    return f"{cantidad} estado" if cantidad == 1 else f"{cantidad} estados"


def _marca(afd_o_afn, estado: int) -> str:
    """Prefijo que señala si un estado es inicial y/o de aceptación."""
    marca = ""
    if estado == afd_o_afn.inicial:
        marca += "&rarr;"
    if estado in afd_o_afn.aceptacion:
        marca += "*"
    return marca


def _clases(automata, estado: int) -> str:
    clases = []
    if estado == automata.inicial:
        clases.append("inicial")
    if estado in automata.aceptacion:
        clases.append("final")
    return f' class="{" ".join(clases)}"' if clases else ""


def _tabla_afn(afn: AFN) -> str:
    columnas = sorted(afn.alfabeto) + [EPSILON]

    filas = []
    for estado in sorted(afn.estados):
        celdas = [
            f'<td class="mono centro">{_marca(afn, estado)}q{estado}</td>'
        ]
        for simbolo in columnas:
            destinos = sorted(afn.transiciones.get(estado, {}).get(simbolo, set()))
            texto = (
                "{" + ", ".join(f"q{d}" for d in destinos) + "}"
                if destinos
                else '<span class="vacio">&mdash;</span>'
            )
            celdas.append(f'<td class="mono centro">{texto}</td>')
        filas.append(f"<tr{_clases(afn, estado)}>" + "".join(celdas) + "</tr>")

    encabezados = "".join(
        f'<th class="centro mono">{escape(c)}</th>' for c in columnas
    )
    return (
        "<table><thead><tr><th>Estado</th>"
        + encabezados
        + "</tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
        + '<p class="leyenda">&rarr; estado inicial &nbsp;&nbsp; * estado de aceptación</p>'
    )


def _tabla_afd(afd: AFD) -> str:
    columnas = sorted(afd.alfabeto)

    filas = []
    for estado in sorted(afd.estados):
        celdas = [
            f'<td class="mono centro">{_marca(afd, estado)}q{estado}</td>'
        ]
        for simbolo in columnas:
            destino = afd.delta(estado, simbolo)
            texto = (
                f"q{destino}"
                if destino is not None
                else '<span class="vacio">&mdash;</span>'
            )
            celdas.append(f'<td class="mono centro">{texto}</td>')
        filas.append(f"<tr{_clases(afd, estado)}>" + "".join(celdas) + "</tr>")

    encabezados = "".join(
        f'<th class="centro mono">{escape(c)}</th>' for c in columnas
    )
    return (
        "<table><thead><tr><th>Estado</th>"
        + encabezados
        + "</tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
        + '<p class="leyenda">&rarr; estado inicial &nbsp;&nbsp; * estado de aceptación</p>'
    )


def _tabla_origenes(afd: AFD) -> str:
    filas = []
    for estado in sorted(afd.estados):
        conjunto = afd.origen.get(estado)
        detalle = (
            "{" + ", ".join(f"q{n}" for n in sorted(conjunto)) + "}"
            if conjunto
            else '<span class="vacio">&mdash;</span>'
        )
        filas.append(
            f'<tr><td class="mono centro">A{estado}</td>'
            f'<td class="mono">{detalle}</td></tr>'
        )
    return (
        "<table><thead><tr><th>Estado del AFD</th>"
        "<th>Estados del AFN que lo conforman</th></tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
    )


def _tabla_bloques(bloques: Dict[int, FrozenSet[int]]) -> str:
    filas = []
    for identificador in sorted(bloques):
        miembros = ", ".join(f"A{n}" for n in sorted(bloques[identificador]))
        filas.append(
            f'<tr><td class="mono centro">M{identificador}</td>'
            f'<td class="mono">{{{miembros}}}</td></tr>'
        )
    return (
        "<table><thead><tr><th>Estado del AFD mínimo</th>"
        "<th>Estados del AFD que se fundieron</th></tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
    )


def _bloque_simulacion(analisis: Analisis) -> str:
    resultado = analisis.resultado
    if resultado is None:
        return ""

    mostrada = (
        f"<code>{escape(resultado.cadena)}</code>"
        if resultado.cadena
        else "<em>(cadena vacía)</em>"
    )

    partes = ["<h3>Simulación</h3>"]

    if analisis.desconocidos:
        ajenos = ", ".join(f"<code>{escape(s)}</code>" for s in analisis.desconocidos)
        partes.append(
            f'<p class="aviso">Aviso: la cadena usa símbolos que no están '
            f"en el alfabeto de esta expresión: {ajenos}</p>"
        )

    def si_no(valor: bool) -> str:
        return "sí" if valor else "no"

    partes.append(
        "<table><thead><tr><th>Autómata</th>"
        '<th class="centro">¿Acepta <span class="mono">w</span>?</th></tr></thead><tbody>'
        f'<tr><td>AFN (Thompson)</td><td class="centro">{si_no(resultado.afn)}</td></tr>'
        f'<tr><td>AFD (subconjuntos)</td><td class="centro">{si_no(resultado.afd)}</td></tr>'
        f'<tr><td>AFD mínimo (Hopcroft)</td><td class="centro">{si_no(resultado.minimo)}</td></tr>'
        "</tbody></table>"
    )

    if not resultado.coinciden:
        partes.append(
            '<p class="veredicto discrepa"><strong>¡Discrepancia!</strong> '
            "Los tres autómatas deberían reconocer el mismo lenguaje, así que "
            "esto indica un error en alguna etapa de la construcción.</p>"
        )
    elif resultado.acepta:
        partes.append(
            f'<p class="veredicto">La cadena {mostrada} <strong>pertenece</strong> '
            "al lenguaje. Los tres autómatas coinciden.</p>"
        )
    else:
        partes.append(
            f'<p class="veredicto rechaza">La cadena {mostrada} '
            "<strong>no pertenece</strong> al lenguaje. Los tres autómatas coinciden.</p>"
        )

    return "".join(partes)


def _seccion(analisis: Analisis, numero: int) -> str:
    titulo = (
        f'<h2>Expresión #{numero}: '
        f'<span class="expresion-titulo">{escape(analisis.expresion)}</span></h2>'
    )

    if not analisis.valido:
        return (
            titulo
            + f'<div class="error"><strong>Error de sintaxis</strong>'
            f"<pre>{escape(analisis.error or '')}</pre></div>"
        )

    alfabeto = (
        ", ".join(f"<code>{escape(s)}</code>" for s in analisis.alfabeto)
        or '<span class="vacio">(vacío)</span>'
    )

    posiciones = (
        "".join(
            f'<tr><td class="centro mono">{n}</td>'
            f'<td class="centro mono">{escape(s)}</td></tr>'
            for n, s in analisis.posiciones
        )
        or '<tr><td colspan="2" class="vacio">'
        "(ninguna: la expresión solo genera la cadena vacía)</td></tr>"
    )

    return "".join(
        [
            titulo,
            '<div class="campo"><span class="etiqueta">Con concatenación explícita</span>'
            f'<code>{escape(analisis.con_concatenacion)}</code></div>',
            '<div class="campo"><span class="etiqueta">Notación postfix</span>'
            f'<code>{escape(analisis.postfix)}</code></div>',
            f'<div class="campo"><span class="etiqueta">Alfabeto</span>{alfabeto}</div>',
            "<h3>Árbol sintáctico</h3>",
            f"<pre>{escape(analisis.arbol)}</pre>",
            "<h3>Posiciones de los símbolos</h3>",
            '<table><thead><tr><th class="centro">Posición</th>'
            '<th class="centro">Símbolo</th></tr></thead><tbody>'
            + posiciones
            + "</tbody></table>",
            f"<h3>AFN de Thompson — {_estados(len(analisis.afn.estados))}</h3>",
            _tabla_afn(analisis.afn),
            f"<h3>AFD por subconjuntos — {_estados(len(analisis.afd.estados))}</h3>",
            _tabla_afd(analisis.afd),
            "<h4>Estados y el subconjunto del AFN que los origina</h4>",
            _tabla_origenes(analisis.afd),
            f"<h3>AFD mínimo (Hopcroft) — {_estados(len(analisis.minimo.estados))}</h3>",
            f"<p>Reducción: {len(analisis.afd.estados)} &rarr; "
            f"{_estados(len(analisis.minimo.estados))}.</p>",
            _tabla_afd(analisis.minimo),
            "<h4>Estados del AFD que se fundieron en cada uno</h4>",
            _tabla_bloques(analisis.bloques),
            _bloque_simulacion(analisis),
        ]
    )


def _resumen(analisis: List[Analisis]) -> str:
    filas = []
    for numero, uno in enumerate(analisis, start=1):
        if not uno.valido:
            filas.append(
                f'<tr><td class="centro">{numero}</td>'
                f'<td class="mono">{escape(uno.expresion)}</td>'
                f'<td colspan="4" class="vacio">error de sintaxis</td></tr>'
            )
            continue

        veredicto = ""
        if uno.resultado is not None:
            veredicto = (
                f'<td class="centro">{"sí" if uno.resultado.acepta else "no"}</td>'
            )

        filas.append(
            f'<tr><td class="centro">{numero}</td>'
            f'<td class="mono">{escape(uno.expresion)}</td>'
            f'<td class="mono">{escape(uno.postfix)}</td>'
            f'<td class="centro">{len(uno.afn.estados)}</td>'
            f'<td class="centro">{len(uno.afd.estados)}</td>'
            f'<td class="centro">{len(uno.minimo.estados)}</td>'
            + veredicto
            + "</tr>"
        )

    columna_extra = (
        '<th class="centro">¿Acepta w?</th>'
        if any(uno.resultado is not None for uno in analisis)
        else ""
    )

    return (
        "<h2>Resumen</h2><table><thead><tr>"
        '<th class="centro">#</th><th>Expresión</th><th>Postfix</th>'
        '<th class="centro">AFN</th><th class="centro">AFD</th>'
        '<th class="centro">AFD mín.</th>'
        + columna_extra
        + "</tr></thead><tbody>"
        + "".join(filas)
        + "</tbody></table>"
    )


def a_html(
    analisis: List[Analisis],
    cadena: Optional[str] = None,
    archivo: Optional[str] = None,
) -> str:
    """
    Arma el documento HTML completo a partir de una lista de análisis.
    Devuelve el HTML como cadena de texto.
    """
    subtitulos = [
        "Universidad del Valle de Guatemala",
        "Teoría de la Computación (CC2019), Sección 30",
    ]
    if archivo:
        subtitulos.append(f"Archivo: <code>{escape(archivo)}</code>")
    if cadena is not None:
        mostrada = (
            f"<code>{escape(cadena)}</code>" if cadena else "<em>(cadena vacía)</em>"
        )
        subtitulos.append(f"Cadena simulada: {mostrada}")

    encabezado = (
        '<div class="encabezado"><h1>Analizador léxico &mdash; Proyecto #1</h1>'
        + "".join(f'<p class="sub">{s}</p>' for s in subtitulos)
        + "</div>"
    )

    secciones = "".join(
        _seccion(uno, numero) for numero, uno in enumerate(analisis, start=1)
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Analizador léxico — Proyecto #1</title>"
        f"<style>{ESTILO}</style></head><body>"
        + encabezado
        + _resumen(analisis)
        + secciones
        + "</body></html>\n"
    )
