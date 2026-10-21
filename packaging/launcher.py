"""Frozen executable entry point and isolated packaging smoke check."""
import json
from pathlib import Path
import sys
import traceback
from tempfile import TemporaryDirectory
from emailchronicle.qt_lifecycle import dispose_windows

def smoke_test(report):
    from PySide6.QtWidgets import QApplication
    from emailchronicle.app import Window
    from emailchronicle.store import Store

    if getattr(sys, "frozen", False):
        import emailchronicle.app as app_module
        assert Path(app_module.__file__).resolve().is_relative_to(Path(sys._MEIPASS).resolve()), 'App loaded from outside bundled runtime'
        notices = Path(sys._MEIPASS) / "third-party-notices"
        assert (notices / "source-index.json").is_file(), "License source index missing"
        assert any("lgpl" in p.name.lower() for p in notices.rglob("*")), "LGPL license text missing"

    with TemporaryDirectory(prefix="EmailChronicle-smoke-") as directory:
        folder = Path(directory)
        original = folder / "synthetic.eml"
        original.write_bytes(b"From: smoke@example.test\nTo: recipient@example.test\n"
                             b"Subject: Packaged smoke test\nDate: Tue, 07 Jul 2026 12:00:00 +0100\n\nSynthetic content.")
        app = QApplication([])
        store = Store(folder / "data")
        try:
            investigation = store.create_investigation("Packaging smoke test")
            assert store.import_eml(investigation, original) == 1
            window = Window(store)
            window.show()
            app.processEvents()
            assert window.table.rowCount() == 1
            row = window.rows[0]
            assert row["date_utc"] == "2026-07-07T11:00:00+00:00"
            assert store.verified_source(row["id"]).read_bytes() == original.read_bytes()
            from emailchronicle.exports import export_bundle
            exports = export_bundle(store, investigation, store.timeline(investigation), folder, {})
            assert (exports / "investigation.pdf").read_bytes().startswith(b"%PDF")
            assert (exports / "investigation.xlsx").is_file()
            assert (exports / "communication-001.svg").is_file()
            from emailchronicle.search import search
            groups = [{'name': 'Content', 'terms': ['material', 'content'], 'enabled': True}]
            store.save_search_dictionary(investigation, groups)
            results = search(store.timeline(investigation), 'material', 'expanded', groups)
            assert len(results) == 1 and results[0]['search_matches'][0]['reason'] == 'synonym'
            assert store.search_dictionary(investigation)['version'] == 1
            window.keyword.setText('material')
            window.search_mode.setCurrentIndex(1)
            assert len(window.rows) == 1
            assert window.body_view.extraSelections()
            window.open_source()
            assert 'Synthetic content.' in window.source_dialog.raw_text.toPlainText()
            assert window.source_dialog.raw_text.isReadOnly()
            # Exercise the real UI CSV callback with a synthetic destination,
            # without opening an interactive file dialog during acceptance tests.
            from PySide6.QtWidgets import QFileDialog
            import csv
            original_save_dialog = QFileDialog.getSaveFileName
            csv_path = folder / 'synthetic-timeline.csv'
            try:
                QFileDialog.getSaveFileName = lambda *args: (str(csv_path), 'CSV (*.csv)')
                window.export_csv()
            finally:
                QFileDialog.getSaveFileName = original_save_dialog
            with csv_path.open(encoding='utf-8-sig', newline='') as stream:
                exported = list(csv.DictReader(stream))
            assert len(exported) == 1 and exported[0]['Subject'] == row['subject']
            # Exercise MSG using the bundled parser and an independent synthetic file.
            from email.message import EmailMessage
            from aspose.email_foss.msg import MapiMessage
            mail = EmailMessage()
            mail['From'] = 'outlook@example.test'
            mail['To'] = 'recipient@example.test'
            mail['Subject'] = 'Packaged Outlook test'
            mail['Date'] = 'Tue, 07 Jul 2026 12:30:00 +0100'
            mail.set_content('Synthetic Outlook content.')
            msg_path = folder / 'synthetic.msg'
            with MapiMessage.from_email_message(mail) as outlook:
                msg_path.write_bytes(outlook.to_bytes())
            assert store.import_email(investigation, msg_path) == 1
            assert store.import_email(investigation, msg_path) == 0
            msg_row = next(r for r in store.timeline(investigation) if r['subject'] == 'Packaged Outlook test')
            assert msg_row['date_utc'] == '2026-07-07T11:30:00+00:00'
            assert store.verified_source(msg_row['id']).read_bytes() == msg_path.read_bytes()
            from emailchronicle.app import SourceViewer
            msg_viewer = SourceViewer(msg_path.read_bytes(), msg_path.name, msg_row['sha256'], window)
            assert 'Synthetic Outlook content.' in msg_viewer.raw_text.toPlainText()
            msg_viewer.close()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, app.quit)
            assert app.exec() == 0
            window.close()
            dispose_windows()
            Path(report).write_text(json.dumps({"status": "ok", "qt": True, "sqlite": True,
                "eml": True, "msg": True, "mixed_email_import": True, "hash_verification": True, "expanded_search": True,
                "pdf_excel_graph_exports": True, "csv_ui_export": True, "event_loop_exit": True,
                "native_window_disposal": True, "built_in_source_viewer": True,
                "bundled_runtime": bool(getattr(sys, 'frozen', False))}), encoding="utf-8")
        finally:
            dispose_windows()
            store.close()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        try:
            smoke_test(sys.argv[2])
        except Exception:
            Path(sys.argv[2]).write_text(json.dumps({"status": "failed", "error": traceback.format_exc()}), encoding="utf-8")
            raise SystemExit(1)
    else:
        from emailchronicle.app import main
        raise SystemExit(main())
