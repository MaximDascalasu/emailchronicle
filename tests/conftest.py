"""Keep a single Qt application alive across the entire test process."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
import pytest
from emailchronicle.qt_lifecycle import dispose_windows

_APPLICATION = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def release_test_windows():
    yield
    # close() hides a QWidget; it does not destroy it. Signal/lambda cycles can
    # otherwise leave widgets alive until after QApplication's font teardown.
    dispose_windows()
