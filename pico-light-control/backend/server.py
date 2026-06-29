import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "https://alkerim.github.io")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).with_name("data.sqlite")))


def db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS device_commands (
                device_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                color TEXT NOT NULL,
                brightness INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                last_seen INTEGER NOT NULL,
                ip_address TEXT,
                current_mode TEXT,
                current_color TEXT,
                current_brightness INTEGER
            )
            """
        )


def json_response(handler, status_code, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    add_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(body)


def empty_response(handler, status_code):
    handler.send_response(status_code)
    add_cors_headers(handler)
    handler.end_headers()


def add_cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def parse_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(content_length) if content_length else b"{}"

    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None

class SmartCobbleHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        empty_response(self, 204)

    def do_GET(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) == 5 and parts[:3] == ["api", "devices", parts[2]] and parts[3:] == ["commands", "latest"]:
            self.handle_get_latest_command(parts[2])
            return

        if len(parts) == 4 and parts[:3] == ["api", "devices", parts[2]] and parts[3] == "status":
            self.handle_get_status(parts[2])
            return

        json_response(self, 404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) == 4 and parts[:3] == ["api", "devices", parts[2]] and parts[3] == "commands":
            self.handle_post_command(parts[2])
            return

        if len(parts) == 4 and parts[:3] == ["api", "devices", parts[2]] and parts[3] == "heartbeat":
            self.handle_post_heartbeat(parts[2])
            return

        json_response(self, 404, {"error": "Not found"})

    def handle_post_command(self, device_id):
        payload = parse_body(self)

        if payload is None:
            json_response(self, 400, {"error": "Invalid JSON"})
            return

        mode = payload.get("mode")
        color = payload.get("color")
        brightness = payload.get("brightness")

        if mode not in {"solid", "siri", "off"}:
            json_response(self, 400, {"error": "Invalid mode"})
            return

        if not isinstance(color, str) or len(color) != 6:
            json_response(self, 400, {"error": "Color must be a 6-character hex string"})
            return

        if not isinstance(brightness, int) or brightness < 0 or brightness > 100:
            json_response(self, 400, {"error": "Brightness must be an integer from 0 to 100"})
            return

        now = int(time.time())

        with db_connection() as connection:
            connection.execute(
                """
                INSERT INTO device_commands (device_id, mode, color, brightness, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    mode = excluded.mode,
                    color = excluded.color,
                    brightness = excluded.brightness,
                    updated_at = excluded.updated_at
                """,
                (device_id, mode, color.lower(), brightness, now),
            )

        json_response(
            self,
            200,
            {
                "ok": True,
                "deviceId": device_id,
                "mode": mode,
                "color": color.lower(),
                "brightness": brightness,
                "updatedAt": now,
            },
        )

    def handle_get_latest_command(self, device_id):
        with db_connection() as connection:
            row = connection.execute(
                """
                SELECT device_id, mode, color, brightness, updated_at
                FROM device_commands
                WHERE device_id = ?
                """,
                (device_id,),
            ).fetchone()

        if row is None:
            json_response(
                self,
                200,
                {
                    "deviceId": device_id,
                    "mode": "off",
                    "color": "000000",
                    "brightness": 0,
                    "updatedAt": 0,
                },
            )
            return

        json_response(
            self,
            200,
            {
                "deviceId": row["device_id"],
                "mode": row["mode"],
                "color": row["color"],
                "brightness": row["brightness"],
                "updatedAt": row["updated_at"],
            },
        )

    def handle_post_heartbeat(self, device_id):
        payload = parse_body(self)

        if payload is None:
            json_response(self, 400, {"error": "Invalid JSON"})
            return

        now = int(time.time())
        mode = payload.get("mode")
        color = payload.get("color")
        brightness = payload.get("brightness")

        with db_connection() as connection:
            connection.execute(
                """
                INSERT INTO device_status (
                    device_id, last_seen, ip_address, current_mode, current_color, current_brightness
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    ip_address = excluded.ip_address,
                    current_mode = excluded.current_mode,
                    current_color = excluded.current_color,
                    current_brightness = excluded.current_brightness
                """,
                (
                    device_id,
                    now,
                    self.client_address[0],
                    mode,
                    color,
                    brightness,
                ),
            )

        json_response(self, 200, {"ok": True, "deviceId": device_id, "lastSeen": now})

    def handle_get_status(self, device_id):
        with db_connection() as connection:
            status_row = connection.execute(
                """
                SELECT device_id, last_seen, ip_address, current_mode, current_color, current_brightness
                FROM device_status
                WHERE device_id = ?
                """,
                (device_id,),
            ).fetchone()
            command_row = connection.execute(
                """
                SELECT mode, color, brightness, updated_at
                FROM device_commands
                WHERE device_id = ?
                """,
                (device_id,),
            ).fetchone()

        json_response(
            self,
            200,
            {
                "deviceId": device_id,
                "online": bool(status_row and int(time.time()) - status_row["last_seen"] < 30),
                "lastSeen": status_row["last_seen"] if status_row else None,
                "ipAddress": status_row["ip_address"] if status_row else None,
                "currentMode": status_row["current_mode"] if status_row else None,
                "currentColor": status_row["current_color"] if status_row else None,
                "currentBrightness": status_row["current_brightness"] if status_row else None,
                "latestCommand": (
                    {
                        "mode": command_row["mode"],
                        "color": command_row["color"],
                        "brightness": command_row["brightness"],
                        "updatedAt": command_row["updated_at"],
                    }
                    if command_row
                    else None
                ),
            },
        )

    def log_message(self, format_string, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format_string % args))


def main():
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), SmartCobbleHandler)
    print("Smart Cobble backend listening on %s:%s" % (HOST, PORT))
    server.serve_forever()


if __name__ == "__main__":
    main()
