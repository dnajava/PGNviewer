import tkinter as tk
from pgn_viewer import PGNViewer

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1100x700")
    app = PGNViewer(root)
    root.mainloop()
