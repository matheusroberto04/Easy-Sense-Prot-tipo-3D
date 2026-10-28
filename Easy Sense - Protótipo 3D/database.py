"""Gravação no SQLite e regras de contagem das passagens.

Este arquivo não desenha a tela nem recebe requisições HTTP.
Ele valida cada operação e devolve os dados para a interface.
"""

import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import HISTORY_LIMIT, SIMULATION_SETTINGS, VEHICLES
from security import safe_csv_value


def current_time():
    """Usa a data e o fuso horário do computador da apresentação."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


class PassageStore:
    """Mantém o histórico e permite somente uma passagem ativa por vez."""

    def __init__(self, database_path):
        self.database_path = database_path
        self._create_tables()

    @contextmanager
    def _connect(self):
        """Confirma as alterações se der certo; desfaz em caso de erro."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _create_tables(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS passages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started TEXT NOT NULL,
                    ended TEXT,
                    axes INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    mode TEXT NOT NULL DEFAULT 'manual',
                    vehicle TEXT
                )
            """)
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS one_active
                ON passages(status) WHERE status = 'active'
            """)

            # Atualiza bancos da primeira versão sem apagar o histórico.
            columns = {
                column["name"]
                for column in connection.execute("PRAGMA table_info(passages)")
            }
            if "mode" not in columns:
                connection.execute(
                    "ALTER TABLE passages ADD COLUMN mode TEXT NOT NULL DEFAULT 'manual'"
                )
            if "vehicle" not in columns:
                connection.execute("ALTER TABLE passages ADD COLUMN vehicle TEXT")
            if "identified_type" not in columns:
                connection.execute(
                    "ALTER TABLE passages ADD COLUMN identified_type TEXT"
                )
            if "recognition_status" not in columns:
                connection.execute(
                    "ALTER TABLE passages ADD COLUMN recognition_status TEXT NOT NULL DEFAULT 'pending'"
                )

            # A chave composta impede repetir um evento da mesma câmera/eixo.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS camera_events (
                    passage_id INTEGER NOT NULL,
                    camera TEXT NOT NULL,
                    axle INTEGER NOT NULL,
                    detected TEXT NOT NULL,
                    PRIMARY KEY(passage_id, camera, axle)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS recognition_observations (
                    passage_id INTEGER NOT NULL,
                    camera TEXT NOT NULL,
                    detected_type TEXT NOT NULL,
                    wheel_count INTEGER NOT NULL,
                    window_count INTEGER NOT NULL,
                    detected TEXT NOT NULL,
                    PRIMARY KEY(passage_id, camera)
                )
            """)

    def get_state(self):
        """Reúne passagem ativa, histórico, totais e configurações da tela."""
        with self._connect() as connection:
            active_passage = connection.execute(
                "SELECT * FROM passages WHERE status = 'active'"
            ).fetchone()
            history = connection.execute(
                "SELECT * FROM passages WHERE status = 'finished' ORDER BY id DESC LIMIT ?",
                (HISTORY_LIMIT,),
            ).fetchall()
            totals = connection.execute("""
                SELECT COUNT(*), COALESCE(SUM(axes), 0)
                FROM passages WHERE status = 'finished'
            """).fetchone()

            active_id = active_passage["id"] if active_passage else -1
            camera_events = connection.execute(
                """SELECT camera, axle, detected FROM camera_events
                   WHERE passage_id = ? ORDER BY detected, axle""",
                (active_id,),
            ).fetchall()
            recognition = connection.execute(
                "SELECT * FROM recognition_observations WHERE passage_id=? ORDER BY camera",
                (active_id,),
            ).fetchall()

        return {
            "active": dict(active_passage) if active_passage else None,
            "history": [dict(passage) for passage in history],
            "camera_events": [dict(event) for event in camera_events],
            "recognition_observations": [
                dict(observation) for observation in recognition
            ],
            "total_passages": totals[0],
            "total_axes": totals[1],
            "vehicles": VEHICLES,
            "simulation_settings": SIMULATION_SETTINGS,
        }

    def handle_action(self, action):
        """Executa uma ação manual, finalização ou cancelamento."""
        with self._connect() as connection:
            # A leitura e a alteração fazem parte da mesma transação.
            connection.execute("BEGIN IMMEDIATE")
            active_passage = connection.execute(
                "SELECT * FROM passages WHERE status = 'active'"
            ).fetchone()

            if action == "start":
                if active_passage:
                    raise ValueError("Já existe uma passagem em andamento.")
                connection.execute(
                    "INSERT INTO passages(started) VALUES (?)", (current_time(),)
                )
            elif action in ("axle", "undo", "finish", "cancel"):
                if not active_passage:
                    raise ValueError("Inicie uma passagem primeiro.")
                self._update_active_passage(connection, active_passage, action)
            else:
                raise ValueError("Ação desconhecida.")

        return self.get_state()

    def _update_active_passage(self, connection, passage, action):
        """Aplica as regras de uma passagem que já está em andamento."""
        passage_id = passage["id"]
        if passage["mode"] == "simulation" and action in ("axle", "undo"):
            raise ValueError(
                "Esta passagem usa câmeras virtuais. Continue na tela de simulação."
            )

        if action == "axle":
            connection.execute(
                "UPDATE passages SET axes = axes + 1 WHERE id = ?", (passage_id,)
            )
        elif action == "undo":
            if passage["axes"] == 0:
                raise ValueError("Não há eixo para desfazer.")
            connection.execute(
                "UPDATE passages SET axes = axes - 1 WHERE id = ?", (passage_id,)
            )
        elif action == "finish":
            self._validate_completion(connection, passage)
            connection.execute(
                "UPDATE passages SET status = 'finished', ended = ? WHERE id = ?",
                (current_time(), passage_id),
            )
        elif action == "cancel":
            connection.execute(
                "UPDATE passages SET status = 'cancelled', ended = ? WHERE id = ?",
                (current_time(), passage_id),
            )

    def _validate_completion(self, connection, passage):
        if passage["axes"] == 0:
            raise ValueError("Registre pelo menos um eixo antes de finalizar.")

        if passage["mode"] == "simulation":
            # Duas observações por eixo: uma da câmera A, outra da B.
            expected_events = len(VEHICLES[passage["vehicle"]]["axes"]) * 2
            received_events = connection.execute(
                "SELECT COUNT(*) FROM camera_events WHERE passage_id = ?",
                (passage["id"],),
            ).fetchone()[0]
            if received_events != expected_events:
                raise ValueError(
                    "Aguarde a confirmação de todos os eixos pelas duas câmeras."
                )

    def start_simulation(self, vehicle_key):
        """Abre uma passagem para o modelo de veículo escolhido na tela."""
        if vehicle_key not in VEHICLES:
            raise ValueError("Selecione um veículo disponível.")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active_passage = connection.execute(
                "SELECT 1 FROM passages WHERE status = 'active'"
            ).fetchone()
            if active_passage:
                raise ValueError(
                    "Conclua ou cancele a passagem em andamento antes de iniciar outra."
                )
            connection.execute(
                "INSERT INTO passages(started, mode, vehicle) VALUES (?, 'simulation', ?)",
                (current_time(), vehicle_key),
            )

        return self.get_state()

    def record_camera_event(self, passage_id, camera, axle):
        """Confirma um eixo apenas quando A e B observarem o mesmo número."""
        if (
            camera not in ("A", "B")
            or type(axle) is not int
            or type(passage_id) is not int
        ):
            raise ValueError("Evento de câmera inválido.")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            passage = connection.execute(
                "SELECT * FROM passages WHERE id = ? AND status = 'active'",
                (passage_id,),
            ).fetchone()
            if not passage or passage["mode"] != "simulation":
                raise ValueError("Esta passagem simulada não está ativa.")
            if not 1 <= axle <= len(VEHICLES[passage["vehicle"]]["axes"]):
                raise ValueError("Eixo inválido para este veículo.")

            connection.execute(
                "INSERT OR IGNORE INTO camera_events VALUES (?, ?, ?, ?)",
                (passage_id, camera, axle, current_time()),
            )
            confirmed_axes = connection.execute(
                """SELECT COUNT(*) FROM (
                       SELECT axle FROM camera_events
                       WHERE passage_id = ?
                       GROUP BY axle HAVING COUNT(*) = 2
                   )""",
                (passage_id,),
            ).fetchone()[0]
            connection.execute(
                "UPDATE passages SET axes = ? WHERE id = ?",
                (confirmed_axes, passage_id),
            )

        return self.get_state()

    def record_recognition(
        self, passage_id, camera, detected_type, wheel_count, window_count
    ):
        """Salva o resultado da análise dos pixels, separado do cenário escolhido.

        Não usa vehicle para determinar o tipo. O navegador envia o que o
        classificador visual observou; A e B precisam concordar.
        """
        valid_types = ("car", "bus", "truck", "trailer", "unknown")
        if (
            type(passage_id) is not int
            or camera not in ("A", "B")
            or detected_type not in valid_types
            or type(wheel_count) is not int
            or not 0 <= wheel_count <= 20
            or type(window_count) is not int
            or not 0 <= window_count <= 30
        ):
            raise ValueError("Resultado de reconhecimento inválido.")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            passage = connection.execute(
                "SELECT * FROM passages WHERE id=? AND status='active'", (passage_id,)
            ).fetchone()
            if not passage or passage["mode"] != "simulation":
                raise ValueError("Esta passagem simulada não está ativa.")
            connection.execute(
                "INSERT OR REPLACE INTO recognition_observations VALUES (?,?,?,?,?,?)",
                (
                    passage_id,
                    camera,
                    detected_type,
                    wheel_count,
                    window_count,
                    current_time(),
                ),
            )
            observations = connection.execute(
                "SELECT detected_type FROM recognition_observations WHERE passage_id=?",
                (passage_id,),
            ).fetchall()
            identified_type = None
            status = "pending"
            if len(observations) == 2:
                types = {observation["detected_type"] for observation in observations}
                if len(types) == 1 and "unknown" not in types:
                    identified_type = observations[0]["detected_type"]
                    status = "agreed"
                else:
                    identified_type = "unknown"
                    status = "inconclusive"
            connection.execute(
                "UPDATE passages SET identified_type=?,recognition_status=? WHERE id=?",
                (identified_type, status, passage_id),
            )
        return self.get_state()

    def export_csv(self):
        """Exporta todas as passagens finalizadas, incluindo fora do limite da tela."""
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";")
        writer.writerow(
            [
                "Passagem",
                "Inicio",
                "Fim",
                "Eixos",
                "Grupo demonstrativo",
                "Origem",
                "Cenario escolhido",
                "Tipo identificado por regras visuais",
                "Status reconhecimento",
            ]
        )
        with self._connect() as connection:
            passages = connection.execute(
                "SELECT * FROM passages WHERE status = 'finished' ORDER BY id"
            )
            for passage in passages:
                vehicle_label = VEHICLES.get(passage["vehicle"], {}).get("label", "")
                writer.writerow(
                    [
                        passage["id"],
                        passage["started"],
                        passage["ended"],
                        passage["axes"],
                        f"{passage['axes']} eixo(s)",
                        passage["mode"],
                        safe_csv_value(vehicle_label),
                        passage["identified_type"] or "",
                        passage["recognition_status"],
                    ]
                )

        # O marcador UTF-8 ajuda programas de planilha a ler os acentos.
        return ("\ufeff" + output.getvalue()).encode("utf-8")
