"""Ponto de entrada. Execute: python3 app.py"""

import argparse
import threading
import webbrowser
from http.server import ThreadingHTTPServer

from config import DATABASE_PATH, HOST, PORT
from database import PassageStore
from server import create_handler


def main():
    parser = argparse.ArgumentParser(
        description="Easy Sense: demonstração local de contagem de eixos."
    )
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    arguments = parser.parse_args()

    if HOST not in ("127.0.0.1", "localhost"):
        print("Este protótipo é local. Mantenha HOST como 127.0.0.1 em config.py.")
        return
    if not 1 <= arguments.port <= 65535:
        parser.error("A porta precisa estar entre 1 e 65535.")

    store = PassageStore(DATABASE_PATH)
    try:
        server = ThreadingHTTPServer((HOST, arguments.port), create_handler(store))
    except OSError:
        print(
            f"Porta {arguments.port} ocupada. Tente: python3 app.py --port {arguments.port + 1}"
        )
        return

    address = f"http://{HOST}:{server.server_port}"
    print("\nEasy Sense")
    print(f"Abra no navegador: {address}")
    print(
        "Mantenha este terminal aberto. Para encerrar, pressione Ctrl+C.\n", flush=True
    )

    if not arguments.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(address)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAplicação encerrada. O histórico foi preservado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
