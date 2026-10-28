"""Proteções do servidor local, separadas das regras do pedágio.

O programa atende apenas no computador que o executa. Estas verificações
reduzem a possibilidade de outra página da internet interagir com ele.
Não substituem isolamento do sistema nem autenticação para uso em rede.
"""

import json
from urllib.parse import urlparse

from config import MAX_REQUEST_BYTES

REQUEST_TIMEOUT_SECONDS = 5

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data: blob:; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'none'; worker-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
}


class RequestValidationError(ValueError):
    """Uma requisição inválida, com status HTTP e mensagem controlados."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def validate_local_request(handler):
    """Confere o destino real, sem confiar no domínio enviado pelo cliente."""
    hosts = handler.headers.get_all("Host", [])
    if len(hosts) != 1:
        raise RequestValidationError(400, "Informe um único endereço local.")

    host = hosts[0].lower()
    port = handler.server.server_port
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if host not in allowed_hosts:
        raise RequestValidationError(
            403, "Este programa aceita apenas endereços locais."
        )

    try:
        route = urlparse(handler.path)
    except ValueError:
        raise RequestValidationError(400, "Endereço de requisição inválido.") from None
    if route.scheme or route.netloc:
        raise RequestValidationError(400, "Endereço de requisição inválido.")

    origins = handler.headers.get_all("Origin", [])
    if len(origins) > 1 or (origins and origins[0] != f"http://{host}"):
        raise RequestValidationError(403, "Origem não permitida.")

    # Permite abrir a página por um link, mas não chamadas de outra página
    # para as APIs, arquivos ou ações do protótipo.
    cross_site = handler.headers.get("Sec-Fetch-Site") == "cross-site"
    page_navigation = (
        handler.command == "GET"
        and handler.headers.get("Sec-Fetch-Mode") == "navigate"
        and route.path in ("/", "/manual", "/simulacao")
    )
    if cross_site and not page_navigation:
        raise RequestValidationError(
            403, "Chamadas de outros sites não são permitidas."
        )


def read_json_request(handler):
    """Aceita apenas JSON pequeno, com comprimento explícito e leitura limitada."""
    if handler.headers.get_content_type() != "application/json":
        raise RequestValidationError(415, "Envie os dados como application/json.")
    if handler.headers.get("Transfer-Encoding") is not None:
        raise RequestValidationError(400, "Formato de transferência não permitido.")

    lengths = handler.headers.get_all("Content-Length", [])
    if len(lengths) != 1:
        raise RequestValidationError(400, "Informe um único comprimento de dados.")
    try:
        size = int(lengths[0])
    except ValueError:
        raise RequestValidationError(400, "Comprimento de dados inválido.") from None
    if not 0 <= size <= MAX_REQUEST_BYTES:
        raise RequestValidationError(413, "Dados acima do limite permitido.")

    try:
        payload = handler.rfile.read(size)
    except TimeoutError:
        raise RequestValidationError(
            408, "Tempo limite para receber os dados."
        ) from None
    if len(payload) != size:
        raise RequestValidationError(400, "Dados incompletos.")
    try:
        data = json.loads(payload or b"{}")
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise RequestValidationError(400, "JSON inválido.") from None
    if not isinstance(data, dict):
        raise RequestValidationError(400, "Envie um objeto JSON.")
    return data


def safe_csv_value(value):
    """Evita interpretar textos como fórmulas ao abrir o CSV numa planilha."""
    if isinstance(value, str):
        stripped = value.lstrip()
        starts_formula = stripped.startswith(("=", "+", "-", "@"))
        starts_control = value.startswith(("\t", "\r", "\n"))
        if starts_formula or starts_control:
            return "'" + value
    return value
