"""Verificações do servidor local. Não fazem chamadas para serviços externos."""

import csv
import io
import json
import socket
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from config import VEHICLES
from database import PassageStore
from security import SECURITY_HEADERS, safe_csv_value
from server import create_handler


class LocalSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = PassageStore(Path(self.temp.name) / "security.sqlite3")
        handler = create_handler(self.store)
        handler.timeout = 0.15  # Reduz a espera apenas neste ambiente de teste.
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method="GET", path="/", data=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        request_headers = dict(headers or {})
        body = data
        if isinstance(data, dict):
            body = json.dumps(data).encode()
            request_headers.setdefault("Content-Type", "application/json")
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            return response.status, dict(response.headers), response.read()
        finally:
            connection.close()

    def raw_request(self, headers, body=b""):
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as client:
            client.sendall(headers.encode() + body)
            response = client.recv(4096)
            return int(response.split(b" ", 2)[1])

    def test_security_headers_on_pages_and_errors(self):
        for path in ["/", "/manual", "/api/state", "/not-found"]:
            status, headers, _ = self.request(path=path)
            self.assertIn(status, [200, 404])
            for name, value in SECURITY_HEADERS.items():
                self.assertEqual(headers[name], value)
            self.assertEqual(headers["Server"], "PedagioFacil")

    def test_rejects_non_local_host_even_if_origin_matches(self):
        headers = {"Host": "example.invalid", "Origin": "http://example.invalid"}
        status, _, _ = self.request("POST", "/api/start", {}, headers)
        self.assertEqual(status, 403)
        self.assertIsNone(self.store.get_state()["active"])
        self.assertEqual(self.request(headers={"Host": "example.invalid"})[0], 403)

    def test_accepts_localhost_and_rejects_foreign_origins(self):
        self.assertEqual(
            self.request(headers={"Host": f"localhost:{self.port}"})[0], 200
        )
        for origin in ["https://example.invalid", "null", "http://localhost:12345"]:
            status, _, _ = self.request("POST", "/api/start", {}, {"Origin": origin})
            self.assertEqual(status, 403)
        self.assertIsNone(self.store.get_state()["active"])

    def test_cross_site_metadata_blocks_api_but_allows_page_navigation(self):
        metadata = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"}
        self.assertEqual(self.request(headers=metadata)[0], 200)
        self.assertEqual(self.request(path="/api/state", headers=metadata)[0], 403)
        self.assertEqual(self.request("POST", "/api/start", {}, metadata)[0], 403)

    def test_does_not_serve_database_source_or_arbitrary_paths(self):
        paths = [
            "/pedagio.sqlite3",
            "/database.py",
            "/config.py",
            "/.env",
            "/../database.py",
            "/%2e%2e/database.py",
            "/vendor/../database.py",
        ]
        for path in paths:
            self.assertEqual(self.request(path=path)[0], 404, path)

    def test_rejects_forms_and_invalid_json_without_changing_data(self):
        for body, content_type, expected in [
            (b"{}", "text/plain", 415),
            (b"action=start", "application/x-www-form-urlencoded", 415),
            (b"{invalid", "application/json", 400),
            (b"[]", "application/json", 400),
            (b"[" * 1100 + b"]" * 1100, "application/json", 400),
        ]:
            self.assertEqual(
                self.request(
                    "POST", "/api/start", body, {"Content-Type": content_type}
                )[0],
                expected,
            )
        self.assertIsNone(self.store.get_state()["active"])

    def test_rejects_oversized_duplicate_or_chunked_requests(self):
        base = f"POST /api/start HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
        self.assertEqual(self.raw_request(base + "Content-Length: 5000\r\n\r\n"), 413)
        self.assertEqual(
            self.raw_request(
                base + "Content-Length: 2\r\nContent-Length: 2\r\n\r\n", b"{}"
            ),
            400,
        )
        self.assertEqual(
            self.raw_request(
                base + "Host: example.invalid\r\nContent-Length: 2\r\n\r\n", b"{}"
            ),
            400,
        )
        self.assertEqual(
            self.raw_request(
                base + "Transfer-Encoding: chunked\r\nContent-Length: 2\r\n\r\n", b"{}"
            ),
            400,
        )
        self.assertIsNone(self.store.get_state()["active"])

    def test_incomplete_body_times_out(self):
        request = f"POST /api/start HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\nContent-Length: 20\r\n\r\n"
        self.assertEqual(self.raw_request(request, b"{"), 408)
        self.assertIsNone(self.store.get_state()["active"])

    def test_invalid_inputs_do_not_modify_schema(self):
        for vehicle in ["'; DROP TABLE passages; --", [], {}]:
            status, _, _ = self.request("POST", "/api/simulation", {"vehicle": vehicle})
            self.assertIn(status, [400, 409])
        self.assertEqual(self.request("POST", "/api/start", {})[0], 200)
        self.assertIsNotNone(self.store.get_state()["active"])

    def test_csv_formula_protection(self):
        for value in ["=1+1", "+1", "-1", "@SUM(A1)", "  =1+1", "\ttext"]:
            self.assertEqual(safe_csv_value(value), "'" + value)
        self.assertEqual(safe_csv_value(3), 3)
        self.assertEqual(safe_csv_value("Caminhão"), "Caminhão")
        self.store.start_simulation("car")
        for axle in [1, 2]:
            for camera in ["A", "B"]:
                self.store.record_camera_event(1, camera, axle)
        self.store.handle_action("finish")
        modified = {**VEHICLES["car"], "label": "=1+1"}
        with patch.dict(VEHICLES, {"car": modified}):
            rows = list(
                csv.reader(
                    io.StringIO(self.store.export_csv().decode("utf-8-sig")),
                    delimiter=";",
                )
            )
        self.assertEqual(rows[1][6], "'=1+1")


if __name__ == "__main__":
    unittest.main()
