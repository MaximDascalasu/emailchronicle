"""Minimal offline investigation workspace."""
import argparse
import csv
from datetime import date
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from .store import Store


class Window(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = []
        self.setWindowTitle("EmailChronicle — local evidence workspace")
        self.resize(1200, 800)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("How to use EmailChronicle", self.show_help)
        help_menu.addAction("Third-party licenses", self.open_licenses)
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)
        top = QHBoxLayout()
        self.cases = QComboBox()
        self.cases.setAccessibleName("Investigation")
        top.addWidget(QLabel("Investigation"))
        top.addWidget(self.cases, 1)
        for label, action in (("New investigation", self.new_case), ("Import EML", self.import_files),
                              ("Open source copy", self.open_source), ("Export CSV", self.export_csv)):
            button = QPushButton(label)
            button.clicked.connect(action)
            top.addWidget(button)
        layout.addLayout(top)
        filters = QHBoxLayout()
        self.sender = QLineEdit()
        self.sender.setPlaceholderText("Filter sender")
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("Search subject or content")
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("UTC from: YYYY-MM-DD")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("UTC to: YYYY-MM-DD")
        for widget, name in ((self.sender, "Sender filter"), (self.keyword, "Keyword filter"),
                              (self.date_from, "UTC start date"), (self.date_to, "UTC end date")):
            widget.setAccessibleName(name)
            filters.addWidget(widget)
            widget.textChanged.connect(self.refresh)
        layout.addLayout(filters)
        layout.addWidget(QLabel("Oldest → newest · UTC · Undated messages appear last and remain visible with date filters."))
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date (UTC)", "Sender", "Subject", "Origin", "Review flags"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_message)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setAccessibleName("Message content and provenance")
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        layout.addWidget(splitter)
        self.cases.currentIndexChanged.connect(self.refresh)
        self.reload_cases()

    def show_help(self):
        QMessageBox.information(self, "How EmailChronicle works",
            "1. Create an investigation, then import EML files.\n"
            "2. The app preserves a hashed copy of each file and extracts messages.\n"
            "3. Known dates are converted to UTC and sorted oldest first.\n"
            "4. Review quoted headers, missing dates and likely duplicates manually.\n"
            "5. Select a message to inspect its content and source; export visible rows to CSV.\n\n"
            "Original files are never modified by the importer. All evidence stays in your local workspace.\n"
            "Quoted headers are unverified text. No missing times or senders are invented.\n\n"
            f"Workspace: {self.store.directory}")

    def open_licenses(self):
        if getattr(sys, "frozen", False):
            path = Path(sys._MEIPASS) / "third-party-notices"
        else:
            root = Path(__file__).resolve().parents[2]
            path = root / "build" / "compliance" / "third-party-notices"
            if not path.is_dir():
                path = root / "THIRD_PARTY_NOTICES.md"
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Third-party licenses", f"Could not open {path}")

    def reload_cases(self, selected=None):
        self.cases.blockSignals(True)
        self.cases.clear()
        for row in self.store.investigations():
            self.cases.addItem(row["name"], row["id"])
        if selected is not None:
            self.cases.setCurrentIndex(self.cases.findData(selected))
        self.cases.blockSignals(False)
        self.refresh()

    def new_case(self):
        name, ok = QInputDialog.getText(self, "New investigation", "Investigation name:")
        if ok and name.strip():
            self.reload_cases(self.store.create_investigation(name))

    def import_files(self):
        case = self.cases.currentData()
        if case is None:
            QMessageBox.information(self, "Investigation required", "Create an investigation first.")
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Import evidence", "", "Email files (*.eml)")
        count, skipped, failures = 0, 0, []
        for path in paths:
            try:
                added = self.store.import_eml(case, path)
                count += added
                skipped += added == 0
            except Exception as exc:
                failures.append(f"{Path(path).name}: {exc}")
                with self.store.db:
                    self.store.audit(case, "import_failed", {"path": path, "error": str(exc)})
        self.refresh()
        if paths:
            QMessageBox.information(self, "Import result", f"Extracted {count} messages. Skipped {skipped} exact duplicate files.\n" + "\n".join(failures))

    def refresh(self):
        try:
            start, end = self.date_from.text().strip(), self.date_to.text().strip()
            for value in (start, end):
                if value and date.fromisoformat(value).isoformat() != value:
                    raise ValueError("Use YYYY-MM-DD")
            if start and end and start > end:
                raise ValueError("Start date must not follow end date")
        except ValueError:
            self.rows = []
            self.table.setRowCount(0)
            self.detail.clear()
            self.statusBar().showMessage("Invalid date range. Use YYYY-MM-DD, with start before end.")
            return
        self.rows = self.store.timeline(self.cases.currentData(), self.sender.text(), self.keyword.text(),
                                        self.date_from.text().strip(), self.date_to.text().strip())
        self.table.setRowCount(0)
        self.detail.clear()
        for i, row in enumerate(self.rows):
            self.table.insertRow(i)
            flags = json.loads(row["flags"])
            if row["duplicate_count"]:
                flags.append("likely_duplicate")
            for col, value in enumerate((row["date_utc"] or "Undated / review", row["sender"] or "Unknown",
                                         row["subject"] or "(no subject)", row["kind"], ", ".join(flags))):
                self.table.setItem(i, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.statusBar().showMessage(f"{len(self.rows)} messages · Local workspace: {self.store.directory}")

    def selected(self):
        index = self.table.currentRow()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def show_message(self):
        row = self.selected()
        if row:
            self.detail.setPlainText(
                f"From: {row['sender'] or '[missing]'}\nTo: {row['recipients'] or '[missing]'}\n"
                f"Subject: {row['subject'] or '[missing]'}\nOriginal date text: {row['raw_date'] or '[missing]'}\n"
                f"Origin: {row['kind']}\nLocation: {row['locator']}\n"
                f"Review flags: {row['flags']}\nLikely duplicates: {row['duplicate_count']}\n"
                f"Submitted source: {row['original_path']}\nPreserved copy: {row['stored_path']}\n"
                f"SHA-256: {row['sha256']}\n\n{row['body']}")

    def open_source(self):
        row = self.selected()
        if row:
            try:
                path = self.store.verified_source(row["id"])
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                    raise OSError("Windows could not open the EML; configure an EML viewer.")
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Open source", str(exc))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export visible timeline", "timeline.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            # Block overwriting originals, managed evidence, or application storage.
            target = Path(path).resolve()
            sources = self.store.db.execute("SELECT original_path, stored_path FROM sources").fetchall()
            protected = {Path(r[k]).resolve() for r in sources for k in ("original_path", "stored_path")}
            if target in protected or target.is_relative_to(self.store.directory):
                raise ValueError("Choose an export location outside the workspace and original evidence files.")
            fields = ["date_utc", "raw_date", "sender", "recipients", "subject", "body", "kind", "flags",
                      "duplicate_count", "locator", "original_path", "sha256"]
            with target.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                for row in self.rows:
                    # Keep spreadsheet consumers from interpreting evidence text as formulas.
                    writer.writerow([safe_cell(row[key]) for key in fields])
            with self.store.db:
                self.store.audit(self.cases.currentData(), "export_csv", {"path": str(target), "messages": len(self.rows)})
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))


def safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


def main():
    parser = argparse.ArgumentParser(description="Offline email evidence timeline")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EmailChronicle")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    store = Store(args.data_dir)
    window = Window(store)
    window.show()
    try:
        return app.exec()
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
