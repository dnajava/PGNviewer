import sys
from PyQt6.QtWidgets import QApplication
from ui import PGNViewerWindow
from pgn_viewer2 import ChessGame

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Esimerkki: ladataan PGN-tiedosto

    with open("/path/to/PGN") as f:
        pgn_text = f.read()

    game = ChessGame.from_pgn_string(pgn_text)
    window = PGNViewerWindow(game)
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())
