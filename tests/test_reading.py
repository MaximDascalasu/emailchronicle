from emailchronicle.reading import clean_message, chronological, readable_date


def test_cleaning_preserves_substance_and_removes_footer():
    body = "Hello Alex,\n\nPlease approve the revised date.\n\nKind regards,\nJamie\nDirector | 12345\nOn Tuesday someone wrote:\nOld message"
    assert clean_message(body) == "Hello Alex,\n\nPlease approve the revised date."
    assert clean_message("Thanks for confirming.\n\nNext meeting is Friday.") == "Thanks for confirming.\n\nNext meeting is Friday."
    assert clean_message("> Confirmed.\n> -- \n> Name") == "Confirmed."


def test_order_and_readable_dates():
    rows = [dict(id=3,date_utc=None),dict(id=2,date_utc="2026-01-02T12:30:00+00:00"),dict(id=1,date_utc="2026-01-01T12:30:00+00:00")]
    assert [r['id'] for r in chronological(rows)] == [1,2,3]
    assert readable_date(rows[1]['date_utc']) == "02 Jan 2026 · 12:30:00 UTC"


def test_csv_uses_clean_text_and_chronology(tmp_path, monkeypatch):
    import csv
    from PySide6.QtWidgets import QApplication
    from emailchronicle.app import Window
    from emailchronicle.store import Store
    from emailchronicle import app as module
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path/'data')
    case = store.create_investigation('Reading')
    for day in (2, 1):
        path = tmp_path/f'{day}.eml'
        path.write_text(f'From: a@example.test\nTo: b@example.test\nDate: Thu, {day:02d} Jan 2025 12:00:00 +0000\nSubject: Update\n\nDecision {day}.\n\nKind regards,\nName\nPhone: 123')
        store.import_eml(case,path)
    window = Window(store)
    window.rows.reverse()
    target = tmp_path/'clean.csv'
    monkeypatch.setattr(module.QFileDialog,'getSaveFileName',lambda *args: (str(target),''))
    window.export_csv()
    with target.open(encoding='utf-8-sig',newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert [r['Message'] for r in rows] == ['Decision 1.', 'Decision 2.']
    window.resize(1366,768)
    window.show()
    app.processEvents()
    assert window.body_view.height() >= 250
    assert window.table.height() >= 450
    window.close()
    store.close()


def test_outlook_dates_reply_messages_and_signatures(tmp_path):
    from emailchronicle.parser import parse_eml, recorded_datetime
    from emailchronicle.reading import message_date
    from emailchronicle.store import Store
    data = ("From: Jamie Example <jamie@example.test>\nTo: alex@example.test\nDate: Tue, 18 Nov 2025 17:34:13 +0000\nSubject: Update\nContent-Type: text/plain; charset=utf-8\n\n"
        "Hi Alex,\n\nPlease review the revised plan.\n\nBest,\nJamie Example\nProgram Manager\n5440 Example Blvd\n919-677-4244\n[signature_123]\n\n"
        "From: Alex Example <alex@example.test<mailto:alex@example.test>>\nSent: Thursday, November 13, 2025 at 10:24\u202fAM\nTo: Jamie Example <jamie@example.test>\nSubject: Update\n\n"
        "The plan is ready: https://example.test/plan\n\nAlex Example\nPartner & Chief Strategist\nc: 217.502.1309\n\n"
        "On Thu, Nov 6, 2025 at 7:30\u202fAM Jamie Example <jamie@example.test> wrote:\nEarlier question.\n\nBest,\nJamie Example\nProgram Manager") .encode('utf-8')
    messages = parse_eml(data)
    assert len(messages)==3
    assert clean_message(messages[0].body,messages[0].sender)=='Hi Alex,\n\nPlease review the revised plan.'
    assert clean_message(messages[1].body,messages[1].sender)=='The plan is ready: https://example.test/plan'
    assert clean_message(messages[2].body,messages[2].sender)=='Earlier question.'
    assert message_date(vars(messages[1]))=='13 Nov 2025 · 10:24 · timezone not recorded'
    assert messages[1].date_utc is None
    assert 'unparsed_date' not in messages[1].flags
    store = Store(tmp_path/'evidence'); case=store.create_investigation('Legacy upgrade')
    source=tmp_path/'chain.eml';source.write_bytes(data);store.import_eml(case,source)
    original_ids=[r['id'] for r in store.timeline(case)]
    with store.db:
        store.db.execute("UPDATE messages SET body='Old extraction' WHERE kind='original'")
        store.db.execute('PRAGMA user_version=2')
    store.close();store=Store(tmp_path/'evidence')
    rows=store.timeline(case)
    assert [r['id'] for r in rows]==original_ids
    assert [message_date(r) for r in rows][0].startswith('06 Nov 2025')
    assert all(r['body']!='Old extraction' for r in rows)
    assert source.read_bytes()==data
    store.close()


def test_reader_defaults_to_clean_message_and_resets_scroll(tmp_path):
    from PySide6.QtWidgets import QApplication
    from emailchronicle.store import Store
    from emailchronicle.app import Window
    app=QApplication.instance() or QApplication([])
    store=Store(tmp_path/'data');case=store.create_investigation('Reader')
    for day in (13,14):
        source=tmp_path/f'{day}.eml'
        source.write_text(f'From: Jamie Example <jamie@example.test>\nTo: alex@example.test\nDate: Thu, {day} Nov 2025 10:24:13 +0000\nSubject: Update\n\n' + 'Decision text.\n\n'*40 + 'Best,\nJamie Example\n[signature_123]')
        store.import_eml(case,source)
    window=Window(store);window.resize(1366,768);window.show();app.processEvents()
    window.body_view.verticalScrollBar().setValue(99999)
    window.tabs.setCurrentIndex(2)
    window.table.selectRow(1);app.processEvents()
    assert window.tabs.currentIndex()==0
    assert window.body_view.verticalScrollBar().value()==0
    assert '10:24:13 UTC' in window.message_meta.text()
    assert '[signature_' not in window.body_view.toPlainText()
    assert '[signature_' not in window.detail.toPlainText()
    assert '[signature_' in window.original_text.toPlainText()
    assert window.body_view.height()>=250
    window.close();store.close()
