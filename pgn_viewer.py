import os, io, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import zstandard as zstd
import chess, chess.pgn, chess.svg, cairosvg
from PIL import Image, ImageTk

from createtooltip import CreateToolTip

DEFAULT_PGN_DIR = "/path/to/files"
CHUNK_SIZE = 32 * 1024  # 32 KB


def load_zst_with_progress(path, progressbar, add_game_callback, on_done_callback=None):
    try:
        filesize = os.path.getsize(path)
        progressbar.config(mode="determinate", maximum=filesize, value=0)

        dctx = zstd.ZstdDecompressor()
        total_read = 0
        buffer = b""
        with open(path, "rb") as f:
            with dctx.stream_reader(f) as reader:
                while True:
                    chunk = reader.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    buffer += chunk
                    total_read += len(chunk)

                    while b"\n\n" in buffer:
                        game, buffer = buffer.split(b"\n\n", 1)
                        add_game_callback(game.decode("utf-8", errors="ignore"))

                    progressbar.after(0, lambda tr=total_read: progressbar.config(value=tr))

        if buffer.strip():
            add_game_callback(buffer.decode("utf-8", errors="ignore"))

    except Exception as e:
        if on_done_callback:
            on_done_callback(error=e)
        return

    if on_done_callback:
        on_done_callback()

def stream_pgn(path):
    game_lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() == "" and game_lines:
                yield "".join(game_lines)
                game_lines = []
            else:
                game_lines.append(line)
    if game_lines:
        yield "".join(game_lines)

def svg_board_image_bytes(board, size=480):
    svg = chess.svg.board(board=board, size=size)
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"))

