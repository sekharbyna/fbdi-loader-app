"""Stdlib web server — no pip packages required.

Usage:
    py -3 server.py
    python server.py
"""

from __future__ import annotations

import json
import os
import sys
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import get_object, list_objects  # noqa: E402
from app.load_service import run_load  # noqa: E402
from app.oracle_client import OracleERPClient, OracleError  # noqa: E402

STATIC = ROOT / "static"
PORT = int(os.environ.get("PORT", "8000"))


def parse_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def parse_multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    length = int(handler.headers.get("Content-Length") or "0")
    body = handler.rfile.read(length) if length else b""
    content_type = handler.headers.get("Content-Type", "")
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n"
    msg = BytesParser(policy=policy.default).parsebytes(header.encode("utf-8") + body)
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="Content-Disposition")
        if not name:
            continue
        filename = part.get_param("filename", header="Content-Disposition")
        payload = part.get_payload(decode=True)
        if payload is None:
            payload = b""
        if filename:
            files[str(name)] = (str(filename), payload)
        else:
            fields[str(name)] = payload.decode("utf-8", errors="replace")
    return fields, files


class Handler(BaseHTTPRequestHandler):
    server_version = "FBDILoadConsole/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, payload, content_type: str = "application/json; charset=utf-8") -> None:
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = str(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code: int, message: str) -> None:
        self._send(code, {"detail": message})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC / rel).resolve()
            if STATIC not in target.parents and target != STATIC:
                self._error(403, "Forbidden")
                return
            ctype = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".ico": "image/x-icon",
            }.get(target.suffix, "application/octet-stream")
            self._file(target, ctype)
            return
        if path == "/api/health":
            self._send(200, {"status": "ok", "mode": "stdlib"})
            return
        if path == "/api/defaults":
            self._send(
                200,
                {
                    "base_url": os.getenv("ORACLE_BASE_URL", ""),
                    "username": os.getenv("ORACLE_USERNAME", ""),
                    "has_password": bool(os.getenv("ORACLE_PASSWORD")),
                    "data_access_set": os.getenv("DEFAULT_DATA_ACCESS_SET", ""),
                    "ledger_id": os.getenv("DEFAULT_LEDGER_ID", ""),
                    "business_unit": os.getenv("DEFAULT_BUSINESS_UNIT", ""),
                    "journal_source": os.getenv("DEFAULT_JOURNAL_SOURCE", "Spreadsheet"),
                    "ap_source": os.getenv("DEFAULT_AP_SOURCE", "Spreadsheet"),
                },
            )
            return
        if path == "/api/objects":
            self._send(200, list_objects())
            return
        self._error(404, "Not found")

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._error(404, f"Missing {path.name}")
            return
        self._send(200, path.read_bytes(), content_type)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/ping":
                body = parse_json(self)
                OracleERPClient(body["base_url"], body["username"], body["password"]).ping()
                self._send(200, {"ok": True})
                return
            if path == "/api/lookup-interface":
                body = parse_json(self)
                spec = get_object(body["object_key"])
                raw = OracleERPClient(body["base_url"], body["username"], body["password"]).inbound_process_details(
                    spec["import_job"]["job_name"]
                )
                self._send(200, {"object": spec["key"], "job_name": spec["import_job"]["job_name"], "oracle": raw})
                return
            if path == "/api/status":
                body = parse_json(self)
                raw = OracleERPClient(body["base_url"], body["username"], body["password"]).get_ess_job_status(
                    body["request_id"]
                )
                self._send(200, raw)
                return
            if path == "/api/job-details":
                body = parse_json(self)
                raw = OracleERPClient(body["base_url"], body["username"], body["password"]).get_ess_job_details(
                    body["request_id"], file_type="log"
                )
                self._send(200, raw)
                return
            if path == "/api/load":
                fields, files = parse_multipart(self)
                uploaded = files.get("file")
                if not uploaded:
                    self._error(400, "Choose the FBDI ZIP first.")
                    return
                filename, content = uploaded
                result = run_load(
                    base_url=fields.get("base_url", ""),
                    username=fields.get("username", ""),
                    password=fields.get("password", ""),
                    object_key=fields.get("object_key", ""),
                    mode=fields.get("mode", "two_step"),
                    interface_id=fields.get("interface_id", ""),
                    run_import=fields.get("run_import", "Y"),
                    wait_for_load=fields.get("wait_for_load", "Y"),
                    wait_seconds=fields.get("wait_seconds", "300"),
                    import_parameters=fields.get("import_parameters", ""),
                    filename=filename,
                    content=content,
                )
                self._send(200, result)
                return
            self._error(404, "Not found")
        except KeyError as exc:
            self._error(404, str(exc))
        except (OracleError, ValueError, json.JSONDecodeError) as exc:
            self._error(400, str(exc))
        except Exception as exc:
            self._error(500, str(exc))


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"FBDI Load Console")
    print(f"Open http://127.0.0.1:{PORT}")
    print("Stop with Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")


if __name__ == "__main__":
    main()
