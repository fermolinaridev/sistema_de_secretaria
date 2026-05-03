import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "medsys.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE,
    data_nascimento TEXT NOT NULL,
    telefone TEXT NOT NULL,
    operadora TEXT,
    carteirinha TEXT,
    validade_carteirinha TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pacientes_nome ON pacientes(nome);
CREATE INDEX IF NOT EXISTS idx_pacientes_cpf  ON pacientes(cpf);
"""


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar():
    with conectar() as c:
        c.executescript(SCHEMA)


def inserir_paciente(dados: dict) -> int:
    agora = datetime.now().isoformat(timespec="seconds")
    with conectar() as c:
        cur = c.execute(
            """INSERT INTO pacientes
               (nome, cpf, data_nascimento, telefone, operadora,
                carteirinha, validade_carteirinha, criado_em, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dados["nome"],
                dados["cpf"],
                dados["data_nascimento"],
                dados["telefone"],
                dados.get("operadora") or None,
                dados.get("carteirinha") or None,
                dados.get("validade_carteirinha") or None,
                agora,
                agora,
            ),
        )
        return cur.lastrowid


def atualizar_paciente(id_: int, dados: dict) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    with conectar() as c:
        c.execute(
            """UPDATE pacientes SET
                 nome=?, cpf=?, data_nascimento=?, telefone=?,
                 operadora=?, carteirinha=?, validade_carteirinha=?,
                 atualizado_em=?
               WHERE id=?""",
            (
                dados["nome"],
                dados["cpf"],
                dados["data_nascimento"],
                dados["telefone"],
                dados.get("operadora") or None,
                dados.get("carteirinha") or None,
                dados.get("validade_carteirinha") or None,
                agora,
                id_,
            ),
        )


def remover_paciente(id_: int) -> None:
    with conectar() as c:
        c.execute("DELETE FROM pacientes WHERE id=?", (id_,))


def obter_paciente(id_: int):
    with conectar() as c:
        row = c.execute("SELECT * FROM pacientes WHERE id=?", (id_,)).fetchone()
        return dict(row) if row else None


def listar_pacientes(filtro: str = ""):
    sql = "SELECT * FROM pacientes"
    args: tuple = ()
    if filtro:
        sql += " WHERE nome LIKE ? OR cpf LIKE ?"
        like = f"%{filtro}%"
        args = (like, like)
    sql += " ORDER BY nome COLLATE NOCASE"
    with conectar() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def cpf_existente(cpf: str, ignorar_id: int | None = None) -> bool:
    sql = "SELECT 1 FROM pacientes WHERE cpf=?"
    args: list = [cpf]
    if ignorar_id is not None:
        sql += " AND id<>?"
        args.append(ignorar_id)
    with conectar() as c:
        return c.execute(sql, args).fetchone() is not None


def dias_para_vencer(validade: str | None) -> int | None:
    if not validade:
        return None
    try:
        d = datetime.strptime(validade, "%d/%m/%Y").date()
    except ValueError:
        return None
    return (d - date.today()).days
