"""Local web server for the pixel-art version of Talk Past the Guard.

    python server.py            then open http://localhost:8000
    python server.py --port 8080

UI only, not part of the turn-in. API keys stay here on the server; the
browser only ever sees the guard's replies and the verdicts.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from game_engine import ENDINGS, MAX_TURNS, SUSPICION_LIMIT, GameSession, make_judge
from scenarios import SCENARIOS

INDEX = Path(__file__).parent / "web" / "index.html"
MAX_LINE = 600

_sessions: dict[str, tuple[GameSession, str, str]] = {}  # id -> (game, judge kind, model)
_judges: dict[str, tuple[str, object]] = {}
_lock = threading.Lock()


def load_windows_user_env(name: str):
    """A terminal opened before `setx` doesn't see new variables; read the saved one."""
    if os.environ.get(name) or os.name != "nt":
        return
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            os.environ[name] = winreg.QueryValueEx(key, name)[0]
    except OSError:
        pass


def available_judges() -> dict[str, bool]:
    return {
        "gpt": bool(os.environ.get("OPENAI_API_KEY")),
        "jev": bool(os.environ.get("TYPESAFE_API_KEY")),
    }


def get_judge(kind: str):
    with _lock:
        if kind not in _judges:
            _judges[kind] = make_judge(kind)
        return _judges[kind]


def scenario_info(key: str) -> dict:
    s = SCENARIOS[key]
    return {
        "key": s.key,
        "title": s.title,
        "guard": s.guard,
        "setting": s.setting,
        "goal": s.goal,
        "clues": [line.removeprefix("- ") for line in s.player_knows.splitlines()],
        "opening_line": s.opening_line,
    }


def new_game(body: dict) -> dict:
    kind = body.get("judge", "gpt")
    if kind not in ("gpt", "jev"):
        raise ValueError("judge must be 'gpt' or 'jev'.")
    if not available_judges()[kind]:
        raise ValueError(f"No API key set for the {kind} judge.")
    key = body.get("scenario") or random.choice(list(SCENARIOS))
    if key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {key}")

    model, judge = get_judge(kind)
    game_id = uuid.uuid4().hex
    with _lock:
        _sessions[game_id] = (GameSession(SCENARIOS[key], judge), kind, model)
    return {
        "id": game_id,
        "judge": kind,
        "model": model,
        "max_turns": MAX_TURNS,
        "suspicion_limit": SUSPICION_LIMIT,
        "scenario": scenario_info(key),
    }


def take_turn(body: dict) -> dict:
    with _lock:
        entry = _sessions.get(body.get("id", ""))
    if not entry:
        raise ValueError("Unknown game. Start a new one.")
    game, _, _ = entry
    line = str(body.get("line", "")).strip()[:MAX_LINE]
    if not line:
        raise ValueError("Say something to the guard first.")

    result = game.take_turn(line)
    v = result.verdict
    return {
        "reply": result.reply,
        "closing_line": result.closing_line,
        "decision": v.decision,
        "raw_decision": v.raw_decision,
        "confidence": v.confidence,
        "persuasiveness": v.persuasiveness,
        "out_of_character": v.out_of_character,
        "probabilities": v.probabilities,
        "rationale": v.rationale,
        "latency_ms": round(v.latency_s * 1000),
        "turn": game.turn,
        "suspicion": game.suspicion,
        "outcome": game.outcome,
        "ending": ENDINGS.get(game.outcome or ""),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict):
        self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/config":
            self._json(200, {"judges": available_judges(), "scenarios": [scenario_info(k) for k in SCENARIOS]})
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        routes = {"/api/new": new_game, "/api/turn": take_turn}
        handler = routes.get(self.path)
        if not handler:
            self._json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._json(200, handler(body))
        except ValueError as error:
            self._json(400, {"error": str(error)})
        except Exception as error:  # judge/API failures: show them in the game instead of crashing
            self._json(502, {"error": f"{type(error).__name__}: {error}"})

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/turn"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the pixel-art guard game.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    load_windows_user_env("OPENAI_API_KEY")
    load_windows_user_env("TYPESAFE_API_KEY")
    judges = available_judges()
    print(f"Judges available: gpt={'yes' if judges['gpt'] else 'NO KEY'}, jev={'yes' if judges['jev'] else 'NO KEY'}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Talk Past the Guard: open http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
