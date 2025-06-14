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
