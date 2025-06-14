from cx_Freeze import setup, Executable
import sys
import os

# Configurações do executável
build_exe_options = {
    "packages": ["PyQt6", "spotipy", "lyricsgenius", "synchronouslyrics"],
    "include_files": ["icon.ico"],
    "excludes": ["tkinter"],
    "optimize": 2
}

executables = [
    Executable(
        "main.py",
        base="Win32GUI",
        icon="icon.ico",
        target_name="LetrasPIP.exe",
        shortcut_name="LetrasPIP",
        shortcut_dir="DesktopFolder"
    )
]

setup(
    name="LetrasPIP",
    version="0.1",
    description="LetrasPIP - Letras de músicas do Spotify",
    options={"build_exe": build_exe_options},
    executables=executables
)
