"""Shared desktop theme."""

STYLESHEET = """
            QMainWindow, QWidget { background: #1b2230; color: #e5ecf5; font-size: 13px; }
            QLabel#appTitle { font-size: 23px; font-weight: 700; }
            QLabel#quickStart { color: #8fe8bc; background: #24372f; padding: 10px 12px; border-radius: 5px; font-size: 14px; }
            QLabel#sectionTitle { font-size: 16px; font-weight: 600; }
            QLabel#filename { color: #b3c2d5; }
            QLabel#saveState { color: #69e7ad; padding: 6px 12px; background: #243d37; border-radius: 5px; }
            QLabel#helpText { color: #a9b8cc; padding: 10px 0; line-height: 1.5; }
            QPushButton { background: #2d394c; border: 1px solid #41516b; padding: 9px 12px; border-radius: 5px; }
            QPushButton:hover { background: #3a4d66; }
            QPushButton:disabled { color: #6c7a8e; border-color: #303a49; background: #242d3b; }
            QListWidget { background: #151c28; border: 1px solid #354155; border-radius: 5px; padding: 5px; }
            QListWidget::item { padding: 10px 7px; border-radius: 4px; }
            QListWidget::item:selected { background: #665630; color: #ffe29a; }
            QComboBox, QSpinBox { background: #151c28; border: 1px solid #46546a; padding: 7px; border-radius: 4px; }
            QStatusBar { color: #9aabc2; }
            QSplitter::handle { background: #354155; width: 2px; }
        """
