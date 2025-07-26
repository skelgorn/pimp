# test_simple.py
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt

class SimpleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Teste Simples')
        self.setGeometry(100, 100, 300, 200)
        
        label = QLabel('Teste funcionando!', self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setGeometry(50, 80, 200, 40)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleWindow()
    window.show()
    sys.exit(app.exec()) 