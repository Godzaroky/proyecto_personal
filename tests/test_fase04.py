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
    minimo_de,
)

from analizador.automatas.afd import AFD
from analizador.hopcroft import construir as minimizar, construir_con_bloques


class PruebasHopcroft(unittest.TestCase):
    def test_el_minimo_reconoce_el_mismo_lenguaje_que_el_afd(self):
        """
        Prueba de regresión principal de la fase: para cada expresión del
        curso se recorren todas las cadenas de longitud 0 a 5 y se exige
        que el AFD y su versión mínima coincidan en cada una.
        """
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afd = afd_de(expresion)
                minimo = minimo_de(expresion)
                for cadena in cadenas_hasta(sorted(afd.alfabeto), 5):
                    self.assertEqual(
                        acepta_afd(afd, cadena),
                        acepta_afd(minimo, cadena),
                        f"discrepancia en {expresion!r} con la cadena {cadena!r}",
                    )

    def test_los_tres_automatas_coinciden(self):
        """AFN, AFD y AFD mínimo deben aceptar exactamente lo mismo."""
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afn = afn_de(expresion)
                afd = afd_de(expresion)
                minimo = minimo_de(expresion)
                for cadena in cadenas_hasta(sorted(afn.alfabeto), 4):
                    esperado = acepta_afn(afn, cadena)
                    self.assertEqual(acepta_afd(afd, cadena), esperado, cadena)
                    self.assertEqual(acepta_afd(minimo, cadena), esperado, cadena)

    def test_tamanos_esperados(self):
        """
        Los dos objetivos anotados al cerrar la fase 3: el lenguaje Σ*
        colapsa a un solo estado y el AFD clásico de 'abb' baja de 9 a 4.
        """
        esperado = {
            "(a*|b*)+": 1,
            "((ε|a)|b*)*": 1,
            "(a|b)*abb(a|b)*": 4,
        }
        for expresion, estados in esperado.items():
            with self.subTest(expresion=expresion):
                self.assertEqual(len(minimo_de(expresion).estados), estados)

    def test_sigma_estrella_es_un_bucle_de_un_estado(self):
        minimo = minimo_de("(a*|b*)+")
        self.assertEqual(len(minimo.estados), 1)
        self.assertEqual(minimo.aceptacion, {minimo.inicial})
        for simbolo in minimo.alfabeto:
            self.assertEqual(minimo.delta(minimo.inicial, simbolo), minimo.inicial)

    def test_el_minimo_no_tiene_estados_equivalentes(self):
        """
        Minimizar dos veces no debe cambiar nada: si quedara algún par de
        estados equivalentes, la segunda pasada los fundiría.
        """
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                minimo = minimo_de(expresion)
                otra_vez = minimizar(minimo)
                self.assertEqual(minimo.a_diccionario(), otra_vez.a_diccionario())

    def test_no_quedan_estados_inalcanzables(self):
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                minimo = minimo_de(expresion)
                self.assertEqual(minimo.estados_alcanzables(), minimo.estados)

    def test_poda_estados_inalcanzables_del_afd_de_entrada(self):
        """Un estado inalcanzable no debe aparecer en el mínimo."""
        afd = AFD(inicial=0, aceptacion=[1])
        afd.agregar_transicion(0, "a", 1)
        afd.agregar_transicion(1, "a", 1)
        afd.agregar_estado(99, de_aceptacion=True)  # isla inalcanzable
        afd.agregar_transicion(99, "a", 99)

        minimo = minimizar(afd)
        self.assertEqual(minimo.estados_alcanzables(), minimo.estados)
        self.assertTrue(acepta_afd(minimo, "a"))
        self.assertFalse(acepta_afd(minimo, ""))

    def test_el_minimo_queda_parcial_sin_sumidero(self):
        """
        'ab' produce un AFD parcial; el mínimo debe seguir parcial en vez
        de arrastrar el sumidero que agrega completar().
        """
        minimo = minimizar(afd_de("ab"))
        self.assertNotIn(-1, minimo.estados)
        self.assertIsNone(minimo.delta(minimo.inicial, "b"))
        self.assertTrue(acepta_afd(minimo, "ab"))
        self.assertFalse(acepta_afd(minimo, "b"))
        self.assertFalse(acepta_afd(minimo, "abb"))

    def test_estados_equivalentes_se_funden(self):
        """
        AFD con dos estados de aceptación indistinguibles: ambos aceptan y
        ambos van a sí mismos con 'a'. Deben fundirse en uno.
        """
        afd = AFD(inicial=0)
        afd.agregar_estado(0)
        afd.agregar_estado(1, de_aceptacion=True)
        afd.agregar_estado(2, de_aceptacion=True)
        afd.agregar_transicion(0, "a", 1)
        afd.agregar_transicion(1, "a", 2)
        afd.agregar_transicion(2, "a", 1)

        minimo = minimizar(afd)
        self.assertEqual(len(minimo.estados), 2)

    def test_bloques_cubren_todos_los_estados_del_afd(self):
        """
        El mapeo de bloques debe repartir los estados del AFD original sin
        traslapes. Los estados ausentes solo pueden ser los estériles.
        """
        afd = afd_de("(a|b)*abb(a|b)*")
        minimo, bloques = construir_con_bloques(afd)

        self.assertEqual(len(bloques), len(minimo.estados))

        vistos = set()
        for miembros in bloques.values():
            self.assertFalse(vistos & miembros, "un estado quedó en dos bloques")
            vistos |= miembros

        # Este AFD no tiene estados estériles, así que se cubren todos.
        self.assertEqual(vistos, afd.estados)

    def test_bloques_del_afd_clasico(self):
        """
        La partición esperada de '(a|b)*abb(a|b)*': {0,2}, {1}, {3} y los
        cinco estados de aceptación fundidos en uno.
        """
        afd = afd_de("(a|b)*abb(a|b)*")
        _, bloques = construir_con_bloques(afd)

        particion = {frozenset(miembros) for miembros in bloques.values()}
        self.assertEqual(
            particion,
            {
                frozenset({0, 2}),
                frozenset({1}),
                frozenset({3}),
                frozenset({4, 5, 6, 7, 8}),
            },
        )

    def test_numeracion_estable_entre_corridas(self):
        primero = minimo_de("(a|b)*abb(a|b)*")
        segundo = minimo_de("(a|b)*abb(a|b)*")
        self.assertEqual(primero.a_diccionario(), segundo.a_diccionario())

    def test_el_estado_inicial_es_cero(self):
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                self.assertEqual(minimo_de(expresion).inicial, 0)

    def test_origen_conserva_los_estados_del_afn(self):
        """
        El origen de un estado mínimo es la unión de los subconjuntos del
        AFN de los estados que se fundieron en él.
        """
        afd = afd_de("(a|b)*abb(a|b)*")
        minimo, bloques = construir_con_bloques(afd)

        for identificador, miembros in bloques.items():
            union = set()
            for estado in miembros:
                union |= afd.origen[estado]
            self.assertEqual(minimo.origen[identificador], frozenset(union))


if __name__ == "__main__":
    unittest.main(verbosity=2)
