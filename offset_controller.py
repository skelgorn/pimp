# offset_controller.py
# Controlador central do offset do LetrasPIP
# Centraliza leitura/escrita e aplica bloqueio temporário contra sobrescrita indevida.

import threading
import traceback
import logging
from user_logger import log_usuario_interacao

class OffsetController:
    def __init__(self, initial=0):
        self._value = initial
        self._user_lock = False
        self._lock_timer = None
        self._lock = threading.Lock()

    def set_sync_offset(self, value, *, user_action=False, source=None):
        with self._lock:
            # Se bloqueado por ação do usuário e não for ação do usuário, ignora
            if self._user_lock and not user_action:
                log_usuario_interacao(f"Bloqueado: tentativa de set_sync_offset({value}) de {source} ignorada por user_lock")
                return False

            prev = self._value
            self._value = value

            # Se ação do usuário, ativa bloqueio temporário
            if user_action:
                self._user_lock = True
                if self._lock_timer:
                    self._lock_timer.cancel()
                self._lock_timer = threading.Timer(2.5, self._release_user_lock)
                self._lock_timer.daemon = True
                self._lock_timer.start()

            # Log contextual com stack curta
            stack = "".join(traceback.format_stack(limit=5))
            log_usuario_interacao(f"set_sync_offset: {prev} -> {self._value} (user_action={user_action}, source={source})\n{stack}")

            try:
                self._on_offset_changed(self._value)
            except Exception:
                logging.getLogger().exception("Erro ao notificar mudança de offset na UI")

            return True

    def _release_user_lock(self):
        with self._lock:
            self._user_lock = False
            self._lock_timer = None
            log_usuario_interacao("user_lock liberado automaticamente")

    def get_sync_offset(self):
        with self._lock:
            return self._value

    def _on_offset_changed(self, value):
        # Aqui você deve integrar a atualização visual e persistência.
        # Exemplo:
        # self.ui.update_sync_label(value)
        # cache.save_offset(value)
        pass
