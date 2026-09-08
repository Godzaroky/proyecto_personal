"""
Pruebas del driver de línea de comandos.

Se ejecutan con:
    python3 -m unittest discover -s tests -v
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MAIN = RAIZ / "main.py"


def correr(argumentos, cwd):
    """Ejecuta main.py como proceso aparte y devuelve (código, salida)."""
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
    proceso = subprocess.run(
        [sys.executable, str(MAIN), *argumentos],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=entorno,
    )
    return proceso.returncode, proceso.stdout + proceso.stderr


class PruebasArchivoDeExpresiones(unittest.TestCase):
    def test_encuentra_el_archivo_por_omision_desde_el_proyecto(self):
        codigo, salida = correr([], cwd=RAIZ)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Procesadas 4 de 4", salida)

    def test_encuentra_el_archivo_por_omision_desde_otra_carpeta(self):
        """
        Regresión: main.py resolvía 'expresiones.txt' contra el directorio
        actual, así que ejecutarlo desde otra carpeta —o desde un IDE con
        otro directorio de trabajo— fallaba con "no se encontró el
        archivo". Ahora también se busca junto a main.py.
        """
        with tempfile.TemporaryDirectory() as otra_carpeta:
            codigo, salida = correr([], cwd=otra_carpeta)
            self.assertEqual(codigo, 0, salida)
            self.assertIn("Procesadas 4 de 4", salida)

    def test_archivo_propio_relativo_al_directorio_actual(self):
        """Un archivo del usuario se busca primero donde él está parado."""
        with tempfile.TemporaryDirectory() as carpeta:
            propio = Path(carpeta) / "mias.txt"
            propio.write_text("a*\n(a|b)c\n", encoding="utf-8")

            codigo, salida = correr(["mias.txt"], cwd=carpeta)
            self.assertEqual(codigo, 0, salida)
            self.assertIn("Procesadas 2 de 2", salida)

    def test_archivo_inexistente_reporta_error_sin_reventar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            codigo, salida = correr(["no_existe.txt"], cwd=carpeta)
            self.assertEqual(codigo, 1)
            self.assertIn("No se encontró el archivo", salida)
            self.assertIn("Se buscó en", salida)
            self.assertNotIn("Traceback", salida)


class PruebasSimulacionDesdeLaLinea(unittest.TestCase):
    def test_simula_la_cadena_indicada(self):
        codigo, salida = correr(["expresiones.txt", "abba"], cwd=RAIZ)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Simulación:", salida)
        self.assertIn("PERTENECE", salida)

    def test_simula_la_cadena_vacia(self):
        """La cadena vacía es un argumento válido, no 'no se pidió simular'."""
        codigo, salida = correr(["expresiones.txt", ""], cwd=RAIZ)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("(vacía)", salida)

    def test_sin_cadena_no_simula(self):
        codigo, salida = correr(["expresiones.txt"], cwd=RAIZ)
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("Simulación:", salida)

    def test_no_revienta_con_epsilon_en_la_cadena(self):
        """Regresión: 'ε' dentro de w hacía reventar la simulación."""
        codigo, salida = correr(["expresiones.txt", "aεb"], cwd=RAIZ)
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("Traceback", salida)
        self.assertIn("fuera del alfabeto", salida)


if __name__ == "__main__":
    unittest.main(verbosity=2)
