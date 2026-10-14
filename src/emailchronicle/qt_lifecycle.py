"""Dispose native windows before QApplication and its font database tear down."""
import gc

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication


def dispose_windows():
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
