#!/usr/bin/env python3
"""Exercise the configured Alloy pipeline with synthetic Docker JSON logs."""

from __future__ import annotations

import gzip
import http.server
import json
from pathlib import Path
import re
import socketserver
import subprocess
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.grafana.yaml"
CONFIG_FILE = ROOT / "docker/alloy/config.alloy"


class LokiReceiver(http.server.BaseHTTPRequestHandler):
    requests: list[bytes] = []

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        payload = self.rfile.read(int(self.headers["Content-Length"]))
        if payload.startswith(b"\x1f\x8b"):
            payload = gzip.decompress(payload)
        self.requests.append(payload)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args: object) -> None:
        pass


def main() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    image_match = re.search(r"^\s+image:\s+(grafana/alloy:[^\s]+)$", compose, re.MULTILINE)
    if not image_match:
        raise RuntimeError("Could not find the pinned Alloy image in Compose")
    image = image_match.group(1)

    subprocess.run(
        [
            "docker", "run", "--rm", "--entrypoint=/bin/alloy",
            "-e", "COMPOSE_PROJECT_NAME=music-tool-bot",
            "-e", "GRAFANA_CLOUD_LOKI_URL=http://127.0.0.1:3100/loki/api/v1/push",
            "-e", "GRAFANA_CLOUD_LOKI_USERNAME=test", "-e", "GRAFANA_CLOUD_API_KEY=test",
            "-v", f"{CONFIG_FILE}:/etc/alloy/config.alloy:ro",
            image, "validate", "/etc/alloy/config.alloy",
        ],
        cwd=ROOT,
        check=True,
    )

    LokiReceiver.requests.clear()
    with socketserver.TCPServer(("127.0.0.1", 0), LokiReceiver) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory(prefix="alloy-redaction-") as temporary:
            root = Path(temporary)
            container_logs = root / "containers"
            sample_dir = container_logs / "synthetic-container"
            sample_dir.mkdir(parents=True)
            sample_file = sample_dir / "synthetic-json.log"
            sample_file.touch()

            command = [
                "docker", "run", "--rm", "--network=host",
                "-e", f"COMPOSE_PROJECT_NAME=music-tool-bot",
                "-e", f"GRAFANA_CLOUD_LOKI_URL=http://127.0.0.1:{server.server_address[1]}/loki/api/v1/push",
                "-e", "GRAFANA_CLOUD_LOKI_USERNAME=test",
                "-e", "GRAFANA_CLOUD_API_KEY=test",
                "-v", f"{container_logs}:/var/lib/docker/containers:ro",
                "-v", f"{CONFIG_FILE}:/etc/alloy/config.alloy:ro",
                image, "run", "--server.http.listen-addr=127.0.0.1:6010",
                "--storage.path=/tmp/alloy-test-data", "/etc/alloy/config.alloy",
            ]
            process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            try:
                time.sleep(2)
                if process.poll() is not None:
                    raise RuntimeError(f"Alloy exited during startup with status {process.returncode}")

                now = "2026-11-02T12:00:00.000000000Z"
                attrs = {
                    "com.docker.compose.project": "music-tool-bot",
                    "com.docker.compose.service": "bot",
                }
                samples = [
                    {
                        "log": "2026-11-02 12:00:00 INFO [music_tool_bot] User 6230368243 completed output=/data/private/6230368243.mp3\n",
                        "stream": "stdout", "time": now, "attrs": attrs,
                    },
                    {
                        "log": "2026-11-02 12:00:01 INFO User 777 sent message while in module=core username=Alice text=private-chat-text\n",
                        "stream": "stdout", "time": now, "attrs": attrs,
                    },
                    {
                        "log": "2026-11-02 12:00:02 INFO User 888 changed username from old_name to new_name\n",
                        "stream": "stdout", "time": now, "attrs": attrs,
                    },
                    {
                        "log": "NON_BOT_MUST_NOT_SHIP\n", "stream": "stdout", "time": now,
                        "attrs": {**attrs, "com.docker.compose.service": "worker"},
                    },
                    {
                        "log": "OTHER_PROJECT_MUST_NOT_SHIP\n", "stream": "stdout", "time": now,
                        "attrs": {**attrs, "com.docker.compose.project": "other-project"},
                    },
                ]
                with sample_file.open("a", encoding="utf-8") as stream:
                    for sample in samples:
                        stream.write(json.dumps(sample) + "\n")

                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and not LokiReceiver.requests and process.poll() is None:
                    time.sleep(0.2)
                if process.poll() is not None:
                    raise RuntimeError(f"Alloy exited while processing logs with status {process.returncode}")
                if not LokiReceiver.requests:
                    raise AssertionError("Alloy did not send the synthetic bot log to the Loki receiver")

                forwarded = b"\n".join(LokiReceiver.requests)
                for forbidden in (b"6230368243", b"777", b"888", b"/data/private", b"private-chat-text", b"Alice", b"old_name", b"new_name", b"NON_BOT_MUST_NOT_SHIP", b"OTHER_PROJECT_MUST_NOT_SHIP", b"/var/lib/docker/containers"):
                    if forbidden in forwarded:
                        raise AssertionError(f"Sensitive or out-of-scope content reached Loki: {forbidden!r}")
                for expected in (b"[REDACTED_USER]", b"[PATH]"):
                    if expected not in forwarded:
                        raise AssertionError(f"Expected redaction marker missing from Loki payload: {expected!r}")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        server.shutdown()

    print("PASS: Alloy filters unrelated logs, drops message content, and redacts user IDs and paths.")


if __name__ == "__main__":
    main()
