"""
Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import unittest

from apoyo import (
    EXPRESIONES_DEL_CURSO,
    afd_de,
    afn_de,
    cadenas_hasta,
    minimo_de,
)

from analizador.simulacion import (
    Resultado,
    acepta_afd,
    acepta_afn,
    formatear,
    recorrido_afd,
    recorrido_afn,
    simbolos_desconocidos,
    simular,
)


class PruebasSimulacion(unittest.TestCase):
    def test_expresiones_del_curso(self):
        """Los casos del enunciado, ahora sobre los tres autómatas a la vez."""
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
                resultado = simular(
                    afn_de(expresion), afd_de(expresion), minimo_de(expresion), cadena
                )
                self.assertTrue(resultado.coinciden)
                self.assertEqual(resultado.acepta, esperado)

    def test_los_tres_coinciden_exhaustivamente(self):
        """
        La verificación que el enunciado pide hacer visible: sobre todas
        las cadenas de longitud 0 a 5, los tres autómatas deben dar la
        misma respuesta para cada expresión del curso.
        """
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                afn = afn_de(expresion)
                afd = afd_de(expresion)
                minimo = minimo_de(expresion)
                for cadena in cadenas_hasta(sorted(afn.alfabeto), 5):
                    resultado = simular(afn, afd, minimo, cadena)
                    self.assertTrue(
                        resultado.coinciden,
                        f"{expresion!r} discrepa en {cadena!r}: {resultado}",
                    )


class PruebasRecorridos(unittest.TestCase):
    def test_el_recorrido_del_afn_tiene_un_paso_por_simbolo(self):
        afn = afn_de("(a|b)*abb(a|b)*")
        pasos = recorrido_afn(afn, "aabb")
        self.assertEqual(len(pasos), 5)  # len("aabb") + 1

    def test_el_recorrido_del_afn_arranca_en_la_cerradura_del_inicial(self):
        afn = afn_de("(a|b)*abb(a|b)*")
        self.assertEqual(
            recorrido_afn(afn, "ab")[0], afn.cerradura_epsilon({afn.inicial})
        )

    def test_el_recorrido_del_afd_marca_donde_murio(self):
        """
        En el AFD de 'ab' no hay transición para 'b' desde el inicial, así
        que el recorrido termina en None y no sigue consumiendo.
        """
        afd = afd_de("ab")
        pasos = recorrido_afd(afd, "bbbb")
        self.assertEqual(pasos[0], afd.inicial)
        self.assertIsNone(pasos[-1])
        self.assertEqual(len(pasos), 2)  # se detuvo al primer símbolo

    def test_el_recorrido_del_afd_completo_no_tiene_none(self):
        afd = afd_de("(a|b)*abb(a|b)*")
        pasos = recorrido_afd(afd, "aabb")
        self.assertEqual(len(pasos), 5)
        self.assertNotIn(None, pasos)

    def test_recorrido_de_la_cadena_vacia(self):
        afn = afn_de("a*")
        afd = afd_de("a*")
        self.assertEqual(len(recorrido_afn(afn, "")), 1)
        self.assertEqual(recorrido_afd(afd, ""), [afd.inicial])


class PruebasAceptacion(unittest.TestCase):
    def test_afd_parcial_rechaza_sin_transicion(self):
        """
        El punto que CLAUDE.md marca como delicado: los AFD son parciales
        por diseño, así que delta() == None debe significar rechazo.
        """
        afd = afd_de("ab")
        self.assertIsNone(afd.delta(afd.inicial, "b"))
        self.assertFalse(acepta_afd(afd, "b"))
        self.assertTrue(acepta_afd(afd, "ab"))

    def test_simbolo_fuera_del_alfabeto_se_rechaza(self):
        afn = afn_de("(a|b)*abb(a|b)*")
        afd = afd_de("(a|b)*abb(a|b)*")
        self.assertFalse(acepta_afn(afn, "aabbz"))
        self.assertFalse(acepta_afd(afd, "aabbz"))

    def test_simbolos_desconocidos_los_reporta(self):
        afd = afd_de("(a|b)*abb(a|b)*")
        self.assertEqual(simbolos_desconocidos(afd, "aabb"), set())
        self.assertEqual(simbolos_desconocidos(afd, "az1b"), {"z", "1"})

    def test_epsilon_en_la_cadena_se_rechaza_sin_reventar(self):
        """
        Regresión: si el usuario teclea 'ε' dentro de w —creyendo que
        significa la cadena vacía— la simulación debe rechazar, no
        reventar. Epsilon no está en el alfabeto y `AFN.mover` lanza
        excepción si se le pasa, así que `recorrido_afn` tiene que
        atajar el símbolo antes de llegar ahí.
        """
        afn = afn_de("((ε|a)|b*)*")
        self.assertEqual(simbolos_desconocidos(afn, "ε"), {"ε"})
        self.assertFalse(acepta_afn(afn, "ε"))
        self.assertFalse(acepta_afn(afn, "aεb"))
        # La cadena vacía sí pertenece: es el caso que el usuario quería.
        self.assertTrue(acepta_afn(afn, ""))


class PruebasResultado(unittest.TestCase):
    def test_coinciden_detecta_la_discrepancia(self):
        self.assertTrue(Resultado("a", True, True, True).coinciden)
        self.assertTrue(Resultado("a", False, False, False).coinciden)
        self.assertFalse(Resultado("a", True, False, True).coinciden)

    def test_formatear_menciona_los_tres_automatas(self):
        resultado = Resultado("abb", True, True, True)
        texto = formatear(resultado)
        self.assertIn("AFN", texto)
        self.assertIn("AFD", texto)
        self.assertIn("mínimo", texto)
        self.assertIn("PERTENECE", texto)

    def test_formatear_avisa_de_la_discrepancia(self):
        texto = formatear(Resultado("abb", True, False, True))
        self.assertIn("DISCREPANCIA", texto)

    def test_formatear_muestra_la_cadena_vacia(self):
        self.assertIn("vacía", formatear(Resultado("", True, True, True)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
