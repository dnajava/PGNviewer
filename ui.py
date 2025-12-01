from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTextEdit,
    QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
)

from pgn_viewer2 import ChessGame
from PyQt6.QtCore import Qt
import sys

class PGNViewerWindow(QMainWindow):
    def __init__(self, game: ChessGame):
        super().__init__()
        self.game = game
        self.current_ply = 0
        self.setWindowTitle(f"{game.headers.white} vs {game.headers.black}")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Vasen puoli: siirrot ja headerit
        left = QWidget()
        left_layout = QVBoxLayout(left)

        header_label = QLabel(str(self.game.headers))
        header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        left_layout.addWidget(header_label)

        self.move_text = QTextEdit()
        self.move_text.setReadOnly(True)
        self.move_text.setText(self._format_moves())
        left_layout.addWidget(self.move_text)

        # Napit
        nav = QHBoxLayout()
        prev_btn = QPushButton("← Edellinen")
        next_btn = QPushButton("Seuraava →")
        prev_btn.clicked.connect(self.prev_move)
        next_btn.clicked.connect(self.next_move)
        nav.addWidget(prev_btn)
        nav.addWidget(next_btn)
        left_layout.addLayout(nav)

        # Oikea puoli: shakkilauta (tässä yksinkertainen teksti, mutta voi korvata chess.svg:llä tms.)
        self.board_display = QTextEdit()
        self.board_display.setReadOnly(True)
        self.board_display.setFontFamily("Courier")
        self.update_board()

        splitter.addWidget(left)
        splitter.addWidget(self.board_display)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

    def _format_moves(self) -> str:
        moves = []
        for i, move in enumerate(self.game.moves, 1):
            if i % 2 == 1:
                moves.append(f"{(i+1)//2}. {move}")
            else:
                moves[-1] += f" {move}"
        return " ".join(moves)

    def update_board(self):
        board = self.game.current_board(self.current_ply)
        self.board_display.setText(str(board))

    def prev_move(self):
        if self.current_ply > 0:
            self.current_ply -= 1
            self.update_board()

    def next_move(self):
        if self.current_ply < len(self.game.board_history) - 1:
            self.current_ply += 1
            self.update_board()