from cx_Freeze import setup, Executable

# Configurações do executável
executables = [
    Executable(
        "main.py",
        base="Win32GUI",  # Para aplicação sem console
        icon="icon.ico",
        target_name="LetrasPIP.exe"
    )
]

# Configurações do setup
setup(
    name="LetrasPIP",
    version="0.1",
    description="LetrasPIP - Letras de músicas do Spotify",
    executables=executables
)
