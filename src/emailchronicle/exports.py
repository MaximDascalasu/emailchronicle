"""Local report exports. No network access or evidence modifications."""
from collections import Counter
from datetime import datetime, timezone
from email.utils import getaddresses
from html import escape
import hashlib
import json
from pathlib import Path
import re
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPdfWriter, QPageSize, QTextDocument

FIELDS = ['id', 'date_utc', 'raw_date', 'sender', 'recipients', 'subject', 'body', 'kind',
          'message_id', 'flags', 'duplicate_count', 'locator', 'original_path', 'stored_path', 'sha256']
NOTICE = ('UTC throughout. Undated messages are not assigned times. Quoted headers are unverified claims. '
          'Duplicate hints are not merged; graph counts include all exported occurrences. '
          'File hashes establish byte integrity, not author identity. Audit records are locally editable.')


def connections(rows):
    """Keep original and quoted assertions separate; never invent missing parties."""
    edges = Counter()
    for row in rows:
        senders = [addr.lower() for _, addr in getaddresses([row['sender'] or '']) if '@' in addr]
        recipients = {addr.lower() for _, addr in getaddresses([row['recipients'] or '']) if '@' in addr}
        for sender in set(senders):
            for recipient in recipients:
                edges[(sender, recipient, row['kind'])] += 1
    return edges


def text_xml(value):
    # OOXML strings cannot contain XML 1.0 forbidden controls; retain readable escapes.
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', lambda m: f'\\u{ord(m[0]):04x}', str(value or '')))


