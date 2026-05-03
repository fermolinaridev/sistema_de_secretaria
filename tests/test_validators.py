import unittest

from medsys.validators import (
    cpf_valido,
    data_valida,
    formatar_cpf,
    formatar_telefone,
    telefone_valido,
)


class TestCPF(unittest.TestCase):
    def test_validos(self):
        for cpf in ("529.982.247-25", "11144477735", "390.533.447-05"):
            self.assertTrue(cpf_valido(cpf), cpf)

    def test_invalidos(self):
        for cpf in ("123.456.789-00", "111.111.111-11", "00000000000", "1234", ""):
            self.assertFalse(cpf_valido(cpf), cpf)

    def test_formatar(self):
        self.assertEqual(formatar_cpf("52998224725"), "529.982.247-25")


class TestData(unittest.TestCase):
    def test_validas(self):
        self.assertTrue(data_valida("01/01/1990"))
        self.assertTrue(data_valida("29/02/2024"))

    def test_invalidas(self):
        self.assertFalse(data_valida("31/02/2024"))
        self.assertFalse(data_valida("1990-01-01"))
        self.assertFalse(data_valida(""))


class TestTelefone(unittest.TestCase):
    def test_validos(self):
        self.assertTrue(telefone_valido("(11) 91234-5678"))
        self.assertTrue(telefone_valido("1132145566"))

    def test_invalidos(self):
        self.assertFalse(telefone_valido("12345"))
        self.assertFalse(telefone_valido(""))

    def test_formatar(self):
        self.assertEqual(formatar_telefone("11912345678"), "(11) 91234-5678")
        self.assertEqual(formatar_telefone("1132145566"), "(11) 3214-5566")


if __name__ == "__main__":
    unittest.main()
