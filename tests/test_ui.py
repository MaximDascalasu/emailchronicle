import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from emailchronicle.app import Window, safe_cell
from emailchronicle.store import Store
from test_core import SAMPLES


def test_window_timeline_selection_and_filter(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path)
    case = store.create_investigation("UI case")
    store.import_eml(case, SAMPLES / "03-followup.eml")
    window = Window(store)
    window.show()
    app.processEvents()
    assert window.table.rowCount() == 2
    window.table.selectRow(0)
    app.processEvents()
    assert "SHA-256:" in window.detail.toPlainText()
    assert "quoted_headers_unverified" in window.detail.toPlainText()
    window.sender.setText("Alice")
    assert window.table.rowCount() == 1
    window.date_from.setText("invalid")
    assert window.table.rowCount() == 0
    assert "Invalid date range" in window.statusBar().currentMessage()
    window.close()
    store.close()


def test_csv_formula_escaping():
    assert safe_cell("=CMD()") == "'=CMD()"
    assert safe_cell("  +formula") == "'  +formula"
    assert safe_cell("normal") == "normal"


def test_help_and_license_access(tmp_path, monkeypatch):
    from emailchronicle import app as module
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path)
    window = Window(store)
    messages, opened = [], []
    monkeypatch.setattr(module.QMessageBox, "information", lambda *args: messages.append(args[-1]))
    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    window.show_help()
    window.open_licenses()
    assert "No missing times or senders are invented" in messages[0]
    assert opened and module.Path(opened[0]).exists()
    window.close()
    store.close()


def test_import_export_and_source_ui(tmp_path, monkeypatch):
    import csv
    from emailchronicle import app as module
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path / "data")
    store.create_investigation("Actions")
    window = Window(store)
    monkeypatch.setattr(module.QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(module.QFileDialog, "getOpenFileNames", lambda *args: ([str(SAMPLES / "01-initial.eml")], ""))
    window.import_files()
    assert len(window.rows) == 1
    output = tmp_path / "timeline.csv"
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    window.export_csv()
    with output.open(encoding="utf-8-sig", newline="") as stream:
        exported = list(csv.DictReader(stream))
    assert exported[0]["date_utc"] == "2026-07-07T10:30:00+00:00"
    assert exported[0]["sha256"] == window.rows[0]["sha256"]
    opened = []
    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    window.table.selectRow(0)
    window.open_source()
    assert opened[0].replace("\\", "/") == window.rows[0]["stored_path"].replace("\\", "/")
    warnings = []
    monkeypatch.setattr(module.QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    source = SAMPLES / "01-initial.eml"
    original = source.read_bytes()
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", lambda *args: (str(source), ""))
    window.export_csv()
    assert warnings and source.read_bytes() == original
    window.close()
    store.close()
