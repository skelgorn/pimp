from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    'packages': ['PyQt6', 'spotipy', 'lyricsgenius', 'syncedlyrics', 'func_timeout'],
    'include_files': ['icon.ico'],
    'excludes': ['tkinter'],
}

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('main.py', base=base)
]

setup(
    name='LetrasPIP',
    version='1.0.1',
    description='LetrasPIP - Letras sincronizadas do Spotify',
    options={'build_exe': build_exe_options},
    executables=executables
)
