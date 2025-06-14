from distutils.core import setup
import py2exe

setup(
    windows=[{"script": "main.py"}],
    options={
        "py2exe": {
            "packages": ["PyQt6", "spotipy", "lyricsgenius", "synchronouslyrics"],
            "includes": ["PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui"],
            "excludes": ["tkinter"],
            "optimize": 2,
            "dll_excludes": ["MSVCP90.dll"]
        }
    }
)
