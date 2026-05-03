import re
from datetime import datetime


def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def formatar_cpf(cpf: str) -> str:
    d = somente_digitos(cpf)
    if len(d) != 11:
        return cpf
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def cpf_valido(cpf: str) -> bool:
    d = somente_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False

    soma = sum(int(d[i]) * (10 - i) for i in range(9))
    dv1 = (soma * 10) % 11
    if dv1 == 10:
        dv1 = 0
    if dv1 != int(d[9]):
        return False

    soma = sum(int(d[i]) * (11 - i) for i in range(10))
    dv2 = (soma * 10) % 11
    if dv2 == 10:
        dv2 = 0
    return dv2 == int(d[10])


def data_valida(texto: str) -> bool:
    try:
        datetime.strptime(texto, "%d/%m/%Y")
        return True
    except (ValueError, TypeError):
        return False


def telefone_valido(texto: str) -> bool:
    d = somente_digitos(texto)
    return 10 <= len(d) <= 11


def formatar_telefone(texto: str) -> str:
    d = somente_digitos(texto)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return texto
