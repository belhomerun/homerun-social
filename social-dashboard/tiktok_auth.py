#!/usr/bin/env python3
"""
One-time TikTok OAuth flow.
Run: python3 tiktok_auth.py
Opens TikTok in browser → you approve → tokens saved to homerun/.env
"""

import urllib.request
import urllib.parse
import json
import webbrowser
import secrets
import hashlib
import base64
import http.server
import threading
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent.parent / "homerun" / ".env"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "user.info.basic,user.info.stats,video.list"


def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def save_tokens(access_token, refresh_token, open_id):
    lines = ENV_FILE.read_text().splitlines()
    keys_to_update = {
        "TIKTOK_ACCESS_TOKEN": access_token,
        "TIKTOK_REFRESH_TOKEN": refresh_token,
        "TIKTOK_OPEN_ID": open_id,
    }
    updated = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            k = stripped.split("=", 1)[0].strip()
            if k in keys_to_update:
                new_lines.append(f"{k}={keys_to_update[k]}")
                updated.add(k)
                continue
        new_lines.append(line)
    for k, v in keys_to_update.items():
        if k not in updated:
            new_lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    print(f"  Saved {', '.join(keys_to_update.keys())} to .env")


def exchange_code(code, client_key, client_secret, code_verifier):
    payload = json.dumps({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }).encode()
    req = urllib.request.Request(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main():
    env = load_env()
    client_key = env.get("TIKTOK_CLIENT_KEY")
    client_secret = env.get("TIKTOK_CLIENT_SECRET")
    if not client_key or not client_secret:
        print("TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be in homerun/.env")
        raise SystemExit(1)

    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/?"
        + urllib.parse.urlencode({
            "client_key": client_key,
            "response_type": "code",
            "scope": SCOPES,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
    )

    code_holder = {}
    server_done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if "code" in params:
                code_holder["code"] = params["code"]
                self.wfile.write(b"<h2>Authorised. You can close this tab.</h2>")
            else:
                self.wfile.write(b"<h2>Error - no code returned. Try again.</h2>")
            server_done.set()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("localhost", 8080), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    print("\nOpening TikTok in your browser...")
    print("Log in as @homerun.app and approve access.\n")
    webbrowser.open(auth_url)

    server_done.wait(timeout=120)
    server.shutdown()

    code = code_holder.get("code")
    if not code:
        print("No code received. Did you approve access in the browser?")
        raise SystemExit(1)

    print("Exchanging code for tokens...")
    result = exchange_code(code, client_key, client_secret, code_verifier)

    if "access_token" not in result:
        print(f"Token exchange failed: {result}")
        raise SystemExit(1)

    save_tokens(result["access_token"], result.get("refresh_token", ""), result.get("open_id", ""))
    print("\nDone! TikTok connected. Run dashboard.py to fetch real data.")


if __name__ == "__main__":
    main()
