"""Place the verified English manuscript in the user-supplied IEEE A4 template.

The original Strict OOXML template is retained byte-for-byte. A working copy is
normalized to equivalent Transitional namespace/measurement syntax for python-docx.
"""
from pathlib import Path
from copy import deepcopy
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import re
import runpy
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = WORK.parent / 'itt2026_output'
TEMPLATE = ROOT / 'template/conference-template-a4.docx'
NORMALIZED = ROOT / 'template/conference-template-a4-transitional.docx'
TARGET = OUT / 'ITT2026_Final_Manuscript_EN.docx'

NAMES = ['Goran Lazarov', 'Thaeer Kobbaey', 'Vishwesh Akre',
         'Waleed Al-Sit', 'Nedaa Al Barghuthi']
EMAILS = ['glazarov@hct.ac.ae', 'tkobbaey@hct.ac.ae', 'vakre@hct.ac.ae',
          'walsit@hct.ac.ae', 'nalbarghuthi@hct.ac.ae']

def normalize_template():
    pairs = {
        'wordprocessingml/main': 'wordprocessingml/2006/main',
        'drawingml/main': 'drawingml/2006/main',
        'drawingml/wordprocessingDrawing': 'drawingml/2006/wordprocessingDrawing',
        'officeDocument/relationships': 'officeDocument/2006/relationships',
        'officeDocument/math': 'officeDocument/2006/math',
        'officeDocument/customXml': 'officeDocument/2006/customXml',
        'officeDocument/docPropsVTypes': 'officeDocument/2006/docPropsVTypes',
        'officeDocument/extendedProperties': 'officeDocument/2006/extended-properties',
    }
    with ZipFile(TEMPLATE) as src, ZipFile(NORMALIZED, 'w', ZIP_DEFLATED) as dst:
        for name in src.namelist():
            data = src.read(name)
            if name.endswith(('.xml', '.rels')):
                text = data.decode('utf-8')
                for a,b in pairs.items():
                    text = text.replace('http://purl.oclc.org/ooxml/' + a,
                                        'http://schemas.openxmlformats.org/' + b)
                text = re.sub(r'="(-?\d+(?:\.\d+)?)pt"',
                              lambda m: '="' + str(round(float(m[1])*20)) + '"', text)
                text = text.replace('w:val="start"', 'w:val="left"')
                text = text.replace('w:val="end"', 'w:val="right"')
                text = text.replace('w:start=', 'w:left=').replace('w:end=', 'w:right=')
                data = text.encode('utf-8')
            dst.writestr(name, data)

def no_numbering(p):
    pr = p._p.get_or_add_pPr().get_or_add_numPr()
    pr.get_or_add_numId().val = 0

def clear_format(p):
    if p._p.pPr is not None:
        p._p.remove(p._p.pPr)
    for r in p.runs:
        if r._r.rPr is not None:
            r._r.remove(r._r.rPr)

