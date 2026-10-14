from emailchronicle.search import search
from emailchronicle.store import Store
from PySide6.QtWidgets import QApplication
from emailchronicle.app import Window
import pytest

GROUPS=[{'name':'Payment','enabled':True,'terms':['payment','remittance','settlement']},
        {'name':'Project','enabled':True,'terms':['Phoenix','PHX']}]


def row(id, body, **kwargs):
    return dict(id=id,body=body,subject='',sender='',recipients='',message_id='',**kwargs)


def test_modes_explanations_and_phrase_boundaries():
    rows=[row(1,'PHX remittance'),row(2,'Phoenix payment'),row(3,'payments remitance'),row(4,'Phoenix remitance')]
    assert [r['id'] for r in search(rows,'Phoenix payment')]==[2]
    result=search(rows,'Phoenix payment','expanded',GROUPS)
    assert [r['id'] for r in result]==[1,2]
    assert result[0]['search_matches'][0]['reason']=='synonym'
    assert [r['id'] for r in search(rows,'Phoenix remittance','approximate')]==[4]
    assert not search([row(1,'paid by bank transfer')],'"bank payment"')
    assert search([row(1,'paid by bank transfer')],'"bank transfer"')
    assert not search([row(1,'settlement')],'payment','expanded',[dict(GROUPS[0],enabled=False)])
    assert not search([row(1,'Billings')],'bill')
    with pytest.raises(ValueError):search(rows,'"unclosed')


def test_ranking_case_unicode_and_literal_regex():
    rows=[row(1,'remittance'),row(2,'payment')]
    assert [r['id'] for r in search(rows,'payment','expanded',GROUPS,True)]==[2,1]
    assert search([row(1,'ÉTUDE')],'étude')
    assert search([row(1,'a+b')],'a+b')
    assert not search([row(1,'aaab')],'a+b')
    assert not search([row(1,'cat')],'cut','approximate')
    assert search([row(1,"O'Connor")], "O'Connor")


def test_dictionary_persistence_and_case_isolation(tmp_path):
    store=Store(tmp_path);case=store.create_investigation('One');other=store.create_investigation('Two')
    store.save_search_dictionary(case,GROUPS)
    assert store.search_dictionary(case)['version']==1
    assert store.search_dictionary(other)['groups']==[]
    store.close();store=Store(tmp_path)
    assert store.search_dictionary(case)['groups']==GROUPS
    store.save_search_dictionary(case,[])
    assert store.search_dictionary(case)['version']==2
    assert store.db.execute("SELECT count(*) FROM audit WHERE action='search_dictionary_changed'").fetchone()[0]==2
    with pytest.raises(ValueError):store.save_search_dictionary(case,[dict(name='bad',terms=['one'],enabled=True)])
    store.close()


def test_ui_smart_search_and_reset(tmp_path):
    app=QApplication.instance() or QApplication([])
    store=Store(tmp_path/'data');case=store.create_investigation('Search')
    source=tmp_path/'test.eml';source.write_text('From: a@example.test\nTo: b@example.test\nSubject: PHX\n\nSend the remittance.')
    store.import_eml(case,source);store.save_search_dictionary(case,GROUPS)
    window=Window(store)
    window.keyword.setText('Phoenix payment')
    assert not window.rows
    window.search_mode.setCurrentIndex(1)
    assert len(window.rows)==1
    assert 'remittance' in window.match_info.text()
    assert window.body_view.extraSelections()
    assert window.search_settings()['dictionary']['version']==1
    window.relevance.setChecked(True)
    assert 'Relevance' in window.order_label.text()
    window.clear_filters()
    assert len(window.rows)==1 and window.search_mode.currentData()=='exact'
    assert not window.body_view.extraSelections()
    window.close();store.close()


def test_search_context_survives_export(tmp_path):
    import json
    from zipfile import ZipFile
    from emailchronicle.exports import export_bundle
    store=Store(tmp_path/'data');case=store.create_investigation('Export search')
    source=tmp_path/'test.eml';source.write_text('From: a@example.test\nTo: b@example.test\nSubject: PHX\n\nremittance')
    store.import_eml(case,source);store.save_search_dictionary(case,GROUPS)
    result=search(store.timeline(case),'Phoenix payment','expanded',GROUPS)
    folder=export_bundle(store,case,result,tmp_path,{'search':{'query':'Phoenix payment','mode':'expanded','dictionary':store.search_dictionary(case)}})
    data=json.loads((folder/'export-data.json').read_text())
    assert data['metadata']['Filters'].find('Payment')>=0
    assert 'synonym' in data['messages'][0]['search_matches']
    with ZipFile(folder/'investigation.xlsx') as z:
        assert b'search_score' in z.read('xl/worksheets/sheet2.xml')
        assert b'remittance' in z.read('xl/worksheets/sheet2.xml')
    store.close()


def test_repetitive_evidence_has_bounded_explanations_and_unicode_highlights():
    from emailchronicle.search import MAX_MATCHES_PER_TERM, MAX_HIGHLIGHTS, highlight_ranges
    body='😀 ' + 'payment ' * 200_000
    result=search([row(1,body)],'payment')
    assert len(result)==1
    assert result[0]['body']==body
    assert len(result[0]['search_matches'])==MAX_MATCHES_PER_TERM
    assert result[0]['search_matches_limited']
    spans=highlight_ranges(body,['payment'])
    assert len(spans)==MAX_HIGHLIGHTS
    assert spans[0]==(3,10)
    assert highlight_ranges('😀 payment',['payment'])==[(3,10)]
    assert highlight_ranges('nothing',['payment'])==[]
    assert not search([row(1,body)],'payment missing')
    assert search([row(1,body+'missing')],'payment missing')
