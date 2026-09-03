"""
Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import unittest

from apoyo import acepta_afn as acepta, afn_de

from analizador.tokens import EPSILON


class PruebasThompson(unittest.TestCase):
    def test_un_unico_estado_de_aceptacion(self):
        afn = afn_de("a*b*")
        self.assertEqual(len(afn.aceptacion), 1)

    def test_expresiones_del_curso_aceptan_lo_esperado(self):
        casos = [
            ("(a*|b*)+", "abba", True),
            ("(a*|b*)+", "", True),
            ("((ε|a)|b*)*", "abba", True),
            ("((ε|a)|b*)*", "", True),
            ("(a|b)*abb(a|b)*", "aabbab", True),
            ("(a|b)*abb(a|b)*", "", False),
            ("0?(1?)?0*", "0100", True),
            ("0?(1?)?0*", "", True),
        ]
        for expresion, cadena, esperado in casos:
            with self.subTest(expresion=expresion, cadena=cadena):
                self.assertEqual(acepta(afn_de(expresion), cadena), esperado)

    def test_rechaza_cadena_que_no_pertenece_al_lenguaje(self):
        self.assertFalse(acepta(afn_de("a*b*"), "ba"))

    def test_kleene_acepta_vacia_y_repite(self):
        afn = afn_de("a*")
        self.assertTrue(acepta(afn, ""))
        self.assertTrue(acepta(afn, "aaaa"))
        self.assertFalse(acepta(afn, "aab"))

    def test_plus_exige_al_menos_una_repeticion(self):
        afn = afn_de("a+")
        self.assertFalse(acepta(afn, ""))
        self.assertTrue(acepta(afn, "a"))
        self.assertTrue(acepta(afn, "aaa"))

    def test_opcional_no_repite(self):
        afn = afn_de("a?")
        self.assertTrue(acepta(afn, ""))
        self.assertTrue(acepta(afn, "a"))
        self.assertFalse(acepta(afn, "aa"))

    def test_concatenacion_y_union(self):
        afn = afn_de("(a|b)c")
        self.assertTrue(acepta(afn, "ac"))
        self.assertTrue(acepta(afn, "bc"))
        self.assertFalse(acepta(afn, "c"))
        self.assertFalse(acepta(afn, "ab"))

    def test_epsilon_como_operando(self):
        afn = afn_de("aεb")
        self.assertTrue(acepta(afn, "ab"))

    def test_alfabeto_no_incluye_epsilon(self):
        afn = afn_de("((ε|a)|b*)*")
        self.assertNotIn(EPSILON, afn.alfabeto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