def main():
    # Regenerate the fully edited text and scientific figure from the prior draft.
    prepared = runpy.run_path(str(ROOT / 'analysis/finalize_itt2026.py'))
    src = prepared['d']
    # Include the already-computed clean outcomes so all pilot evidence sources
    # described in the methods are represented in the final results section.
    audit_intro=next(p for p in src.paragraphs if p.text.startswith('Three attacked-utility rows'))
    audit_intro.text=audit_intro.text.replace('Table III','Table IV')
    audit_caption=next(p for p in src.paragraphs if p.text.startswith('TABLE III\n'))
    audit_caption.text=audit_caption.text.replace('TABLE III','TABLE IV',1)
    anchor=next(p for p in src.paragraphs if p.text.startswith('For unprotected GPT-4o, the exact'))
    clean_text=prepared['after'](anchor,
        'Clean-task completion provides additional context for the low joint rates (Table III). '
        'Spotlighting preserves the baseline clean completion count in both models, whereas Tool Filter '
        'and Progent have lower counts in this archive. Low attack success must therefore be read together '
        'with task capability. The clean and attacked denominators differ: 12 clean records and 24 attacked '
        'records per condition. These descriptive counts do not isolate a causal effect of the attack or '
        'a defense component, and do not evaluate later implementations of the named defenses.')
    clean_caption=prepared['after'](clean_text,
        'TABLE III\nCOMPLETED CLEAN TASKS IN THE ARCHIVAL PILOT','Caption')
    pilot=json.loads((WORK/'analysis/results/pilot_summary.json').read_text())['conditions']
    clean_rows=[]
    models=['gpt-4o-2024-08-06','google_gemini-2.5-pro']
    for label,defense in [('No added defense','none'),('Spotlighting','spotlighting'),
                          ('Tool Filter','tool_filter'),('Progent','progent')]:
        values=[]
        for model in models:
            row=next(x for x in pilot if x['model']==model and x['defense']==defense)
            values.append(str(row['clean_successes'])+'/'+str(row['clean_n']))
        clean_rows.append([label,*values])
    prepared['move_table_after'](clean_caption,
        ['Configuration','GPT-4o','Gemini 2.5 Pro'],clean_rows,[1.6,.75,1.15])
    normalize_template()
    d = Document(NORMALIZED)
    title_sect = deepcopy(d.sections[0]._sectPr)
    body_sect = deepcopy(d.sections[3]._sectPr)
    end_sect = deepcopy(d.sections[4]._sectPr)
    for sect in [title_sect, body_sect]:
        for node in list(sect):
            if node.tag in [qn('w:footerReference'), qn('w:headerReference'), qn('w:titlePg')]:
                sect.remove(node)
    # No placeholder copyright or funding statement is carried into the manuscript.
    for relid,rel in list(d.part.rels.items()):
        if rel.reltype.endswith(('/footer', '/header', '/customXml')):
            d.part.drop_rel(relid)
    body = d._element.body
    for node in list(body):
        body.remove(node)
    body.append(body_sect)
    # The template renders its default body type at 10 pt. Make that default explicit.
    default = d.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr')[0]
    for name in ['sz', 'szCs']:
        el = default.find(qn('w:'+name))
        if el is None:
            el = OxmlElement('w:'+name); default.append(el)
        el.set(qn('w:val'), '20')
    d.styles['Normal'].font.size=Pt(10)
    d.styles['equation'].font.size=Pt(10)
    d.styles['equation'].font.name='Times New Roman'
    numbering=d.part.numbering_part.element
    heading_num=numbering.xpath('./w:num[@w:numId="4"]/w:abstractNumId')[0].get(qn('w:val'))
    for level in numbering.xpath('./w:abstractNum[@w:abstractNumId="'+heading_num+'"]//w:lvl'):
        if level.get(qn('w:ilvl'))=='0':
            suffix=OxmlElement('w:suff');suffix.set(qn('w:val'),'space')
            level.insert(3,suffix)
    title = d.add_paragraph(prepared['title'], 'paper title')
    title.paragraph_format.keep_with_next = True
    author_table = d.add_table(rows=2, cols=6)
    author_table.autofit = False
    author_table.alignment = 1
    full_width = (d.sections[0].page_width - Pt(44.65)*2)
    for col in author_table.columns:
        col.width = int(full_width/6)
    for row in author_table.rows:
        for cell in row.cells:
            cell.width = int(full_width/6)
            tcPr=cell._tc.get_or_add_tcPr()
            mar=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                el=OxmlElement('w:'+side);el.set(qn('w:w'),'0');el.set(qn('w:type'),'dxa');mar.append(el)
            tcPr.append(mar)
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    cells=[author_table.cell(0,0).merge(author_table.cell(0,1)),
           author_table.cell(0,2).merge(author_table.cell(0,3)),
           author_table.cell(0,4).merge(author_table.cell(0,5)),
           author_table.cell(1,0).merge(author_table.cell(1,2)),
           author_table.cell(1,3).merge(author_table.cell(1,5))]
    for i,cell in enumerate(cells):
        p=cell.paragraphs[0];p.style=d.styles['Author']
        p.paragraph_format.keep_together=True
        if i>=3:p.paragraph_format.space_after=Pt(8)
        if i<3:
            lines=[NAMES[i], 'Computer and Information Science',
                   'Higher Colleges of Technology', 'Dubai Academic City Campus',
                   'Dubai, United Arab Emirates', EMAILS[i]]
            italic={3}
        elif i==3:
            lines=[NAMES[i], 'Computer and Information Science',
                   'Higher Colleges of Technology, UAE', 'Department of Computer Engineering',
                   'Mu’tah University, Al-Karak, Jordan', EMAILS[i]]
            italic={3,4}
        else:
            lines=[NAMES[i], 'Computer and Information Science',
                   'Higher Colleges of Technology', 'Sharjah, United Arab Emirates', EMAILS[i]]
            italic=set()
        for j,line in enumerate(lines):
            if j:p.add_run().add_break()
            r=p.add_run(line);r.font.size=Pt(9);r.italic=j in italic
    transition=d.add_paragraph()
    transition.paragraph_format.space_after=Pt(6)
    transition.paragraph_format.space_before=Pt(0)
    transition.paragraph_format.line_spacing=Pt(1)
    transition._p.get_or_add_pPr().append(title_sect)

    for node in src._element.body:
        if node.tag==qn('w:sectPr'):
            continue
        if node.tag==qn('w:p'):
            old=Paragraph(node,src._body)
            if old.style.name=='Title' or node.xpath('./w:pPr/w:sectPr'):
                continue
            if not old.text and not node.xpath('.//w:drawing|.//m:oMath'):
                continue
        new=deepcopy(node)
        for blip in new.xpath('.//a:blip'):
            rid=blip.get(qn('r:embed'))
            if rid:
                new_rid,_=d.part.get_or_add_image(BytesIO(src.part.related_parts[rid].blob))
                blip.set(qn('r:embed'),new_rid)
        body.insert(len(body)-1,new)
        if node.tag != qn('w:p'):
            continue
        p=Paragraph(new,d._body);oldstyle=old.style.name
        text=p.text
        display=bool(p._p.xpath('.//m:oMath')) and '\t(' in text
        figure=bool(p._p.xpath('.//w:drawing'))
        clear_format(p)
        if oldstyle=='Heading 1':
            if text in ['Acknowledgment','References']:
                p.style=d.styles['Heading 5']
                if text=='References':p.paragraph_format.page_break_before=True
            else:
                p.text=re.sub(r'^[IVX]+\.\s*','',text)
                p.style=d.styles['Heading 1']
        elif oldstyle=='Heading 2':
            p.text=re.sub(r'^[A-Z]\.\s*','',text)
            p.style=d.styles['Heading 2']
        elif text.startswith('Abstract—'):
            p.style=d.styles['Abstract']
        elif text.startswith('Index Terms—'):
            p.text=text.replace('Index Terms—','Keywords—',1)
            p.style=d.styles['Keywords']
        elif text.startswith('TABLE '):
            p.style=d.styles['table head'];no_numbering(p)
            p.paragraph_format.keep_with_next=True
        elif oldstyle=='Caption':
            p.style=d.styles['figure caption'];no_numbering(p)
        elif re.match(r'^\[\d+\]',text):
            p.style=d.styles['references'];no_numbering(p)
            p.paragraph_format.left_indent=Pt(12)
            p.paragraph_format.first_line_indent=Pt(-12)
            p.paragraph_format.keep_together=True
        elif display:
            p.style=d.styles['equation']
            p.paragraph_format.line_spacing=1.0
            p.paragraph_format.keep_together=True
            p.paragraph_format.keep_with_next=False
            p.paragraph_format.tab_stops.clear_all()
            p.paragraph_format.tab_stops.add_tab_stop(Pt(114),WD_TAB_ALIGNMENT.CENTER)
            p.paragraph_format.tab_stops.add_tab_stop(Pt(242.5),WD_TAB_ALIGNMENT.RIGHT)
            for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(10)
        elif figure:
            p.style=d.styles['Normal']
            p.paragraph_format.keep_with_next=True
            for el in p._p.xpath('.//wp:extent|.//a:xfrm/a:ext'):
                cx=int(el.get('cx'));cy=int(el.get('cy'))
                el.set('cx',str(int(Inches(3.365))))
                el.set('cy',str(round(cy*int(Inches(3.365))/cx)))
        else:
            p.style=d.styles['Body Text']
            if text.startswith('OpenAI ChatGPT assisted'):
                p.paragraph_format.keep_together=True
        for rfonts in p._p.xpath('.//m:r/w:rPr/w:rFonts'):
            for attr in ['ascii','hAnsi','eastAsia','cs']:
                rfonts.set(qn('w:'+attr),'Times New Roman')
        for size in p._p.xpath('.//m:r/w:rPr/w:sz'):
            size.set(qn('w:val'),'20')
        for mr in p._p.xpath('.//m:r'):
            sty=mr.find('./'+qn('m:rPr')+'/'+qn('m:sty'))
            if sty is not None and sty.get(qn('m:val'))=='p':
                normal=OxmlElement('m:nor');mr.find(qn('m:rPr')).append(normal)
                rp=mr.find(qn('w:rPr'))
                if rp is not None:
                    italic=OxmlElement('w:i');italic.set(qn('w:val'),'0');rp.append(italic)

    # Keep equation (3) clear of its right-aligned label in both Word and LO.
    eq3=next(p for p in d.paragraphs if p.style.name=='equation' and '(3)' in p.text)
    math=eq3._p.find(qn('m:oMath'))
    for el in list(math):math.remove(el)
    math.append(prepared['eqrows']([
        [prepared['mr']('L = '),prepared['mr']('max',True),prepared['mr']('(0,u − a),')],
        [prepared['mr']('H = '),prepared['mr']('min',True),prepared['mr']('(u,1 − a).')],
    ]))
    for fonts in eq3._p.xpath('.//m:r/w:rPr/w:rFonts'):
        for attr in ['ascii','hAnsi','eastAsia','cs']:fonts.set(qn('w:'+attr),'Times New Roman')
    for mr in eq3._p.xpath('.//m:r'):
        sty=mr.find('./'+qn('m:rPr')+'/'+qn('m:sty'))
        if sty is not None and sty.get(qn('m:val'))=='p':
            mr.find(qn('m:rPr')).append(OxmlElement('m:nor'))
    for p in d.paragraphs:
        if p.style.name=='equation':
            previous=p._p.getprevious()
            if previous is not None and previous.tag==qn('w:p'):
                Paragraph(previous,d._body).paragraph_format.keep_with_next=True

    # Float the explanatory paragraph ahead of the first results table to avoid
    # a large blank column when the complete table moves to the following page.
    narrowing=next(p for p in d.paragraphs if p.text.startswith('The largest narrowing occurs'))
    table1cap=next(p for p in d.paragraphs if p.text.startswith('TABLE I\n'))
    table1cap._p.addprevious(narrowing._p)

    # Use template table styles and keep each small scientific table together.
    for table in d.tables[1:]:
        table.autofit=False
        widths=[c.width for c in table.columns]
        scale=Pt(242.5)/sum(widths)
        for i,col in enumerate(table.columns):col.width=int(widths[i]*scale)
        for ri,row in enumerate(table.rows):
            for ci,cell in enumerate(row.cells):
                cell.width=int(widths[ci]*scale)
                for shade in cell._tc.xpath('./w:tcPr/w:shd'):
                    shade.set(qn('w:fill'),'FFFFFF')
                for p in cell.paragraphs:
                    text=p.text;clear_format(p)
                    p.style=d.styles['table col head' if ri==0 else 'table copy']
                    p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci==0 else WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.keep_with_next=ri < len(table.rows)-1
                    p.paragraph_format.keep_together=True
                    if len(table.rows)>10 and ri==len(table.rows)-1:
                        for r in p.runs:r.bold=True
        following=table._tbl.getnext()
        if following is not None and following.tag==qn('w:p'):
            Paragraph(following,d._body).paragraph_format.space_before=Pt(5)
    # The template's closing continuous section balances the last two columns.
    closing=d.add_paragraph()
    closing.paragraph_format.line_spacing=Pt(1)
    closing.paragraph_format.space_before=Pt(0)
    closing.paragraph_format.space_after=Pt(0)
    closing._p.get_or_add_pPr().append(body_sect)
    body.append(end_sect)
    d.core_properties.title=prepared['title']
    d.core_properties.author='; '.join(NAMES)
    d.core_properties.last_modified_by=''
    d.core_properties.subject='ITT 2026 manuscript with authors; IEEE A4 template'
    d.core_properties.comments=''
    d.save(TARGET)
    equations=[p for p in d.paragraphs if p.style.name=='equation']
    assert len(equations)==10
    assert len([p for p in d.paragraphs if p.style.name=='references'])==12
    report={
        'conference':'ITT 2026','template_binary_imported':True,
        'template_source':'User attachment: conference-template-a4.docx',
        'original_template_sha256':hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
        'normalization':'Strict OOXML namespaces and point lengths converted to equivalent Transitional syntax',
        'paper_size_points':[595.3,841.9],
        'body_margins_points':{'top':54,'bottom':72,'left':45.35,'right':45.35},
        'columns':2,'column_gap_points':18,
        'body_style':'Body Text from supplied template','body_font':'Times New Roman 10 pt',
        'title_style':'paper title from supplied template','title_font':'Times New Roman 24 pt',
        'authors':NAMES,'emails':EMAILS,'anonymous':False,
        'numbered_equations':len(equations),'fresh_model_executions':0,
        'output_docx_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
    }
    (ROOT/'template_alignment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'final':str(TARGET),'authors':NAMES,'equations':len(equations)},indent=2))

if __name__=='__main__':
    main()
