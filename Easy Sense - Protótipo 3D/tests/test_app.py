"""Testes com banco temporário; não alteram os dados da apresentação."""

import csv
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from database import PassageStore
from server import WEB_FILES, create_handler


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.store = PassageStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_passage_and_persistence(self):
        self.store.handle_action("start")
        for _ in range(3):
            self.store.handle_action("axle")
        state = self.store.handle_action("finish")
        self.assertIsNone(state["active"])
        self.assertEqual(state["history"][0]["axes"], 3)
        reopened = PassageStore(self.path).get_state()
        self.assertEqual(reopened["total_passages"], 1)
        self.assertEqual(reopened["total_axes"], 3)
        with self.assertRaises(ValueError):
            self.store.handle_action("finish")

    def test_invalid_transitions(self):
        for action in ["axle", "undo", "finish", "cancel"]:
            with self.assertRaises(ValueError):
                self.store.handle_action(action)
        self.store.handle_action("start")
        for action in ["start", "finish", "undo"]:
            with self.assertRaises(ValueError):
                self.store.handle_action(action)
        self.assertEqual(self.store.get_state()["active"]["axes"], 0)

    def test_undo_cancel_and_recover_active(self):
        self.store.handle_action("start")
        self.store.handle_action("axle")
        self.store.handle_action("axle")
        self.store.handle_action("undo")
        self.assertEqual(PassageStore(self.path).get_state()["active"]["axes"], 1)
        self.store.handle_action("cancel")
        self.assertEqual(self.store.get_state()["history"], [])
        self.assertEqual(self.store.get_state()["total_axes"], 0)

    def test_csv(self):
        for count in [2, 3]:
            self.store.handle_action("start")
            for _ in range(count):
                self.store.handle_action("axle")
            self.store.handle_action("finish")
        rows = list(
            csv.reader(
                io.StringIO(self.store.export_csv().decode("utf-8-sig")), delimiter=";"
            )
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual([row[3] for row in rows[1:]], ["2", "3"])

    def test_http_interface_and_flow(self):
        server = HTTPServer(("127.0.0.1", 0), create_handler(self.store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/manual") as response:
                self.assertIn("Detectar eixo", response.read().decode())
            with urlopen(base) as response:
                self.assertIn("Simulação 3D", response.read().decode())
            # HTML, CSS e módulos JavaScript agora são arquivos separados.
            for route, (_, content_type) in WEB_FILES.items():
                with urlopen(base + route) as response:
                    self.assertTrue(
                        response.headers["Content-Type"].startswith(content_type)
                    )
                    self.assertGreater(len(response.read()), 0)
            with self.assertRaises(HTTPError) as blocked_file:
                urlopen(base + "/database.py")
            self.assertEqual(blocked_file.exception.code, 404)
            for action in ["start", "axle", "axle", "axle", "finish"]:
                with urlopen(
                    Request(
                        base + "/api/" + action,
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                ) as response:
                    state = json.load(response)
            self.assertEqual(state["history"][0]["axes"], 3)
            with self.assertRaises(HTTPError) as failure:
                urlopen(
                    Request(
                        base + "/api/finish",
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                )
            self.assertEqual(failure.exception.code, 409)
            with urlopen(base + "/historico.csv") as response:
                self.assertIn("3 eixo(s)", response.read().decode("utf-8-sig"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_camera_pair_and_duplicate_events(self):
        state = self.store.start_simulation("truck")
        pid = state["active"]["id"]
        for axle in range(1, 4):
            self.store.record_camera_event(pid, "A", axle)
            self.store.record_camera_event(pid, "A", axle)
            self.assertEqual(self.store.get_state()["active"]["axes"], axle - 1)
            self.store.record_camera_event(pid, "B", axle)
            self.store.record_camera_event(pid, "B", axle)
            self.assertEqual(self.store.get_state()["active"]["axes"], axle)
        state = self.store.handle_action("finish")
        self.assertEqual(state["history"][0]["axes"], 3)
        self.assertEqual(state["history"][0]["mode"], "simulation")
        self.assertEqual(PassageStore(self.path).get_state()["total_axes"], 3)

    def test_incomplete_simulation_and_manual_interference(self):
        pid = self.store.start_simulation("car")["active"]["id"]
        self.store.record_camera_event(pid, "A", 1)
        self.store.record_camera_event(pid, "B", 1)
        for action in ["finish", "axle", "undo"]:
            with self.assertRaises(ValueError):
                self.store.handle_action(action)
        with self.assertRaises(ValueError):
            self.store.start_simulation("bus")
        for args in [(pid, "C", 1), (pid, "A", 3), (pid, "B", True), (pid + 1, "A", 1)]:
            with self.assertRaises(ValueError):
                self.store.record_camera_event(*args)
        self.assertEqual(len(PassageStore(self.path).get_state()["camera_events"]), 2)
        self.store.handle_action("cancel")
        self.assertEqual(self.store.get_state()["total_passages"], 0)

    def test_migrates_previous_database_without_losing_history(self):
        oldpath = Path(self.temp.name) / "old.sqlite3"
        with sqlite3.connect(oldpath) as db:
            db.execute(
                "CREATE TABLE passages (id INTEGER PRIMARY KEY, started TEXT, ended TEXT, axes INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active')"
            )
            db.execute(
                "INSERT INTO passages VALUES (1,'2026-10-23','2026-10-23',3,'finished')"
            )
        migrated = PassageStore(oldpath)
        self.assertEqual(migrated.get_state()["total_axes"], 3)
        self.assertEqual(migrated.get_state()["history"][0]["mode"], "manual")
        migrated.start_simulation("trailer")
        self.assertEqual(migrated.get_state()["active"]["id"], 2)

    def test_visual_recognition_is_separate_from_scenario(self):
        passage_id = self.store.start_simulation("car")["active"]["id"]
        # A resposta não deve ser copiada do cenário (car): salva a observação visual enviada.
        self.store.record_recognition(passage_id, "A", "bus", 2, 7)
        self.assertEqual(
            self.store.get_state()["active"]["recognition_status"], "pending"
        )
        self.store.record_recognition(passage_id, "B", "bus", 2, 7)
        state = self.store.get_state()
        self.assertEqual(state["active"]["identified_type"], "bus")
        self.assertEqual(state["active"]["recognition_status"], "agreed")
        self.assertEqual(len(state["recognition_observations"]), 2)
        reopened = PassageStore(self.path).get_state()
        self.assertEqual(reopened["active"]["identified_type"], "bus")

    def test_visual_disagreement_and_unknown(self):
        passage_id = self.store.start_simulation("truck")["active"]["id"]
        for camera, result in [("A", "truck"), ("B", "car")]:
            self.store.record_recognition(passage_id, camera, result, 3, 1)
        self.assertEqual(
            self.store.get_state()["active"]["recognition_status"], "inconclusive"
        )
        self.assertEqual(self.store.get_state()["active"]["identified_type"], "unknown")
        for camera in ["A", "B"]:
            self.store.record_recognition(passage_id, camera, "unknown", 0, 0)
        self.assertEqual(
            self.store.get_state()["active"]["recognition_status"], "inconclusive"
        )
        self.assertEqual(len(self.store.get_state()["recognition_observations"]), 2)

    def test_rejects_invalid_recognition(self):
        passage_id = self.store.start_simulation("car")["active"]["id"]
        invalid = [
            (passage_id, "C", "car", 2, 2),
            (passage_id + 1, "A", "car", 2, 2),
            (passage_id, "A", "invalid", 2, 2),
            (passage_id, "A", "car", -1, 2),
            (passage_id, "A", "car", True, 2),
        ]
        for observation in invalid:
            with self.assertRaises(ValueError):
                self.store.record_recognition(*observation)
        self.assertEqual(self.store.get_state()["recognition_observations"], [])


if __name__ == "__main__":
    unittest.main()