class PGNViewer:
    games: list
    current_index: int
    filepath: str
    game_moves: list
    current_move_index: int
    default_dir: str
    stockfish_var: int

    # board, photo

    def __init__(self, root):
        self.default_dir = os.path.expanduser(DEFAULT_PGN_DIR)
        if not os.path.exists(self.default_dir):
            try:
                os.makedirs(self.default_dir)
            except Exception:
                self.default_dir = "."

        self.root = root
        self.root.title("PGN Viewer")

        # Data
        self.games = []
        self.current_index = 0
        self.filepath = ""
        self.board = None
        self.game_moves = []
        self.current_move_index = 0
        self.photo = None
        self.stockfish_var = 0

        # --- Pääkehys ---
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Pelilista vasemmalle
        left = tk.Frame(main_frame)
        left.pack(side="left", fill="y", padx=4, pady=4)
        ttk.Label(left, text="Pelilista").pack(anchor="w")
        self.game_list = tk.Listbox(left, width=40, height=30)
        self.game_list.pack(fill="y", expand=False)
        self.game_list.bind("<<ListboxSelect>>", self.on_select_list)
        self.tooltip = CreateToolTip(self.game_list)

        # --- Oikea puoli: kaikki siististi pystysuunnassa ---
        right = tk.Frame(main_frame)
        right.pack(side="right", fill="both", expand=True, padx=8, pady=8)


        # 1. Pelin navigointipainikkeet ylhäällä
        top_btns = tk.Frame(right)
        top_btns.pack(fill="x", pady=(0, 10))

        self.first_game_btn = tk.Button(top_btns, text="<<", command=self.first_game, width=5)
        self.first_game_btn.pack(side="left", padx=2)
        self.prev_game_btn = tk.Button(top_btns, text="<", command=self.prev_game, width=5)
        self.prev_game_btn.pack(side="left", padx=2)

        self.game_number_label = tk.Label(top_btns, text="Peli 0/0", font=("Arial", 11), width=15)
        self.game_number_label.pack(side="left", padx=30)

        self.next_game_btn = tk.Button(top_btns, text=">", command=self.next_game, width=5)
        self.next_game_btn.pack(side="left", padx=2)
        self.last_game_btn = tk.Button(top_btns, text=">>", command=self.last_game, width=5)
        self.last_game_btn.pack(side="left", padx=2)


        # 2. SHAKKILAUTA – Ottaa kaiken mahdollisen tilan leveydestä
        board_frame = tk.Frame(right)
        board_frame.pack(fill="both", expand=True) # , pady=(0, 10)

        # Vasen osa = shakkilauta (ottaa kaiken vapaan leveyn)
        board_container = tk.Frame(board_frame, bg="#F0D9B5")
        board_container.pack(side="left", fill="both", expand=True)

        # Varsinainen canvaksen koko mukautuu neliöksi
        self.board_canvas = tk.Canvas(board_container, bg="#F0D9B5", highlightthickness=0)
        self.board_canvas.pack(fill="both", expand=True, padx=20, pady=20)  # 30 px ruskea reuna joka puolella
        self.board_canvas.bind("<Configure>", self.on_resize)

        # Oikea osa = pelaajien nimet + siirtonapit (kiinteä leveys)
        side_panel = tk.Frame(board_frame, width=200)
        side_panel.pack(side="right", fill="y")
        side_panel.pack_propagate(False)  # estää kutistumisen

        playernamesize = 9            # Pelaajien nimet (iso fontti, nätisti)
        # tk.Label(side_panel, text="Mustat", font=("Arial", playernamesize, "italic"), fg="gray40").pack(anchor="w", pady=(40, 0))
        self.black_label = tk.Label(side_panel, text="", font=("Arial", playernamesize, "bold"), fg="black", bg="#F0D9B5")
        self.black_label.pack(anchor="w", pady=(0, 20))

        # tk.Label(side_panel, text="Valkeat", font=("Arial", playernamesize, "italic"), fg="gray40").pack(anchor="w")
        self.white_label = tk.Label(side_panel, text="", font=("Arial", playernamesize, "bold"), fg="black", bg="#F0D9B5")
        self.white_label.pack(anchor="w", pady=(0, 40))

        # 3. Siirtojen navigointipainikkeet laudan alla
        move_btns = tk.Frame(right)
        move_btns.pack(fill="x", pady=(0, 12))

        self.first_move_btn = tk.Button(move_btns, text="<<", command=self.first_move, width=5)
        self.first_move_btn.pack(side="left", padx=2)
        self.prev_move_btn = tk.Button(move_btns, text="<", command=self.prev_move, width=5)
        self.prev_move_btn.pack(side="left", padx=2)

        self.move_number_label = tk.Label(move_btns, text="Siirto 0/0", font=("Arial", 11), width=15)
        self.move_number_label.pack(side="left", padx=30)

        self.next_move_btn = tk.Button(move_btns, text=">", command=self.next_move, width=5)
        self.next_move_btn.pack(side="left", padx=2)
        self.last_move_btn = tk.Button(move_btns, text=">>", command=self.last_move, width=5)
        self.last_move_btn.pack(side="left", padx=2)


        # 4. Loput pienet kontrollit & PGN-teksti
        bottom_frame = tk.Frame(right)
        bottom_frame.pack(fill="both", expand=False)

        tk.Button(bottom_frame, text="Avaa pgn tai zst", command=self.open_file).pack(side="left", padx=(0, 20))
        tk.Radiobutton(bottom_frame, text="Stockfish", variable=self.stockfish_var, value=1).pack(side="left")

        ttk.Label(right, text="Pelin PGN", font=("Arial", 10, "bold")).pack(anchor="w", pady=(20, 4))
        self.text = scrolledtext.ScrolledText(right, height=9, font=("Consolas", 9))
        self.text.pack(fill="both", expand=True, pady=(0, 10))

        # Haku
        search_frame = tk.Frame(right)
        search_frame.pack(fill="x", pady=4)
        ttk.Label(search_frame, text="Haku:").pack(side="left")
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)

        self.progress = ttk.Progressbar(right, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))


    def add_game(self, game_text):
        self.games.append(game_text)
        preview = self._make_preview(game_text)
        self.root.after(0, lambda: self.game_list.insert(tk.END, preview))

    def _make_preview(self, game_text):
        try:
            lines = game_text.splitlines()
            white = next((l.split('"')[1] for l in lines if l.startswith('[White ')), "?")
            black = next((l.split('"')[1] for l in lines if l.startswith('[Black ')), "?")
            res = next((l.split('"')[1] for l in lines if l.startswith('[Result ')), "")
            eco = next((l.split('"')[1] for l in lines if l.startswith('[ECO ')), "")
            opening = next((l.split('"')[1] for l in lines if l.startswith('[Opening ')), "")

            # UTF-8 lopputulosmerkki
            if res == "1-0":
                result_symbol = "⚪"
            elif res == "0-1":
                result_symbol = "⚫"
            elif res == "1/2-1/2":
                result_symbol = "="
            else:
                result_symbol = "?"

            self.tooltip_text = f"ECO: {eco}\nOpening: {opening}"
            return f"{result_symbol}  {white} — {black}"

        except Exception:
            return game_text[:40] + "..."

    def open_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("PGN and ZST files", "*.pgn *.zst"), ("All files", "*.*")]
        )
        if not path:
            return

        self.game_list.delete(0, tk.END)
        self.text.delete("1.0", tk.END)
        self.games = []
        self.current_index = 0
        self.filepath = path
        self.progress.pack(side="bottom", fill="x", pady=4)

        if path.endswith(".zst"):
            def on_done(error=None):
                def finish():
                    self.progress.pack_forget()
                    if error:
                        messagebox.showerror("Virhe", f"ZST-lataus epäonnistui: {error}")

                self.root.after(0, finish)

            t = threading.Thread(target=lambda: load_zst_with_progress(path, self.progress, self.add_game, on_done),
                                 daemon=True)
            t.start()
        else:
            def read_pgn():
                try:
                    for g in stream_pgn(path):
                        self.add_game(g)
                finally:
                    self.root.after(0, lambda: self.progress.pack_forget())

                if self.games:
                    self.current_index = 0
                    self.game_list.select_set(0)
                    self.load_selected_game()

            threading.Thread(target=read_pgn, daemon=True).start()

    def load_selected_game(self):
        if self.current_index is None:
            return
        self.board = chess.Board()
        self.game_moves = []
        self.current_move_index = 0

        # Tyhjennä ja täytä PGN-teksti
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, self.games[self.current_index])

        # Päivitä pelin numero
        self.game_number_label.config(text=f"Peli {self.current_index + 1}/{len(self.games)}")

        # Pelaajien nimet
        try:
            lines = self.games[self.current_index].splitlines()
            white = next((l.split('"')[1] for l in lines if l.startswith('[White ')), "?")
            black = next((l.split('"')[1] for l in lines if l.startswith('[Black ')), "?")
            self.white_label.config(text=f"White: {white}")
            self.black_label.config(text=f"Black: {black}")
        except Exception:
            self.white_label.config(text="White: ?")
            self.black_label.config(text="Black: ?")

        try:
            game = chess.pgn.read_game(io.StringIO(self.games[self.current_index]))
            if game:
                self.game_moves = list(game.mainline_moves())
        except Exception:
            self.game_moves = []

        self.update_move_number()
        self.draw_board()

    def draw_board(self):
        if self.board is None:
            return
        width = self.board_canvas.winfo_width()
        height = self.board_canvas.winfo_height()
        size = min(width, height)
        png_bytes = svg_board_image_bytes(self.board, size=size)
        image = Image.open(io.BytesIO(png_bytes))
        self.photo = ImageTk.PhotoImage(image)
        self.board_canvas.delete("all")
        self.board_canvas.create_image(0, 0, anchor="nw", image=self.photo)

    def on_resize(self, event):
        self.draw_board()

    def first_move(self):
        if self.board is None:
            return
        self.current_move_index = 0
        self.board.reset()
        self.update_move_number()
        self.draw_board()

    def prev_move(self):
        if self.board is None or self.current_move_index == 0:
            return
        self.current_move_index -= 1
        self.board.reset()
        for m in self.game_moves[:self.current_move_index]:
            self.board.push(m)
        self.update_move_number()
        self.draw_board()

    def next_move(self):
        if self.board is None or self.current_move_index >= len(self.game_moves):
            return
        self.board.push(self.game_moves[self.current_move_index])
        self.current_move_index += 1
        self.update_move_number()
        self.draw_board()

    def last_move(self):
        if self.board is None:
            return
        self.current_move_index = len(self.game_moves)
        self.board.reset()
        for m in self.game_moves:
            self.board.push(m)
        self.update_move_number()
        self.draw_board()

    def update_move_number(self):
        move_num = (self.current_move_index + 1) // 2
        total_moves = max(1, len(self.game_moves) // 2)
        self.move_number_label.config(text=f"Siirto {move_num}/{total_moves}")

    def on_select_list(self, event=None):
        sel = self.game_list.curselection()
        if not sel:
            return
        self.current_index = sel[0]
        self.load_selected_game()
        # Päivitä tooltip
        try:
            lines = self.games[self.current_index].splitlines()
            eco = next((l.split('"')[1] for l in lines if l.startswith('[ECO ')), "")
            opening = next((l.split('"')[1] for l in lines if l.startswith('[Opening ')), "")
            self.tooltip.text = f"ECO: {eco}\nOpening: {opening}"
        except Exception:
            self.tooltip.text = ""

    def first_game(self):
        if self.games:
            self.current_index = 0
            self.game_list.select_clear(0, tk.END)
            self.game_list.select_set(self.current_index)
            self.load_selected_game()

    def prev_game(self):
        if self.games and self.current_index > 0:
            self.current_index -= 1
            self.game_list.select_clear(0, tk.END)
            self.game_list.select_set(self.current_index)
            self.load_selected_game()

    def next_game(self):
        if self.games and self.current_index < len(self.games) - 1:
            self.current_index += 1
            self.game_list.select_clear(0, tk.END)
            self.game_list.select_set(self.current_index)
            self.load_selected_game()

    def last_game(self):
        if self.games:
            self.current_index = len(self.games) - 1
            self.game_list.select_clear(0, tk.END)
            self.game_list.select_set(self.current_index)
            self.load_selected_game()

    def search_games(self):
        query = self.search_entry.get().lower().strip()
        if not query:
            return
        for i, g in enumerate(self.games):
            if query in g.lower():
                self.current_index = i
                self.game_list.select_clear(0, tk.END)
                self.game_list.select_set(i)
                self.load_selected_game()
                return
        messagebox.showinfo("Haku", "Ei osumia.")
