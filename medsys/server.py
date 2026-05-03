import json
import sqlite3
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import database as db
from .validators import (
    cpf_valido,
    data_valida,
    formatar_cpf,
    formatar_telefone,
    telefone_valido,
)

ESTATICOS = Path(__file__).resolve().parent / "static"

TIPOS_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
}


def _validar_payload(dados: dict, ignorar_id: int | None = None) -> str | None:
    nome = (dados.get("nome") or "").strip()
    nasc = (dados.get("data_nascimento") or "").strip()
    tel = (dados.get("telefone") or "").strip()
    cpf = (dados.get("cpf") or "").strip()
    oper = (dados.get("operadora") or "").strip()
    cart = (dados.get("carteirinha") or "").strip()
    val = (dados.get("validade_carteirinha") or "").strip()

    if len(nome) < 3:
        return "Informe o nome completo do paciente."
    if not data_valida(nasc):
        return "Data de nascimento inválida. Use dd/mm/aaaa."
    if not telefone_valido(tel):
        return "Telefone inválido. Inclua DDD."
    if not cpf_valido(cpf):
        return "CPF matematicamente inválido. Verifique os dígitos."
    if oper and not cart:
        return "Informe o número da carteirinha do convênio."
    if val and not data_valida(val):
        return "Validade da carteirinha inválida. Use dd/mm/aaaa."
    if db.cpf_existente(formatar_cpf(cpf), ignorar_id=ignorar_id):
        return "Já existe um paciente cadastrado com esse CPF."
    return None


def _normalizar(dados: dict) -> dict:
    return {
        "nome": dados["nome"].strip(),
        "data_nascimento": dados["data_nascimento"].strip(),
        "telefone": formatar_telefone(dados["telefone"].strip()),
        "cpf": formatar_cpf(dados["cpf"].strip()),
        "operadora": (dados.get("operadora") or "").strip(),
        "carteirinha": (dados.get("carteirinha") or "").strip(),
        "validade_carteirinha": (dados.get("validade_carteirinha") or "").strip(),
    }


def _enriquecer(p: dict) -> dict:
    dias = db.dias_para_vencer(p.get("validade_carteirinha"))
    if dias is None:
        situacao = "sem_plano" if not p.get("operadora") else "ok"
    elif dias < 0:
        situacao = "vencido"
    elif dias <= 30:
        situacao = "a_vencer"
    else:
        situacao = "ok"
    return {**p, "dias_para_vencer": dias, "situacao": situacao}


class Handler(BaseHTTPRequestHandler):
    server_version = "MedSysLocal/1.0"

    def log_message(self, *_args):
        return

    def _enviar_json(self, status: int, payload):
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_estatico(self, caminho_relativo: str):
        if caminho_relativo in ("", "/"):
            caminho_relativo = "index.html"
        arquivo = (ESTATICOS / caminho_relativo).resolve()
        if not str(arquivo).startswith(str(ESTATICOS)) or not arquivo.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime = TIPOS_MIME.get(arquivo.suffix, "application/octet-stream")
        dados = arquivo.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _ler_json(self) -> dict | None:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0:
            return {}
        bruto = self.rfile.read(tamanho).decode("utf-8")
        try:
            return json.loads(bruto)
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        rota = urlparse(self.path)
        if rota.path == "/api/pacientes":
            params = parse_qs(rota.query)
            filtro = (params.get("q", [""])[0]).strip()
            pacientes = [_enriquecer(p) for p in db.listar_pacientes(filtro)]
            return self._enviar_json(HTTPStatus.OK, pacientes)
        if rota.path.startswith("/api/pacientes/"):
            try:
                id_ = int(rota.path.rsplit("/", 1)[1])
            except ValueError:
                return self._enviar_json(HTTPStatus.BAD_REQUEST, {"erro": "id inválido"})
            p = db.obter_paciente(id_)
            if not p:
                return self._enviar_json(HTTPStatus.NOT_FOUND, {"erro": "não encontrado"})
            return self._enviar_json(HTTPStatus.OK, _enriquecer(p))
        return self._enviar_estatico(rota.path.lstrip("/"))

    def do_POST(self):
        if self.path != "/api/pacientes":
            return self.send_error(HTTPStatus.NOT_FOUND)
        dados = self._ler_json()
        if dados is None:
            return self._enviar_json(HTTPStatus.BAD_REQUEST, {"erro": "JSON inválido"})
        erro = _validar_payload(dados)
        if erro:
            return self._enviar_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"erro": erro})
        try:
            id_ = db.inserir_paciente(_normalizar(dados))
        except sqlite3.IntegrityError:
            return self._enviar_json(
                HTTPStatus.CONFLICT, {"erro": "CPF já cadastrado."}
            )
        return self._enviar_json(HTTPStatus.CREATED, _enriquecer(db.obter_paciente(id_)))

    def do_PUT(self):
        if not self.path.startswith("/api/pacientes/"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            id_ = int(self.path.rsplit("/", 1)[1])
        except ValueError:
            return self._enviar_json(HTTPStatus.BAD_REQUEST, {"erro": "id inválido"})
        dados = self._ler_json()
        if dados is None:
            return self._enviar_json(HTTPStatus.BAD_REQUEST, {"erro": "JSON inválido"})
        if not db.obter_paciente(id_):
            return self._enviar_json(HTTPStatus.NOT_FOUND, {"erro": "não encontrado"})
        erro = _validar_payload(dados, ignorar_id=id_)
        if erro:
            return self._enviar_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"erro": erro})
        db.atualizar_paciente(id_, _normalizar(dados))
        return self._enviar_json(HTTPStatus.OK, _enriquecer(db.obter_paciente(id_)))

    def do_DELETE(self):
        if not self.path.startswith("/api/pacientes/"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            id_ = int(self.path.rsplit("/", 1)[1])
        except ValueError:
            return self._enviar_json(HTTPStatus.BAD_REQUEST, {"erro": "id inválido"})
        if not db.obter_paciente(id_):
            return self._enviar_json(HTTPStatus.NOT_FOUND, {"erro": "não encontrado"})
        db.remover_paciente(id_)
        return self._enviar_json(HTTPStatus.NO_CONTENT, {})


def executar(host: str = "127.0.0.1", porta: int = 8765, abrir_navegador: bool = True):
    db.inicializar()
    servidor = ThreadingHTTPServer((host, porta), Handler)
    url = f"http://{host}:{porta}/"
    print(f"MedSys Local rodando em {url}")
    print("Encerre com Ctrl+C.")
    if abrir_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando…")
    finally:
        servidor.server_close()
