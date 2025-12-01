"""
Tämä on

paljon helpommin ylläpidettävän
testattavan
laajennettavan (esim. useampi peli, turnausten selaus, tekoälyanalyysi jne.)
ja ennen kaikkea ammattimaisemman näköisen
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Dict
import chess  # python-chess kirjasto (pip install chess)
import chess.pgn

class ChessGame:
    """Yksi kokonainen shakkipeli"""
    headers: GameHeaders
    moves: List[str] = field(default_factory=list)        # SAN-siirrot: ["e4", "e5", ...]
    board_history: List[chess.Board] = field(default_factory=list)  # jokainen asema
    comments: Dict[int, str] = field(default_factory=dict)  # puolinumero -> kommentti

    def __post_init__(self) -> None:
        # Ladataan peli chess.pgn:stä tai rakennetaan käsin
        self._build_board_history()

    def _build_board_history(self) -> None:
        board = chess.Board()
        self.board_history = [board.copy()]

        for move_san in self.moves:
            move = board.parse_san(move_san)
            board.push(move)
            self.board_history.append(board.copy())

    def current_board(self, ply: int = -1) -> chess.Board:
        """Palauttaa laudan annetulla vuorolla (ply = puolinumero, -1 = viimeisin)"""
        return self.board_history[max(0, min(ply, len(self.board_history) - 1))]

    @classmethod
    def from_pgn_string(cls, pgn: str) -> "ChessGame":
        """Luo ChessGame-olion suoraan PGN-tekstistä (helpoin tapa)"""
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            raise ValueError("Virheellinen PGN")

        headers = game.headers

        white = Player(
            name=headers.get("White", "?"),
            elo=_parse_elo(headers.get("WhiteElo")),
            title=headers.get("WhiteTitle")
        )
        black = Player(
            name=headers.get("Black", "?"),
            elo=_parse_elo(headers.get("BlackElo")),
            title=headers.get("BlackTitle")
        )

        game_headers = GameHeaders(
            event=headers.get("Event", "?"),
            site=headers.get("Site", "?"),
            date=_parse_date(headers.get("Date")),
            round=headers.get("Round", "?"),
            white=white,
            black=black,
            result=Result(headers.get("Result", "*")),
            eco=headers.get("ECO"),
            opening=headers.get("Opening"),
            variation=headers.get("Variation")
        )

        moves = []
        node = game
        while node.variations:
            next_node = node.variation(0)
            moves.append(next_node.move.san() if next_node.move else "")
            node = next_node

        return cls(headers=game_headers, moves=moves)