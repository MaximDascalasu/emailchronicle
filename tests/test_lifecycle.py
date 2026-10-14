from PySide6.QtWidgets import QApplication
from emailchronicle.app import Window
from emailchronicle.store import Store
from emailchronicle.qt_lifecycle import dispose_windows
import shiboken6


def test_closed_window_is_disposed_before_application_shutdown(tmp_path):
    store = Store(tmp_path)
    window = Window(store)
    window.close()
    assert shiboken6.isValid(window)  # close alone does not destroy native children
    dispose_windows()
    assert not shiboken6.isValid(window)
    assert not QApplication.topLevelWidgets()
    store.close()
