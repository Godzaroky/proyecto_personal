"""
Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analizador.arbol import (  # noqa: E402
    TipoNodo,
    construir,
    numerar_posiciones,
)
from analizador.automatas import AFD, AFN  # noqa: E402
from analizador.errores import ErrorDeAutomata, ErrorDeSintaxis  # noqa: E402
from analizador.shunting_yard import convertir  # noqa: E402
from analizador.tokens import (  # noqa: E402
    EPSILON,
    TipoToken,
    alfabeto_de,
    preparar,
    tokenizar,
    tokens_a_texto,
)

# Las cuatro expresiones que piden el Lab 3, el Lab 4 y el proyecto.
EXPRESIONES_DEL_CURSO = [
    "(a*|b*)+",
    "((ε|a)|b*)*",
    "(a|b)*abb(a|b)*",
    "0?(1?)?0*",
]


def postfix_de(expresion: str) -> str:
    return tokens_a_texto(convertir(expresion))


class PruebasTokenizacion(unittest.TestCase):
    def test_epsilon_acepta_ambos_alias(self):
        """ε y & producen exactamente el mismo token."""
        con_epsilon = tokenizar("ε")
        con_ampersand = tokenizar("&")
        self.assertEqual(con_epsilon[0].tipo, TipoToken.EPSILON)
        self.assertEqual(con_ampersand[0].tipo, TipoToken.EPSILON)
        self.assertEqual(con_epsilon[0].valor, con_ampersand[0].valor)

    def test_epsilon_fuera_del_alfabeto(self):
        """Epsilon no consume entrada, así que no pertenece al alfabeto."""
        self.assertEqual(alfabeto_de(preparar("((ε|a)|b*)*")), {"a", "b"})

    def test_escape_convierte_operador_en_simbolo(self):
        tokens = tokenizar(r"a\*b")
        self.assertEqual([t.tipo for t in tokens], [TipoToken.SIMBOLO] * 3)
        self.assertTrue(tokens[1].escapado)
        self.assertEqual(tokens[1].valor, "*")

    def test_escape_de_epsilon_es_simbolo_literal(self):
        tokens = tokenizar(r"\ε")
        self.assertEqual(tokens[0].tipo, TipoToken.SIMBOLO)
        self.assertEqual(tokens[0].valor, EPSILON)

    def test_espacios_se_ignoran(self):
        self.assertEqual(tokens_a_texto(preparar("a b")), tokens_a_texto(preparar("ab")))

    def test_espacio_escapado_es_simbolo(self):
        self.assertEqual(alfabeto_de(preparar(r"a\ b")), {"a", " ", "b"})

    def test_concatenacion_implicita(self):
        self.assertEqual(tokens_a_texto(preparar("abb")), "a.b.b")
        self.assertEqual(tokens_a_texto(preparar("(a|b)*a")), "(a|b)*.a")

    def test_barra_invertida_suelta(self):
        with self.assertRaises(ErrorDeSintaxis):
            tokenizar("a\\")

    def test_expresion_vacia(self):
        with self.assertRaises(ErrorDeSintaxis):
            tokenizar("")


class PruebasValidacion(unittest.TestCase):
    def test_rechaza_entradas_mal_formadas(self):
        invalidas = ["(a", "a)", "|a", "a|", "*a", "()", "a||b", "(a|)"]
        for expresion in invalidas:
            with self.subTest(expresion=expresion):
                with self.assertRaises(ErrorDeSintaxis):
                    preparar(expresion)

    def test_acepta_las_expresiones_del_curso(self):
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                preparar(expresion)

    def test_el_error_señala_la_posicion(self):
        with self.assertRaises(ErrorDeSintaxis) as contexto:
            preparar("ab|")
        self.assertEqual(contexto.exception.posicion, 2)


class PruebasShuntingYard(unittest.TestCase):
    def test_expresiones_del_curso(self):
        esperado = {
            "(a*|b*)+": "a*b*|+",
            "((ε|a)|b*)*": "εa|b*|*",
            "(a|b)*abb(a|b)*": "ab|*a.b.b.ab|*.",
            "0?(1?)?0*": "0?1??.0*.",
        }
        for expresion, postfix in esperado.items():
            with self.subTest(expresion=expresion):
                self.assertEqual(postfix_de(expresion), postfix)

    def test_precedencia_union_menor_que_concatenacion(self):
        self.assertEqual(postfix_de("a|bc"), "abc.|")

    def test_asociatividad_izquierda_de_la_union(self):
        self.assertEqual(postfix_de("a|b|c"), "ab|c|")

    def test_asociatividad_izquierda_de_la_concatenacion(self):
        self.assertEqual(postfix_de("abc"), "ab.c.")

    def test_unario_se_aplica_al_atomo_anterior(self):
        self.assertEqual(postfix_de("ab*"), "ab*.")
        self.assertEqual(postfix_de("(ab)*"), "ab.*")

    def test_simbolo_escapado_no_se_confunde_con_operador(self):
        """
        El motivo de usar tokens en vez de texto: en 'a\\*' el asterisco es
        un símbolo del alfabeto y el árbol debe tener dos hojas, no una
        cerradura.
        """
        postfix = convertir(r"a\*")
        self.assertEqual([t.tipo for t in postfix],
                         [TipoToken.SIMBOLO, TipoToken.SIMBOLO, TipoToken.CONCAT])
        raiz = construir(postfix)
        self.assertEqual(raiz.tipo, TipoNodo.CONCAT)
        self.assertEqual(raiz.derecho.tipo, TipoNodo.SIMBOLO)


class PruebasArbolSintactico(unittest.TestCase):
    def test_estructura_de_una_union(self):
        raiz = construir(convertir("a|b"))
        self.assertEqual(raiz.tipo, TipoNodo.UNION)
        self.assertEqual(raiz.izquierdo.valor, "a")
        self.assertEqual(raiz.derecho.valor, "b")

    def test_estructura_de_un_unario(self):
        raiz = construir(convertir("a*"))
        self.assertEqual(raiz.tipo, TipoNodo.KLEENE)
        self.assertEqual(raiz.izquierdo.tipo, TipoNodo.SIMBOLO)
        self.assertIsNone(raiz.derecho)

    def test_posiciones_de_izquierda_a_derecha(self):
        raiz = construir(convertir("(a|b)*abb(a|b)*"))
        posiciones = numerar_posiciones(raiz)
        self.assertEqual(
            posiciones,
            [(1, "a"), (2, "b"), (3, "a"), (4, "b"), (5, "b"), (6, "a"), (7, "b")],
        )

    def test_epsilon_no_recibe_posicion(self):
        """
        Epsilon no consume entrada, así que no ocupa posición en la
        construcción directa. En '((ε|a)|b*)*' solo hay dos posiciones.
        """
        raiz = construir(convertir("((ε|a)|b*)*"))
        posiciones = numerar_posiciones(raiz)
        self.assertEqual(posiciones, [(1, "a"), (2, "b")])

    def test_todas_las_expresiones_del_curso_construyen_arbol(self):
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                raiz = construir(convertir(expresion))
                self.assertIsNotNone(raiz)


class PruebasAFN(unittest.TestCase):
    def construir_afn(self) -> AFN:
        """AFN mínimo para la expresión 'a': q0 --a--> q1."""
        afn = AFN(inicial=0, aceptacion=[1])
        afn.agregar_transicion(0, "a", 1)
        return afn

    def test_epsilon_no_entra_al_alfabeto(self):
        afn = AFN(inicial=0, aceptacion=[1])
        afn.agregar_transicion(0, EPSILON, 1)
        self.assertEqual(afn.alfabeto, set())
        self.assertEqual(afn.estados, {0, 1})

    def test_cerradura_epsilon_es_transitiva(self):
        afn = AFN(inicial=0, aceptacion=[2])
        afn.agregar_transicion(0, EPSILON, 1)
        afn.agregar_transicion(1, EPSILON, 2)
        self.assertEqual(afn.cerradura_epsilon({0}), frozenset({0, 1, 2}))

    def test_cerradura_epsilon_tolera_ciclos(self):
        afn = AFN(inicial=0, aceptacion=[1])
        afn.agregar_transicion(0, EPSILON, 1)
        afn.agregar_transicion(1, EPSILON, 0)
        self.assertEqual(afn.cerradura_epsilon({0}), frozenset({0, 1}))

    def test_mover_no_aplica_cerradura(self):
        afn = self.construir_afn()
        afn.agregar_transicion(1, EPSILON, 2)
        self.assertEqual(afn.mover({0}, "a"), frozenset({1}))

    def test_mover_rechaza_epsilon(self):
        with self.assertRaises(ErrorDeAutomata):
            self.construir_afn().mover({0}, EPSILON)

    def test_serializacion(self):
        datos = self.construir_afn().a_diccionario()
        self.assertEqual(datos["tipo"], "AFN")
        self.assertEqual(datos["alfabeto"], ["a"])
        self.assertEqual(datos["transiciones"][0]["destinos"], [1])


class PruebasAFD(unittest.TestCase):
    def construir_afd(self) -> AFD:
        """AFD parcial que acepta la cadena 'ab'."""
        afd = AFD(inicial=0, aceptacion=[2])
        afd.agregar_transicion(0, "a", 1)
        afd.agregar_transicion(1, "b", 2)
        return afd

    def test_delta_indefinida_devuelve_none(self):
        self.assertIsNone(self.construir_afd().delta(0, "b"))

    def test_rechaza_no_determinismo(self):
        afd = self.construir_afd()
        with self.assertRaises(ErrorDeAutomata):
            afd.agregar_transicion(0, "a", 2)

    def test_completar_agrega_sumidero(self):
        afd = self.construir_afd()
        self.assertFalse(afd.es_completo())

        completo = afd.completar()
        self.assertTrue(completo.es_completo())
        self.assertNotIn(-1, completo.aceptacion)
        # El original no debe modificarse.
        self.assertFalse(afd.es_completo())

    def test_completar_no_ensucia_un_afd_ya_completo(self):
        afd = AFD(inicial=0, aceptacion=[0])
        afd.agregar_transicion(0, "a", 0)
        self.assertEqual(afd.completar().estados, {0})

    def test_estados_alcanzables(self):
        afd = self.construir_afd()
        afd.agregar_estado(99)
        self.assertEqual(afd.estados_alcanzables(), {0, 1, 2})


if __name__ == "__main__":
    unittest.main(verbosity=2)
