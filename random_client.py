# random_client.py — a Sophia-free, dependency-free example AI client.
#
# The neutrality proof: it implements the two AI-side routes with nothing but the
# Python standard library and picks a uniformly random legal move. No grammar, no
# personality, no model — if THIS can play, any runtime wrapping two routes can.
#
#   POST /state           -> 202 immediately; "think" in the background, stash a move
#   GET  /move/<turn_id>  -> 204 while thinking; 200 {"move": token} once decided
#
# Run two instances to play the engine against itself, fully headless:
#   python random_client.py 6001
#   python random_client.py 6002
# then start the engine (its AI_WHITE/AI_BLACK default to those ports).

import json
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

THINK_SECONDS = 0.5      # artificial latency so the engine's poll sees 204 before 200

_lock  = threading.Lock()
_moves = {}              # turn_id -> chosen move token, once decided


def _choose(payload):
    """The entire 'intelligence': one uniformly random legal token. Returns None
    when there's nothing to pick from — a terminal turn, or a shape-only game
    (no enumerated set) that this dumb client simply doesn't play."""
    if payload.get("terminal"):
        return None
    legal = payload.get("legal_moves")
    return random.choice(legal) if legal else None


def _think(turn_id, payload):
    time.sleep(THINK_SECONDS)                    # pretend to deliberate
    move = _choose(payload)
    if move:                                     # abstain -> never stash -> engine re-fires
        with _lock:
            _moves[turn_id] = move


class Handler(BaseHTTPRequestHandler):
    # ---- POST /state : ack fast, think in background -------------------------
    def do_POST(self):
        if self.path.rstrip("/") == "/state":
            payload = self._read_json()          # consume body before responding
            self._send(202)
            turn_id = str(payload.get("turn_id") or "").strip()
            if turn_id and not payload.get("terminal"):
                threading.Thread(target=_think, args=(turn_id, payload),
                                 daemon=True).start()
            return
        self._send(404)

    # ---- GET /move/<turn_id> : 204 until ready, then one-shot 200 -----------
    def do_GET(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "move":
            turn_id = parts[1]
            with _lock:
                move = _moves.pop(turn_id, None)  # one-shot, mirrors her take_move
            if move:
                self._json(200, {"move": move})
            else:
                self._send(204)                   # still thinking (or abstained)
            return
        self._send(404)

    # ---- helpers ------------------------------------------------------------
    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            return {}

    def _send(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass                                      # quiet; flip to a print to debug


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[random-client] http://127.0.0.1:{port}  (think={THINK_SECONDS}s)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()