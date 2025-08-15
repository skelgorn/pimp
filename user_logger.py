# user_logger.py
# Logger separado para ações do usuário no LetrasPIP
# Parte do plano de correção para problemas de offset e rastreio de interações.

import logging
import os

def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

log_path = os.path.join(os.getcwd(), "letraspip_usuario.log")
_ensure_dir(log_path)

user_logger = logging.getLogger("letraspip.usuario")
user_logger.setLevel(logging.DEBUG)

# Evita múltiplos handlers em execuções repetidas
if not user_logger.handlers:
    fh = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    user_logger.addHandler(fh)

def log_usuario_interacao(msg):
    # Grava uma mensagem no log separado de interações do usuário
    try:
        user_logger.info(msg)
    except Exception:
        logging.getLogger().exception("Falha ao gravar em letraspip_usuario.log")
