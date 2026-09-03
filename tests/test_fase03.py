"""
Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import unittest

from apoyo import (
    EXPRESIONES_DEL_CURSO,
    acepta_afd,
    acepta_afn,
    afd_de,
    afn_de,
    cadenas_hasta,
)

from analizador.subconjuntos import listado_de_estados
from analizador.tokens import EPSILON


class PruebasSubconjuntos(unittest.TestCase):
    def test_expresiones_del_curso_aceptan_lo_esperado(self):
        """Los mismos casos verificados sobre el AFN, ahora sobre el AFD."""
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
                self.assertEqual(acepta_afd(afd_de(expresion), cadena), esperado)

    def test_afn_y_afd_reconocen_el_mismo_lenguaje(self):
        """
        Prueba de regresión principal: para cada expresión del curso se
        recorren todas las cadenas de longitud 0 a 5 sobre su alfabeto y
        se exige que el AFN y el AFD coincidan en cada una.
        """
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afn = afn_de(expresion)
                afd = afd_de(expresion)
                for cadena in cadenas_hasta(sorted(afn.alfabeto), 5):
                    self.assertEqual(
                        acepta_afn(afn, cadena),
                        acepta_afd(afd, cadena),
                        f"discrepancia en {expresion!r} con la cadena {cadena!r}",
                    )

    def test_el_afd_es_determinista(self):
        """Cada par (estado, símbolo) lleva a lo sumo a un estado."""
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afd = afd_de(expresion)
                for estado, transiciones in afd.transiciones.items():
                    for simbolo, destino in transiciones.items():
                        self.assertIsInstance(destino, int)
                        self.assertIn(destino, afd.estados)

    def test_epsilon_no_es_columna_del_afd(self):
        afd = afd_de("((ε|a)|b*)*")
        self.assertNotIn(EPSILON, afd.alfabeto)
        self.assertEqual(afd.alfabeto, {"a", "b"})

    def test_origen_registra_el_subconjunto_del_afn(self):
        """
        El estado inicial del AFD debe ser exactamente la cerradura
        epsilon del estado inicial del AFN.
        """
        afn = afn_de("(a|b)*abb(a|b)*")
        afd = afd_de("(a|b)*abb(a|b)*")

        self.assertEqual(
            afd.origen[afd.inicial], afn.cerradura_epsilon({afn.inicial})
        )
        # Todo estado del AFD debe tener su subconjunto registrado.
        for estado in afd.estados:
            self.assertIn(estado, afd.origen)

    def test_aceptacion_si_el_subconjunto_toca_un_final_del_afn(self):
        afn = afn_de("(a|b)*abb(a|b)*")
        afd = afd_de("(a|b)*abb(a|b)*")
        for estado, conjunto in afd.origen.items():
            self.assertEqual(
                estado in afd.aceptacion,
                bool(conjunto & afn.aceptacion),
            )

    def test_caso_minimo(self):
        """La expresión 'a' produce dos estados: el inicial y el final."""
        afd = afd_de("a")
        self.assertEqual(len(afd.estados), 2)
        self.assertEqual(afd.alfabeto, {"a"})
        self.assertTrue(acepta_afd(afd, "a"))
        self.assertFalse(acepta_afd(afd, ""))
        self.assertFalse(acepta_afd(afd, "aa"))

    def test_afd_parcial_rechaza_por_transicion_faltante(self):
        """
        'ab' no tiene transición para 'b' desde el inicial, así que el
        AFD queda parcial y la simulación rechaza ahí mismo.
        """
        afd = afd_de("ab")
        self.assertIsNone(afd.delta(afd.inicial, "b"))
        self.assertFalse(acepta_afd(afd, "b"))
        self.assertTrue(acepta_afd(afd, "ab"))

    def test_completar_no_cambia_el_lenguaje(self):
        """Agregar el sumidero (lo que necesita Hopcroft) no altera nada."""
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afd = afd_de(expresion)
                completo = afd.completar()
                self.assertTrue(completo.es_completo())
                for cadena in cadenas_hasta(sorted(afd.alfabeto), 4):
                    self.assertEqual(
                        acepta_afd(afd, cadena),
                        acepta_afd(completo, cadena),
                        f"el sumidero cambió {expresion!r} en {cadena!r}",
                    )

    def test_numeracion_estable_entre_corridas(self):
        """
        El recorrido en anchura con símbolos ordenados debe dar siempre
        la misma numeración; las tablas del reporte dependen de eso.
        """
        primero = afd_de("(a|b)*abb(a|b)*")
        segundo = afd_de("(a|b)*abb(a|b)*")
        self.assertEqual(primero.a_diccionario(), segundo.a_diccionario())

    def test_listado_de_estados_menciona_todos_los_estados(self):
        afd = afd_de("(a|b)*abb(a|b)*")
        texto = listado_de_estados(afd)
        self.assertEqual(len(texto.splitlines()), len(afd.estados))
        self.assertIn("->", texto)
        self.assertIn("*", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
