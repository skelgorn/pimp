# config.py

# Spotify API Credentials
SPOTIPY_CLIENT_ID = '6859bf6df1fa4b0e998a90d794aaa884'
SPOTIPY_CLIENT_SECRET = 'adf235e1983a4c9f9a358192773314f2'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8888/callback'

# Genius API Credentials
GENIUS_ACCESS_TOKEN = 'qlvL0KeFAapheVmiMPMMrRP0JV3slDCmHpt30H_trG3o_QZjUNaiLHPXL4uC9uUQ'

# Configuração de Caminhos e Cache
import os
APP_NAME = "LetrasPIP"
CACHE_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
CACHE_FILE = os.path.join(CACHE_DIR, ".spotipyoauthcache")
