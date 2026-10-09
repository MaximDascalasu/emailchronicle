"""Frozen executable entry point and isolated packaging smoke check."""
import json
from pathlib import Path
import sys
import traceback
from tempfile import TemporaryDirectory

def smoke_test(report):
    from PySide6.QtWidgets import QApplication
    from emailchronicle.app import Window
    from emailchronicle.store import Store

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
            window.close()
            Path(report).write_text(json.dumps({"status": "ok", "qt": True, "sqlite": True,
                                               "eml": True, "hash_verification": True}), encoding="utf-8")
        finally:
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