def workbook(path, sheets):
    """Small standards-based XLSX writer with explicit literal strings, never formulas."""
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    def col(n):
        result = ''
        while n:
            n, r = divmod(n - 1, 26); result = chr(65 + r) + result
        return result
    with ZipFile(path, 'x', ZIP_DEFLATED) as z:
        overrides = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1))
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+overrides+'</Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml', f'<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF172942"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i, (_, data) in enumerate(sheets, 1):
            if len(data) > 1048576: raise ValueError('Excel row limit exceeded')
            cells=[]
            for r, values in enumerate(data, 1):
                cells.append(f'<row r="{r}"'+(' ht="28" customHeight="1"' if r==1 else '')+'>')
                for c, value in enumerate(values,1):
                    if len(str(value or '')) > 32767: raise ValueError('Excel cell exceeds 32767 characters')
                    cells.append(f'<c r="{col(c)}{r}" s="{1 if r==1 else 0}" t="inlineStr"><is><t xml:space="preserve">{text_xml(value)}</t></is></c>')
                cells.append('</row>')
            last=f'{col(max(map(len,data)))}{len(data)}'
            z.writestr(f'xl/worksheets/sheet{i}.xml', f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="24" customWidth="1"/><col min="2" max="{max(map(len,data))}" width="36" customWidth="1"/></cols><sheetData>'+''.join(cells)+f'</sheetData><autoFilter ref="A1:{last}"/></worksheet>')


class Graphic:
    """Draw PNG and SVG from identical primitives without additional Qt modules."""
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.image=QImage(width,height,QImage.Format.Format_ARGB32); self.image.fill(QColor('white'))
        self.p=QPainter(self.image); self.p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>']
    def text(self,x,y,text,size=13,color='#24334b'):
        self.p.setPen(QColor(color)); self.p.setFont(QFont('Segoe UI',size))
        self.p.drawText(int(x),int(y),str(text))
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Segoe UI, sans-serif" font-size="{size*1.33}" fill="{color}">{escape(str(text))}</text>')
    def line(self,x1,y1,x2,y2,color='#cbd6e5',dashed=False):
        pen=self.p.pen(); pen.setColor(QColor(color)); pen.setWidth(2); pen.setStyle(Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine); self.p.setPen(pen)
        self.p.drawLine(int(x1),int(y1),int(x2),int(y2))
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="6 4"' if dashed else '')+'/>')
    def dot(self,x,y,color='#225ec4'):
        self.p.setPen(QColor(color)); self.p.setBrush(QColor(color)); self.p.drawEllipse(QRectF(x-5,y-5,10,10))
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')
    def save(self,base):
        self.p.end()
        if not self.image.save(str(base)+'.png'): raise OSError('PNG export failed')
        Path(str(base)+'.svg').write_text(''.join(self.svg)+'</svg>',encoding='utf-8')
        writer = QPdfWriter(str(base)+'.pdf')
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(144)
        writer.setTitle(base.name)
        document = QTextDocument()
        document.setHtml(f'<img src="{base.with_suffix(".png").as_uri()}" width="650"/>')
        document.print_(writer)


def charts(folder, rows):
    # Paginate for readability: every occurrence appears, without an unbounded canvas.
    pages=[]
    dated=[r for r in rows if r['date_utc']]
    for kind in ('timeline','gantt'):
        groups=[dated[i:i+24] for i in range(0,len(dated),24)] or [[]]
        for page, group in enumerate(groups,1):
            g=Graphic(1400, max(400,220+len(group)*45))
            g.text(35,40, 'Chronological timeline' if kind=='timeline' else 'Gantt-style event lanes',22)
            g.text(35,73,'UTC · one marker per message · amber = quoted assertion; blue = original metadata')
            g.text(35,98,f'{len(rows)-len(dated)} undated occurrences excluded from time axis; see workbook/report.')
            g.text(35,122,'Emails are point events; no task duration is inferred. IDs link to the workbook and report.')
            times=[datetime.fromisoformat(r['date_utc']).timestamp() for r in dated]
            lo,hi=(min(times),max(times)) if times else (0,1)
            for i,r in enumerate(group):
                y=185+i*45; color='#aa6800' if r['kind']=='quoted' else '#225ec4'
                if kind=='timeline':
                    g.line(55,y-20,55,y+20); g.dot(55,y,color)
                    g.text(80,y,f"#{r['id']}  {r['date_utc']}  {(r['sender'] or '[missing sender]')[:60]}",12)
                    g.text(80,y+20,(r['subject'] or '[no subject]')[:110],11)
                else:
                    g.text(35,y,f"#{r['id']} {(r['subject'] or '[no subject]')[:33]}",11)
                    g.line(470,y,1320,y,'#edf1f6')
                    x=470+850*(datetime.fromisoformat(r['date_utc']).timestamp()-lo)/(hi-lo or 1)
                    g.dot(x,y,color)
                    g.text(470,y+19,r['date_utc'],9)
            if not group: g.text(35,185,'No dated messages in this export.')
            base=folder/f'{kind}-{page:03d}';g.save(base);pages.append(base.with_suffix('.png'))
    edges=connections(rows)
    # Edge-list graph avoids unreadable hairballs and preserves direction and count.
    items=sorted(edges.items())
    for page,start in enumerate(range(0,max(len(items),1),18),1):
        group=items[start:start+18];g=Graphic(1400,max(380,180+len(group)*52))
        g.text(35,40,'Communication graph · directed relationships',22)
        g.text(35,73,'Original metadata: blue solid · quoted assertions: amber dashed · counts include duplicate occurrences')
        g.text(35,98,'Email addresses are parsed assertions, not verified identities. Missing/unparseable parties have no edge.')
        for i,((sender,recipient,kind),count) in enumerate(group):
            y=155+i*52;color='#aa6800' if kind=='quoted' else '#225ec4'
            g.text(35,y,sender[:43],11);g.dot(450,y-5,color);g.line(450,y-5,860,y-5,color,kind=='quoted')
            g.line(850,y-12,860,y-5,color);g.line(850,y+2,860,y-5,color)
            g.text(590,y-13,f'{count} · {kind}',10,color);g.dot(880,y-5,color);g.text(900,y,recipient[:43],11)
        if not group:g.text(35,155,'No parseable sender-to-recipient connections.')
        base=folder/f'communication-{page:03d}';g.save(base);pages.append(base.with_suffix('.png'))
    return pages


def pdf_report(path, rows, metadata, images):
    writer=QPdfWriter(str(path));writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4));writer.setResolution(144)
    writer.setTitle('EmailChronicle investigation report')
    writer.setCreator('EmailChronicle · local export')
    doc=QTextDocument();doc.setDefaultFont(QFont('Segoe UI',10))
    html=['<h1>EmailChronicle</h1><h2>Investigation report</h2>']
    html += [f'<p><b>{escape(k)}</b>: {escape(str(v))}</p>' for k,v in metadata.items()]
    html += [f'<p>{NOTICE}</p><p>No conclusions or manual review completion are inferred.</p>']
    for image in images:
        html.append(f'<h2 style="page-break-before:always">{escape(image.stem)}</h2><img src="{image.as_uri()}" width="650"/>')
    html.append('<h2 style="page-break-before:always">Messages · dated oldest first, undated last</h2>')
    for r in rows:
        html.append(f"<h3>Message #{r['id']} · {escape(r['subject'] or '[no subject]')}</h3>")
        for key in FIELDS:
            if key=='body':continue
            html.append(f'<p><b>{key}</b>: {escape(str(r[key] if r[key] is not None else "[missing]"))}</p>')
        # Paragraphs preserve long messages and avoid non-breaking preformatted overflow.
        html.append('<h4>Extracted content</h4>')
        for line in r['body'].splitlines():
            # Break long tokens so unbroken URLs/hash-like strings cannot overflow the page.
            line=re.sub(r'\S{85,}',lambda m:'\u200b'.join(m[0][i:i+80] for i in range(0,len(m[0]),80)),line)
            html.append('<p>'+escape(line or ' ')+'</p>')
    doc.setHtml(''.join(html));doc.print_(writer)
    if not path.is_file() or path.stat().st_size==0:raise OSError('PDF export failed')


