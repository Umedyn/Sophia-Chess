import chess

from game import Game


class ChessGame(Game):
    _VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
               chess.ROOK: 5, chess.QUEEN: 9}

    def __init__(self, starting_fen: str | None = None):
        self.board = chess.Board(starting_fen) if starting_fen else chess.Board()
        self._last_san = None            # SAN of the opponent's last move, for render

    # ---- protocol surface ---------------------------------------------------
    def render_state(self) -> str:
        b = self.board
        mover = "White" if b.turn == chess.WHITE else "Black"
        lines = [f"Chess — move {b.fullmove_number}, {mover} to play."]

        bal = self._material_balance()
        if bal:
            leader = "White" if bal > 0 else "Black"
            lines.append(f"{leader} leads by {abs(bal)} in material.")
        else:
            lines.append("Material is even.")

        if self._last_san:                                  # absent on the very first turn
            opp = "Black" if b.turn == chess.WHITE else "White"
            lines.append(f"{opp} just played {self._last_san}.")
        if b.is_check():
            lines.append(f"{mover} is in check.")

        lines.append(f"{mover}, choose your move.")          # decision point last
        return "\n".join(lines)

    def legal_actions(self):
        return [m.uci() for m in self.board.legal_moves]     # promotions included, e.g. e7e8q

    def is_legal(self, token: str) -> bool:
        try:
            mv = chess.Move.from_uci(token)                  # rejects malformed
        except ValueError:
            return False
        return mv in self.board.legal_moves                  # re-generated each call

    def apply_action(self, token: str) -> None:
        mv = chess.Move.from_uci(token)                      # is_legal already passed
        self._last_san = self.board.san(mv)                  # SAN before push (relative to this position)
        self.board.push(mv)

    def is_terminal(self) -> bool:
        return self.board.is_game_over()

    def result(self) -> dict:
        outcome = self.board.outcome()
        if outcome is None:
            return {"over": False}
        return {
            "over": True,
            "result": outcome.result(),                      # "1-0" / "0-1" / "1/2-1/2"
            "reason": outcome.termination.name.lower(),      # "checkmate", "stalemate", ...
            "winner": (None if outcome.winner is None
                       else ("white" if outcome.winner else "black")),
        }

    def structured_state(self) -> dict:
        return {"fen": self.board.fen()}     # harmless for AIs that ignore it

    def terminal_message(self, perspective: str | None = None) -> str:
        o = self.board.outcome()
        if o is None:
            return "The game is over."
        if o.winner is None:
            reason = o.termination.name.replace("_", " ").lower()
            return f"The game is over — a draw by {reason}."
        winner = "white" if o.winner else "black"      # standard chess: a win is checkmate
        if perspective == winner:
            return f"Checkmate — you win, playing {winner}!"
        if perspective in ("white", "black"):
            return f"Checkmate — you lose. {winner.capitalize()} wins."
        return f"Checkmate — {winner} wins."

    def render_view(self) -> dict:
        return {
            "fen":   self.board.fen(),      # the page draws pieces from this
            "check": self.board.is_check(), # highlight the side-to-move's king
        }

    def move_labels(self):
        # SAN is unique per legal move (python-chess disambiguates), so the
        # reverse map is clean. Empty on a terminal board — no gloss added.
        return {m.uci(): self.board.san(m) for m in self.board.legal_moves}

    # ---- helpers ------------------------------------------------------------
    def _material_balance(self) -> int:
        b = self.board
        return sum(val * (len(b.pieces(pt, chess.WHITE)) - len(b.pieces(pt, chess.BLACK)))
                   for pt, val in self._VALUES.items())