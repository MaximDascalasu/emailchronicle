"""Keep a single Qt application alive across the entire test process."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

_APPLICATION = QApplication.instance() or QApplication([])
