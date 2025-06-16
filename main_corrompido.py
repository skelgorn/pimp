import sys
import os
import re
import time
import logging

# Configura o logging para um arquivo na pasta do usuário
log_file = os.path.join(os.path.expanduser('~'), 'letras_pip_debug.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='w'  # 'w' para sobrescrever o log a cada execução
)

logging.info('--- SCRIPT INICIADO ---')
from PyQt6.QtWidgets import QApplication, QWidget
import sys

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teste")
        self.setGeometry(100, 100, 300, 200)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

