# main.py

import sys
from PyQt6.QtWidgets import QApplication
from lyrics_window import LyricsWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LyricsWindow()
    window.show()
    sys.exit(app.exec())

