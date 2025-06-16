from nuitka.main import main

main(
    [
        "--standalone",
        "--windows-disable-console",
        "--windows-icon-from-ico=icon.ico",
        "--include-package=PyQt6",
        "--include-package=spotipy",
        "--include-package=lyricsgenius",
        "--include-package=synchronouslyrics",
        "--enable-plugin=qt-plugins",
        "--windows-uac-admin",
        "--windows-uac-uiaccess",
        "main.py"
    ]
)
