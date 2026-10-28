"""Configurações que você pode ajustar sem mexer nas regras do programa.

As posições dos eixos vão de 0 (traseira) a 1 (frente do veículo).
O comprimento é visual, em pixels; não representa uma medida real.
Mantenha os identificadores car/bus/truck/trailer se já houver histórico salvo.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "web"
DATABASE_PATH = PROJECT_ROOT / "pedagio.sqlite3"

HOST = "127.0.0.1"
PORT = 8765
HISTORY_LIMIT = 100
MAX_REQUEST_BYTES = 4096

# Mude para 12000 para uma animação mais lenta (12 segundos).
SIMULATION_SETTINGS = {"duration_ms": 8000}

VEHICLES = {
    "car": {
        "label": "Carro",
        "axes": [0.22, 0.80],
        "length": 160,
        "color": "#ea7931",
    },
    "bus": {
        "label": "Ônibus",
        "axes": [0.18, 0.82],
        "length": 270,
        "color": "#f5f5f4",
    },
    "truck": {
        "label": "Caminhão",
        "axes": [0.16, 0.32, 0.85],
        "length": 280,
        "color": "#ed8b45",
    },
    "trailer": {
        "label": "Carreta",
        "axes": [0.12, 0.22, 0.32, 0.59, 0.69, 0.89],
        "length": 390,
        "color": "#e9e5df",
    },
}
