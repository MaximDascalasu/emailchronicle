import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json
import pytest
from PySide6.QtWidgets import QApplication
from emailchronicle.store import Store
from emailchronicle.exports import export_bundle, connections, workbook


def test_report_bundle(tmp_path):
    app=QApplication.instance() or QApplication([])
    store=Store(tmp_path/'evidence')
    case=store.create_investigation('Synthetic <report>')
    for path in Path('samples').glob('*.eml'):store.import_eml(case,path)
    rows=store.timeline(case)
    original={r['original_path']:Path(r['original_path']).read_bytes() for r in rows}
    folder=export_bundle(store,case,rows,tmp_path,{'sender':'','utc_from':''})
    assert (folder/'investigation.pdf').read_bytes().startswith(b'%PDF')
    for kind in ('timeline','gantt','communication'):
        assert (folder/f'{kind}-001.png').stat().st_size>1000
        assert (folder/f'{kind}-001.pdf').read_bytes().startswith(b'%PDF')
        ET.parse(folder/f'{kind}-001.svg')
    with ZipFile(folder/'investigation.xlsx') as z:
        for name in z.namelist():ET.fromstring(z.read(name))
        assert b'Synthetic &lt;report&gt;' in z.read('xl/worksheets/sheet1.xml')
        assert b'quoted_headers_unverified' in z.read('xl/worksheets/sheet2.xml')
    data=json.loads((folder/'export-data.json').read_text())
    assert len(data['messages'])==len(rows)
    assert data['metadata']['Undated occurrences']==2
    assert store.db.execute("SELECT count(*) FROM audit WHERE action='export_report_bundle'").fetchone()[0]==1
    assert all(Path(p).read_bytes()==content for p,content in original.items())
    with pytest.raises(ValueError):export_bundle(store,case,rows,store.directory,{})
    store.close()


def test_literal_workbook_strings_and_connection_origins(tmp_path):
    path=tmp_path/'test.xlsx'
    workbook(path,[('Literal',[['Text'],['=HYPERLINK("https://example.test")'],['A\x00B']])])
    with ZipFile(path) as z:
        xml=z.read('xl/worksheets/sheet1.xml')
        assert b'<f>' not in xml
        assert b'inlineStr' in xml
        assert b'\\u0000' in xml
    rows=[dict(sender='A <a@example.test>',recipients='b@example.test, B <b@example.test>',kind=k) for k in ('original','quoted')]
    edges=connections(rows)
    assert edges[('a@example.test','b@example.test','original')]==1
    assert edges[('a@example.test','b@example.test','quoted')]==1
    assert not connections([dict(sender=None,recipients='b@example.test',kind='original')])


def test_empty_and_long_message_exports(tmp_path):
    app=QApplication.instance() or QApplication([])
    store=Store(tmp_path/'evidence'); case=store.create_investigation('Empty')
    folder=export_bundle(store,case,[],tmp_path,{})
    assert (folder/'investigation.pdf').is_file()
    source=tmp_path/'long.eml'
    source.write_text('From: a@example.test\nTo: b@example.test\nSubject: Long\n\n'+'x'*65000)
    store.import_eml(case,source)
    folder=export_bundle(store,case,store.timeline(case),tmp_path,{})
    with ZipFile(folder/'investigation.xlsx') as z:
        assert b'body_part_3' in z.read('xl/worksheets/sheet2.xml')
    store.close()
