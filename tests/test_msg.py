"""Synthetic Outlook files; no client evidence or Outlook installation."""
import hashlib
from pathlib import Path
import pytest
from emailchronicle.parser import parse_msg
from emailchronicle.store import Store


def msg_bytes(body="Hello from Outlook", html=False, date="Tue, 07 Jul 2026 10:00:00 +0000"):
    from email.message import EmailMessage
    from aspose.email_foss.msg import MapiMessage
    mail = EmailMessage()
    mail["From"] = "Alice <alice@example.test>"
    mail["To"] = "bob@example.test"
    mail["Subject"] = "Synthetic Outlook email"
    mail["Message-ID"] = "<synthetic@example.test>"
    if date:
        mail["Date"] = date
    mail.set_content(body, subtype="html" if html else "plain")
    with MapiMessage.from_email_message(mail) as message:
        transport = "From: Alice <alice@example.test>\r\nTo: bob@example.test\r\n"
        if date:
            transport += f"Date: {date}\r\n"
        message.set_property(0x007D, 0x001F, transport)
        return message.to_bytes()


def test_real_msg_parser_and_quoted_chain():
    rows = parse_msg(msg_bytes("Hello\nFrom: Bob <bob@example.test>\nDate: Tue, 07 Jul 2026 09:00:00 +0000\nSubject: Earlier\n\nEarlier body"))
    assert rows[0].sender == "Alice <alice@example.test>"
    assert rows[0].subject == "Synthetic Outlook email"
    assert rows[0].date_utc == "2026-07-07T10:00:00+00:00"
    assert rows[0].body == "Hello"
    assert rows[0].locator.startswith("MSG")
    assert rows[1].kind == "quoted"
    assert "quoted_headers_unverified" in rows[1].flags


def test_msg_html_and_uncertain_dates():
    row = parse_msg(msg_bytes("<p>Hello</p><script>hidden</script>", html=True, date="Tue, 07 Jul 2026 10:00:00 -0000"))[0]
    assert row.body == "Hello"
    assert row.date_utc is None
    assert "ambiguous_timezone" in row.flags
    assert "html_converted_to_text" in row.flags
    assert "missing_date" in parse_msg(msg_bytes(date=None))[0].flags


def test_mixed_import_preserves_msg_and_reopens(tmp_path):
    original = tmp_path / "outlook.MSG"
    data = msg_bytes()
    original.write_bytes(data)
    workspace = tmp_path / "workspace"
    store = Store(workspace)
    case = store.create_investigation("Mixed email")
    assert store.import_email(case, original) == 1
    assert store.import_email(case, original) == 0
    assert store.import_email(case, Path("samples/01-initial.eml")) == 1
    row = next(r for r in store.timeline(case) if r["locator"].startswith("MSG"))
    assert store.verified_source(row["id"]).suffix == ".msg"
    assert store.verified_source(row["id"]).read_bytes() == data
    assert original.read_bytes() == data
    assert row["sha256"] == hashlib.sha256(data).hexdigest()
    store.db.execute("PRAGMA user_version=2")
    store.close()
    store = Store(workspace)
    assert len(store.timeline(case)) == 2
    assert any(r["locator"].startswith("MSG") for r in store.timeline(case))
    store.close()


def test_invalid_msg_creates_no_evidence(tmp_path):
    path = tmp_path / "invalid.msg"
    path.write_bytes(b"not an Outlook compound file")
    store = Store(tmp_path / "workspace")
    case = store.create_investigation("Invalid")
    with pytest.raises(ValueError, match="Cannot read Outlook MSG"):
        store.import_email(case, path)
    assert not store.timeline(case)
    assert not list(store.evidence.rglob("*.msg"))
    store.close()


def test_unicode_and_non_email_items():
    from aspose.email_foss.msg import MapiMessage
    text = "Caf\u00e9 \u2014 \u4f60\u597d"
    assert parse_msg(msg_bytes(text))[0].body == text
    with MapiMessage.create(subject="Contact") as contact:
        contact.message_class = "IPM.Contact"
        with pytest.raises(ValueError, match="Only Outlook email"):
            parse_msg(contact.to_bytes())


def test_msg_source_viewer():
    from PySide6.QtWidgets import QApplication
    from emailchronicle.app import SourceViewer
    app = QApplication.instance() or QApplication([])
    data = msg_bytes()
    viewer = SourceViewer(data, "original.msg", hashlib.sha256(data).hexdigest())
    assert "Hello from Outlook" in viewer.raw_text.toPlainText()
    assert "Synthetic Outlook email" in viewer.raw_text.toPlainText()
    assert "d0 cf 11 e0" in viewer.hex_text.toPlainText()
    viewer.close()
    app.processEvents()
