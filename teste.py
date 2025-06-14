from PyQt6.QtWidgets import QApplication, QWidget, QLabel
import sys

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teste")
        self.setGeometry(100, 100, 300, 200)
        label = QLabel("Olá, Mundo!", self)
        label.move(100, 80)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
