from __future__ import annotations
from dataclasses import dataclass as immutable_dataclass
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Dict
import chess  # python-chess kirjasto (pip install chess)
import chess.pgn
import io, ui
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTextEdit,
    QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
)


class Result(Enum):
    WHITE_WINS = "1-0"
    BLACK_WINS = "0-1"
    DRAW = "1/2-1/2"
    ONGOING = "*"


@immutable_dataclass(frozen=True)
class Player:
    """Yhden pelaajan tiedot"""
    name: str
    elo: Optional[int] = None
    title: Optional[str] = None          # GM, IM, FM...
    fide_id: Optional[int] = None

    def __str__(self) -> str:
        parts = [self.name]
        if self.title:
            parts.insert(0, self.title)
        if self.elo:
            parts.append(f"({self.elo})")
        return " ".join(parts)


@dataclass
class GameHeaders:
    """PGN-tiedoston header-osio (kaikki standardit tagit)"""
    event: str = "?"
    site: str = "?"
    date: Optional[date] = None
    round: str = "?"
    white: Player = field(default_factory=Player)
    black: Player = Player(name="?")
    result: Result = Result.ONGOING
    eco: Optional[str] = None
    opening: Optional[str] = None
    variation: Optional[str] = None

    # Lisää tarvittaessa: annotator, plycount terminaton jne.


@dataclass
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
        board = game.board()  # Lisää tämä ennen silmukkaa!
        for node in game.mainline():
            if node.move:
                moves.append(board.san(node.move))
                board.push(node.move)  # Ilman tätä seuraava siirto menee pieleen!
            else:
                self.moves.append("")

        while node.variations:
            next_node = node.variation(0)
            # moves.append(next_node.move.san() if next_node.move else "")
            # Oikea tapa saada SAN-merkintä chess-kirjastolla
            if next_node.move:
                moves.append(board.san(next_node.move))
            else:
                moves.append("")
            node = next_node

        return cls(headers=game_headers, moves=moves)


# Apufunktiot
import io
def _parse_elo(elo_str: Optional[str]) -> Optional[int]:
    if not elo_str or elo_str == "?":
        return None
    try:
        return int(elo_str)
    except ValueError:
        return None

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str or date_str == "??" or date_str == "????.??.??":
        return None
    # Yksinkertainen parseri, voi laajentaa
    try:
        return date.fromisoformat(date_str.replace(".", "-"))
    except:
        return None