def init_ui(self):
    self.setWindowIcon(QIcon(resource_path('icon.ico')))
    self.setWindowTitle('Letras PIP Spotify')
    self.setGeometry(100, 100, 600, 250)
    self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)