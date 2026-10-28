"""Servidor local: entrega as telas e encaminha as ações para PassageStore."""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from config import WEB_ROOT
from security import (
    REQUEST_TIMEOUT_SECONDS,
    SECURITY_HEADERS,
    RequestValidationError,
    read_json_request,
    validate_local_request,
)

# Lista explícita dos arquivos publicados. Outros arquivos da pasta não são servidos.
WEB_FILES = {
    "/": ("simulacao.html", "text/html"),
    "/simulacao": ("simulacao.html", "text/html"),
    "/manual": ("manual.html", "text/html"),
    "/css/manual.css": ("css/manual.css", "text/css"),
    "/css/tema.css": ("css/tema.css", "text/css"),
    "/css/simulacao.css": ("css/simulacao.css", "text/css"),
    "/js/api.js": ("js/api.js", "text/javascript"),
    "/js/manual.js": ("js/manual.js", "text/javascript"),
    "/js/simulacao.js": ("js/simulacao.js", "text/javascript"),
    "/js/desenho.js": ("js/desenho.js", "text/javascript"),
    "/js/cena3d.js": ("js/cena3d.js", "text/javascript"),
    "/js/ceu.js": ("js/ceu.js", "text/javascript"),
    "/js/reconhecimento.js": ("js/reconhecimento.js", "text/javascript"),
    "/vendor/three.module.js": ("vendor/three.module.js", "text/javascript"),
    "/vendor/three.core.js": ("vendor/three.core.js", "text/javascript"),
}
MANUAL_ACTIONS = ("start", "axle", "undo", "finish", "cancel")


def create_handler(store):
    """Associa o servidor a um banco; os testes usam um banco temporário."""

    class RequestHandler(BaseHTTPRequestHandler):
        timeout = REQUEST_TIMEOUT_SECONDS

        def version_string(self):
            return "PedagioFacil"

        def end_headers(self):
            # Aplica as proteções também às respostas de erro do servidor.
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            super().end_headers()

        def allow_local_request(self):
            try:
                validate_local_request(self)
                return True
            except RequestValidationError as error:
                self.send_response_body(error.status, {"error": str(error)})
                return False

        def send_response_body(
            self, status, body, content_type="application/json", extra_headers=None
        ):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")

            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            """Lê uma página, os dados atuais ou o arquivo CSV."""
            if not self.allow_local_request():
                return
            route = urlparse(self.path).path

            if route in WEB_FILES:
                filename, content_type = WEB_FILES[route]
                self.send_response_body(
                    200, (WEB_ROOT / filename).read_bytes(), content_type
                )
            elif route == "/api/state":
                self.send_response_body(200, store.get_state())
            elif route == "/historico.csv":
                self.send_response_body(
                    200,
                    store.export_csv(),
                    "text/csv",
                    {
                        "Content-Disposition": 'attachment; filename="historico_pedagio.csv"'
                    },
                )
            elif route == "/favicon.ico":
                self.send_response_body(204, b"")
            else:
                self.send_response_body(404, {"error": "Página não encontrada."})

        def do_POST(self):
            """Valida a requisição e chama a operação correspondente no banco."""
            if not self.allow_local_request():
                return

            route = urlparse(self.path).path
            action = route.removeprefix("/api/")
            allowed_actions = (*MANUAL_ACTIONS, "simulation", "camera", "recognition")
            if not route.startswith("/api/") or action not in allowed_actions:
                self.send_response_body(404, {"error": "Ação não encontrada."})
                return

            try:
                data = read_json_request(self)
                if action == "simulation":
                    result = store.start_simulation(data.get("vehicle"))
                elif action == "camera":
                    result = store.record_camera_event(
                        data.get("passage_id"), data.get("camera"), data.get("axle")
                    )
                elif action == "recognition":
                    result = store.record_recognition(
                        data.get("passage_id"),
                        data.get("camera"),
                        data.get("detected_type"),
                        data.get("wheel_count"),
                        data.get("window_count"),
                    )
                else:
                    result = store.handle_action(action)
                self.send_response_body(200, result)
            except RequestValidationError as error:
                self.send_response_body(error.status, {"error": str(error)})
            except ValueError as error:
                self.send_response_body(409, {"error": str(error)})
            except TypeError:
                self.send_response_body(400, {"error": "Dados inválidos."})
            except sqlite3.Error:
                self.send_response_body(
                    500,
                    {"error": "Não foi possível salvar. Verifique a pasta do projeto."},
                )

        def log_message(self, *_args):
            # Evita encher o terminal de mensagens durante a demonstração.
            pass

    return RequestHandler
