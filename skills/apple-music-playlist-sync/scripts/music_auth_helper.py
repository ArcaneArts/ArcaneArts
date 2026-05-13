#!/usr/bin/env python3
"""Local MusicKit authorization helper.

Serves a localhost page that asks the user to authorize Apple Music and writes
the resulting Music user token to a local file. This script never prints the
private key or user token.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_developer_token(team_id: str, key_id: str, key_path: Path, ttl_seconds: int = 3600) -> str:
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    now = int(time.time())
    header = {"alg": "ES256", "kid": key_id}
    payload = {"iss": team_id, "iat": now, "exp": now + ttl_seconds}
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    )
    der = private_key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r_value, s_value = utils.decode_dss_signature(der)
    signature = r_value.to_bytes(32, "big") + s_value.to_bytes(32, "big")
    return signing_input + "." + b64url(signature)


def build_handler(developer_token: str, token_path: Path, app_name: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def send_text(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/status":
                self.send_text(200, "authorized" if token_path.exists() and token_path.stat().st_size else "waiting")
                return
            if path != "/":
                self.send_text(404, "not found")
                return

            html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Codex Apple Music Auth</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; max-width: 720px; line-height: 1.45; }}
    button {{ font-size: 16px; padding: 10px 14px; }}
    code {{ background: #f2f2f2; padding: 2px 4px; border-radius: 4px; }}
    #status {{ margin-top: 16px; font-weight: 600; }}
  </style>
  <script src="https://js-cdn.music.apple.com/musickit/v1/musickit.js"></script>
</head>
<body>
  <h1>Authorize Apple Music</h1>
  <p>This local page requests an Apple Music user token so Codex can update your library and playlists through the official API.</p>
  <button id="auth">Authorize Apple Music</button>
  <div id="status">Waiting.</div>
  <script>
    const status = document.getElementById('status');
    document.addEventListener('musickitloaded', async function() {{
      try {{
        await MusicKit.configure({{
          developerToken: {json.dumps(developer_token)},
          app: {{ name: {json.dumps(app_name)}, build: '1.0.0' }}
        }});
        status.textContent = 'Ready. Click Authorize Apple Music.';
      }} catch (err) {{
        status.textContent = 'MusicKit setup failed: ' + err;
      }}
    }});
    document.getElementById('auth').addEventListener('click', async function() {{
      try {{
        status.textContent = 'Opening Apple authorization...';
        const music = MusicKit.getInstance();
        const token = await music.authorize();
        await fetch('/token', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ token }}) }});
        status.textContent = 'Authorized. You can close this page.';
      }} catch (err) {{
        status.textContent = 'Authorization failed: ' + err;
      }}
    }});
  </script>
</body>
</html>"""
            self.send_text(200, html, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/token":
                self.send_text(404, "not found")
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            try:
                token = json.loads(body).get("token", "")
                if not isinstance(token, str) or len(token) < 20:
                    raise ValueError("token missing")
                token_path.write_text(token, encoding="utf-8")
                os.chmod(token_path, 0o600)
                self.send_text(200, "ok")
                print("USER_TOKEN_RECEIVED", flush=True)
            except Exception:
                self.send_text(400, "bad token")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a local Apple Music authorization helper.")
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--key-path", required=True, type=Path)
    parser.add_argument("--token-path", default="/tmp/apple_music_user_token.txt", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--app-name", default="Codex Music Helper")
    args = parser.parse_args()

    args.token_path.unlink(missing_ok=True)
    developer_token = make_developer_token(args.team_id, args.key_id, args.key_path)
    handler = build_handler(developer_token, args.token_path, args.app_name)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Open http://localhost:{args.port}/ to authorize Apple Music. Waiting for token...", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