def export_bundle(store, investigation, rows, parent, filters):
    """A new output directory prevents overwriting evidence or prior exports."""
    parent=Path(parent).resolve()
    if parent.is_relative_to(store.directory):raise ValueError('Choose an export folder outside the evidence workspace')
    case=store.db.execute('SELECT name FROM investigations WHERE id=?',(investigation,)).fetchone()
    if not case:raise ValueError('Select an investigation first')
    rows=[dict(r) for r in rows]
    allowed={r['id'] for r in store.timeline(investigation)}
    if any(r['id'] not in allowed for r in rows):raise ValueError('Messages do not belong to selected investigation')
    folder=parent/('EmailChronicle-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    folder.mkdir() # exclusive creation, never reuses an existing export
    metadata={'Investigation':case['name'],'Generated UTC':datetime.now(timezone.utc).isoformat(),
              'Scope':'Current visible timeline; evidence inventory limited to included messages; audit covers whole investigation',
              'Filters':json.dumps(filters,ensure_ascii=False),'Exported occurrences':len(rows),'Undated occurrences':sum(not r['date_utc'] for r in rows)}
    try:
        source_ids={r['source_id'] for r in rows}
        sources=[dict(r) for r in store.db.execute('SELECT * FROM sources WHERE investigation_id=?',(investigation,)) if r['id'] in source_ids]
        audit=[dict(r) for r in store.db.execute('SELECT * FROM audit WHERE investigation_id=? ORDER BY id',(investigation,))]
        # Evidence text can exceed Excel cell limits: split body into numbered parts, never drop text.
        parts=max([1]+[(len(r['body'])+29999)//30000 for r in rows])
        fields=[f for f in FIELDS if f!='body']+[f'body_part_{i+1}' for i in range(parts)]
        messages=[fields]+[[r[f] if r[f] is not None else '' for f in FIELDS if f!='body']+[r['body'][i*30000:(i+1)*30000] for i in range(parts)] for r in rows]
        # Other oversized values fail explicitly rather than silently truncating evidence.
        source_fields=['id','original_path','stored_path','sha256','size_bytes','imported_at']
        edge_rows=[['Sender','Recipient','Origin','Occurrence count']]+[list(edge)+[n] for edge,n in sorted(connections(rows).items())]
        sheets=[('Overview',[['Property','Value']]+[[k,str(v)] for k,v in metadata.items()]+[['Method',NOTICE]]),
                ('Messages',messages),('Evidence',[source_fields]+[[s[f] for f in source_fields] for s in sources]),
                ('Review',[['Message ID','Flags','Duplicate hints']]+[[r['id'],r['flags'],r['duplicate_count']] for r in rows if json.loads(r['flags']) or r['duplicate_count']]),
                ('Communications',edge_rows),('Audit',[['UTC','Action','Details']]+[[a['time_utc'],a['action'],a['details']] for a in audit])]
        workbook(folder/'investigation.xlsx',sheets)
        images=charts(folder,rows)
        pdf_report(folder/'investigation.pdf',rows,metadata,images)
        (folder/'export-data.json').write_text(json.dumps({'metadata':metadata,'messages':rows,'sources':sources,'audit':audit},ensure_ascii=False,indent=2),encoding='utf-8')
        (folder/'README.txt').write_text(NOTICE+'\nGraphs are paginated and include all dated occurrences. Gantt-style lanes show points, not durations.\nComplete graph labels and counts are in the Communications worksheet.\n'+json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
        (folder/'SHA256SUMS.json').write_text(json.dumps(checksums,indent=2),encoding='utf-8')
        with store.db:store.audit(investigation,'export_report_bundle',{'path':str(folder),'message_ids':[r['id'] for r in rows],'filters':filters,'checksums':checksums})
        return folder
    except Exception:
        # Preserve partial output for diagnosis but never label it completed.
        (folder/'EXPORT_FAILED.txt').write_text('Export did not complete. Do not rely on these partial files.',encoding='utf-8')
        raise
