import sys
from cx_Freeze import setup, Executable

# Opções de build para o cx_Freeze
build_exe_options = {
    "packages": ["PyQt6", "spotipy", "lyricsgenius", "syncedlyrics", "re"],
    "excludes": ["tkinter"],
    "include_files": ["icon.ico"]
}

# Base para aplicações GUI no Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="LetrasPIP",
    version="0.2.1",
    description="Spotify Lyrics in Picture-in-Picture",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, icon="icon.ico", target_name="LetrasPIP.exe")]
)
