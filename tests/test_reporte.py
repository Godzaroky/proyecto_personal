"""
Pruebas del reporte HTML.

Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import unittest

from apoyo import EXPRESIONES_DEL_CURSO

from analizador.reporte import a_html, analizar


class PruebasAnalisis(unittest.TestCase):
    def test_recoge_todo_el_pipeline(self):
        analisis = analizar("(a|b)*abb(a|b)*")
        self.assertTrue(analisis.valido)
        self.assertEqual(analisis.postfix, "ab|*a.b.b.ab|*.")
        self.assertEqual(len(analisis.afn.estados), 22)
        self.assertEqual(len(analisis.afd.estados), 9)
        self.assertEqual(len(analisis.minimo.estados), 4)
        self.assertEqual(len(analisis.bloques), 4)
        self.assertIsNone(analisis.resultado)

    def test_simula_cuando_se_da_una_cadena(self):
        analisis = analizar("(a|b)*abb(a|b)*", "aabbab")
        self.assertIsNotNone(analisis.resultado)
        self.assertTrue(analisis.resultado.acepta)
        self.assertTrue(analisis.resultado.coinciden)

    def test_la_cadena_vacia_se_simula(self):
        """'' es una cadena a simular, no la ausencia de cadena."""
        analisis = analizar("(a|b)*abb(a|b)*", "")
        self.assertIsNotNone(analisis.resultado)
        self.assertFalse(analisis.resultado.acepta)

    def test_una_expresion_mala_no_propaga_la_excepcion(self):
        """Un error de sintaxis no debe detener el proceso de las demás."""
        analisis = analizar("(a|")
        self.assertFalse(analisis.valido)
        self.assertIsNotNone(analisis.error)
        self.assertIsNone(analisis.afn)

    def test_reporta_simbolos_desconocidos(self):
        analisis = analizar("(a|b)*", "azb")
        self.assertEqual(analisis.desconocidos, ["z"])


class PruebasHtml(unittest.TestCase):
    def html_del_curso(self, cadena=None):
        return a_html([analizar(e, cadena) for e in EXPRESIONES_DEL_CURSO], cadena)

    def test_documento_bien_formado(self):
        html = self.html_del_curso()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn('<html lang="es">', html)
        self.assertIn("</body></html>", html)
        self.assertEqual(html.count("<body>"), 1)

    def test_es_autocontenido(self):
        """
        Sin recursos externos: el archivo debe funcionar solo, sin
        conexión y sin carpeta de recursos al lado.
        """
        html = self.html_del_curso()
        self.assertIn("<style>", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_incluye_las_cuatro_expresiones(self):
        html = self.html_del_curso()
        for numero in range(1, 5):
            self.assertIn(f"Expresión #{numero}", html)

    def test_incluye_los_tres_automatas(self):
        html = self.html_del_curso()
        self.assertIn("AFN de Thompson", html)
        self.assertIn("AFD por subconjuntos", html)
        self.assertIn("AFD mínimo (Hopcroft)", html)

    def test_incluye_la_simulacion_cuando_hay_cadena(self):
        self.assertIn("Simulación", self.html_del_curso("abba"))

    def test_sin_cadena_no_hay_simulacion(self):
        self.assertNotIn("<h3>Simulación</h3>", self.html_del_curso())

    def test_reglas_de_impresion_para_el_pdf(self):
        """El PDF sale del navegador, así que el CSS de impresión importa."""
        html = self.html_del_curso()
        self.assertIn("@media print", html)
        self.assertIn("page-break-before", html)

    def test_escapa_los_simbolos_que_son_html(self):
        """
        Un símbolo del alfabeto puede ser '<' o '&'. Sin escapar, el
        navegador lo interpretaría como marcado y el reporte saldría roto
        sin que nada falle de forma visible.
        """
        html = a_html([analizar(r"\<a\>")])
        self.assertIn("&lt;", html)
        self.assertIn("&gt;", html)
        # El símbolo crudo no debe aparecer como marcado dentro del cuerpo.
        self.assertNotIn("<a>", html)

    def test_escapa_el_ampersand_escapado(self):
        html = a_html([analizar(r"a\&b")])
        self.assertIn("&amp;", html)

    def test_una_expresion_mala_sale_como_error_en_el_reporte(self):
        html = a_html([analizar("(a|")])
        self.assertIn("Error de sintaxis", html)
        self.assertIn("error de sintaxis", html)  # también en el resumen

    def test_singular_de_un_solo_estado(self):
        """'1 estado', no '1 estados'."""
        html = a_html([analizar("(a*|b*)+")])
        self.assertIn("1 estado<", html)
        self.assertNotIn("1 estados", html)

    def test_el_resumen_lista_todas_las_expresiones(self):
        html = self.html_del_curso("abba")
        self.assertIn("Resumen", html)
        self.assertIn("AFD mín.", html)
        self.assertIn("¿Acepta w?", html)

        # Cada expresión aparece dos veces: en el resumen y en su sección.
        # Ninguno de sus caracteres necesita escape, así que van literales.
        for expresion in EXPRESIONES_DEL_CURSO:
            with self.subTest(expresion=expresion):
                self.assertGreaterEqual(html.count(expresion), 2, expresion)

    def test_sin_cadena_el_resumen_no_trae_la_columna_del_veredicto(self):
        self.assertNotIn("¿Acepta w?", self.html_del_curso())


if __name__ == "__main__":
    unittest.main(verbosity=2)
