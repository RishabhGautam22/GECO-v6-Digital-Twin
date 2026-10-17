"""Reproducible IEEEtran PDF and editable Word paper from reviewed Markdown."""
from pathlib import Path
import copy, hashlib, json, re, subprocess, urllib.request, sys, site
sys.path=[p for p in sys.path if p!=site.getusersitepackages()]
import docx as docx_package
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'04_PAPER';WORK=OUT/'paper_work';WORK.mkdir(exist_ok=True)
PANDOC='/opt/homebrew/bin/pandoc'
TEX='/Library/TeX/texbin/pdflatex';BIBTEX='/Library/TeX/texbin/bibtex'
BIB=ROOT/'01_RESEARCH_PROTOCOL/literature_editorial/references.bib'
PRINTBIB=WORK/'paper_references.bib'
print_bib=re.sub(r'^\s*note=\{.*\},?\s*$', '', BIB.read_text(), flags=re.M)
print_bib=print_bib.replace('type1 diabetes management','type 1 diabetes management')
print_bib=print_bib.replace(r'\_', '_')
print_bib=print_bib.replace('Man, Chiara Dalla and', 'Dalla Man, Chiara and')
# Retain verified source-title capitalization, including system and dataset names.
print_bib=re.sub(r'^(\s*title=)\{(.*)\}(,?)$', r'\1{{\2}}\3', print_bib, flags=re.M)
print_bib=print_bib.replace('@misc{R09,','@misc{R09,\n  year={2008},')
for k,note in [('R10','Accessed: September 7, 2026'),('R11','Accessed: September 7, 2026'),('R12','Accessed: September 7, 2026'),('R14','Version 1'),('R15','Version 1.2.0')]:
    print_bib=print_bib.replace('@misc{'+k+',','@misc{'+k+',\n  note={'+note+'},')
PRINTBIB.write_text(print_bib)
SRC=OUT/'GECOv6_MANUSCRIPT.md'
TITLE='GECO: Separating Delivery Evidence and Stop Authority in an Insulin-Pump Simulation Study'

def run(args,input=None):
    return subprocess.run(args,input=input,text=True,capture_output=True,check=True,cwd=WORK)

def plain(x):
    if isinstance(x,list):return ''.join(plain(a) for a in x)
    if not isinstance(x,dict):return ''
    t=x.get('t');c=x.get('c')
    if t in ('Str','Code'):return c if t=='Str' else c[1]
    if t in ('Space','SoftBreak','LineBreak'):return ' '
    if t in ('Para','Plain','Strong','Emph','SmallCaps','Strikeout','Superscript','Subscript'):return plain(c)
    if t=='Header':return plain(c[2])
    if t=='Cite':return plain(c[1])
    if t=='Link':return plain(c[1])
    return ''

cache_path=WORK/'paper_cv_cache.json'
CV_CACHE=json.loads(cache_path.read_text()) if cache_path.exists() else {}
def cv(blocks,fmt):
    doc={'pandoc-api-version':API,'meta':{},'blocks':blocks}
    raw=json.dumps(doc);key=hashlib.sha256((fmt+raw).encode()).hexdigest()
    if key not in CV_CACHE:CV_CACHE[key]=run([PANDOC,'-f','json','-t',fmt],raw).stdout.strip()
    return CV_CACHE[key]

def latex_inline(inlines):return cv([{'t':'Plain','c':inlines}],'latex')

def tex_cites(node):
    if isinstance(node,list):return [tex_cites(n) for n in node]
    if isinstance(node,dict):
        if node.get('t')=='Cite':
            keys=','.join(x['citationId'] for x in node['c'][0])
            return {'t':'RawInline','c':['latex',r'\cite{'+keys+'}']}
        return {k:tex_cites(v) for k,v in node.items()}
    return node

def table_rows(b):
    c=b['c'];head=c[3][1]
    bodies=[row for body in c[4] for row in body[3]]
    return [[cell[4] for cell in row[1]] for row in head+bodies]

def latex_table(b,index):
    rows=table_rows(b);n=len(rows[0]);wide=n>=3
    captions={1:'Evidence quantities and access boundaries',2:'Internal participant forecast evaluation',3:'Full/supervised minus simple/supervised delivery differences. Mean paired research U [95\\% parameter-unit interval]; 24 units and 48 paired seed-runs per row.',4:'IIT Patna physical results pending'}
    widths={1:[.29,.64],2:[.24,.26,.43],3:[.12,.29,.26,.26],4:[.21,.27,.11,.12,.22]}[index]
    env='table*' if wide else 'table'
    h=[r'\begin{'+env+'}[!t]',r'\centering',r'\caption{'+captions[index]+'}',r'\label{tab:'+str(index)+'}',r'\small',r'\setlength{\tabcolsep}{3pt}',r'\renewcommand{\arraystretch}{1.17}',r'\begin{tabularx}{\linewidth}{'+''.join(r'>{\raggedright\arraybackslash}p{'+str(v)+r'\linewidth}' for v in widths)+'}',r'\toprule']
    for i,row in enumerate(rows):
        cells=[cv(tex_cites(cell),'latex').replace('\n\n',' ') for cell in row]
        if i==0:cells=[r'\textbf{'+v+'}' for v in cells]
        if index==4 and i>0:h.append(r'\rowcolor{pendingbg}')
        h.append(' & '.join(cells)+r' \\')
        if i==0:h.append(r'\midrule')
    h += [r'\bottomrule',r'\end{tabularx}',r'\end{'+env+'}']
    return '\n'.join(h)

FIGS=[
('03_EXPERIMENTS/filter_calibration/figures/F02_forecast_comparison',
 'Participant-level internal forecast comparison. The selected policy was chosen on tune data; each plotted point is one of 31 evaluated participants. Previously exposed test segments and upstream preprocessing limit prospective interpretation.'),
('03_EXPERIMENTS/filter_calibration/figures/F03_coverage_and_alarm_transfer',
 'Empirical test residual coverage and tune-to-test alarm burden. Near-nominal median coverage does not imply uniform participant coverage or a preserved alarm budget; 13 of 31 participants exceeded one test union alarm per day.')]
figdir=OUT/'paper_figures';figdir.mkdir(exist_ok=True)
for j,(stem,_) in enumerate(FIGS,1):
    for ext in ('pdf','png'):(figdir/('Figure'+str(j)+'.'+ext)).write_bytes((ROOT/(stem+'.'+ext)).read_bytes())
RIGCAP='IIT Patna measurement pending. Left: conceptual water/saline rig, not an as-built apparatus; components remain unselected. Right: proposed evidence chain from a defined outlet through signed native indications to a validated reconstruction with uncertainty. Commands and reports remain separate records. Balance and camera observations are not automatically ground truth. M01–M16 identify the required laboratory evidence.'

source=SRC.read_text()
# Scientific attribution refinements requested after the first content review.
# Content edits occur in reviewed Markdown, not implicitly on subsequent builds.
if source!=SRC.read_text():SRC.write_text(source)
ast=json.loads(run([PANDOC,str(SRC),'-f','markdown','-t','json']).stdout);API=ast['pandoc-api-version']
blocks=ast['blocks'];abstract=plain(blocks[3]);keywords=plain(blocks[4]).replace('Index Terms—','').strip()
# Word conversion uses Pandoc's tested OMML pathway, then python-docx style/table authoring.
word=copy.deepcopy(ast);word['meta']['title']={'t':'MetaInlines','c':[{'t':'Str','c':TITLE}]}
word['blocks']=word['blocks'][1:]
word['meta']['reference-section-title']={'t':'MetaString','c':'References'}
for b in word['blocks']:
    if b['t']=='Header':b['c'][0]-=1
    if b['t']=='Div' and 'pending' in b['c'][0][1]:
        b['c'][0][2].append(['custom-style','Pending Measurement'])

# Add two verified figures adjacent to the real-data results, before next subsection.
idx=next(i for i,b in enumerate(word['blocks']) if b['t']=='Header' and plain(b).startswith('B. Completed'))
fb=[]
for j,(stem,cap) in enumerate(FIGS,1):
    fb += [{'t':'Para','c':[{'t':'Image','c':[['fig'+str(j),[],[['width','6.25in']]],[{'t':'Str','c':cap}],[str(ROOT/(stem+'.png')),'fig:']]}]}]
    fb += [{'t':'Div','c':[['',[],[['custom-style','Caption']]],[{'t':'Para','c':[{'t':'Str','c':'Fig. '+str(j)+'. '+cap}]}]]}]
word['blocks'][idx:idx]=fb
idx=next(i for i,b in enumerate(word['blocks']) if b['t']=='Para' and plain(b).startswith('Figure 3 links'))
word['blocks'][idx+1:idx+1]=[
    {'t':'Para','c':[{'t':'Image','c':[['fig3',[],[['width','6.8in']]],[{'t':'Str','c':RIGCAP}],[str(figdir/'Figure3.png'),'fig:']]}]},
    {'t':'Div','c':[['',[],[['custom-style','Caption']]],[{'t':'Para','c':[{'t':'Str','c':'Fig. 3. '+RIGCAP}]}]]}
]

csl=WORK/'paper_ieee.csl'
if not csl.exists():
    with urllib.request.urlopen('https://raw.githubusercontent.com/citation-style-language/styles/master/ieee.csl',timeout=30) as h:csl.write_bytes(h.read())
wp=WORK/'paper_word_ast.json';wp.write_text(json.dumps(word))
raw=WORK/'paper_unstyled.docx'
run([PANDOC,str(wp),'-f','json','-t','docx','--citeproc','--csl',str(csl),'--bibliography',str(PRINTBIB),'-o',str(raw)])
doc=Document(raw)
for section in doc.sections:
    section.page_width=Inches(8.5);section.page_height=Inches(11)
    section.top_margin=Inches(.75);section.bottom_margin=Inches(.75)
    section.left_margin=Inches(.85);section.right_margin=Inches(.85)
    section.header_distance=Inches(.25);section.footer_distance=Inches(.30)
    foot=section.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');foot._p.append(field)
for style in doc.styles:
    if style.type==1:
        style.font.name='Times New Roman';style.font.color.rgb=RGBColor(0,0,0)
        style.font.size=Pt(11)
        style.paragraph_format.space_after=Pt(5)
        style.paragraph_format.line_spacing=1.05
normal=doc.styles['Normal'];normal.paragraph_format.first_line_indent=Inches(.16)
for name in ['Body Text','First Paragraph']:
    if name in doc.styles:
        doc.styles[name].paragraph_format.first_line_indent=Inches(.16)
for name,size in [('Title',20),('Heading 1',12),('Heading 2',11),('Caption',9),('Bibliography',9)]:
    if name in doc.styles:
        st=doc.styles[name];st.font.size=Pt(size)
        st.paragraph_format.first_line_indent=Inches(0)
        if name.startswith('Heading'):
            st.font.bold=True;st.paragraph_format.space_before=Pt(12);st.paragraph_format.space_after=Pt(5)
            st.paragraph_format.keep_with_next=True
doc.styles['Title'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
doc.styles['Title'].paragraph_format.space_after=Pt(12)
display_index=0
display_numbers=[None,1,2,3,4,5,None,6,7]
for p in doc.paragraphs:
    p.paragraph_format.widow_control=True
    if 'Pending Measurement' in p.style.name:
        p.paragraph_format.first_line_indent=Inches(0)
        pr=p._p.get_or_add_pPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'FFF2CC');pr.append(sh)
        bord=OxmlElement('w:pBdr')
        for side in ['top','bottom','left','right']:
            e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'6');e.set(qn('w:space'),'6');e.set(qn('w:color'),'BF9000');bord.append(e)
        pr.append(bord);p.paragraph_format.space_before=Pt(9);p.paragraph_format.space_after=Pt(9)
    if p.style.name=='Source Code':
        for run0 in p.runs:run0.font.name='Consolas';run0.font.size=Pt(8)
        p.paragraph_format.first_line_indent=Inches(0);p.paragraph_format.keep_together=True
    if p.style.name=='Caption':p.paragraph_format.keep_with_next=False
    if p._p.xpath('.//w:drawing'):p.paragraph_format.keep_with_next=True
    if p._p.xpath('./m:oMathPara'):
        number=display_numbers[display_index];display_index+=1
        for mp in p._p.xpath('./m:oMathPara'):
            maths=mp.findall(qn('m:oMath'))
            p._p.remove(mp)
            for mm in maths:p._p.append(mm)
        tab=OxmlElement('w:r');tab.append(OxmlElement('w:tab'));p._p.insert(1,tab)
        p.paragraph_format.first_line_indent=Inches(0);p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.tab_stops.add_tab_stop(Inches(3.4),WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.8),WD_TAB_ALIGNMENT.RIGHT)
        if number is not None:p.add_run('\t('+str(number)+')')
        else:p.paragraph_format.keep_with_next=True
        p.paragraph_format.space_before=Pt(7);p.paragraph_format.space_after=Pt(7)
    for r0 in p.runs:
        r0.font.color.rgb=RGBColor(0,0,0)
        if r0.font.name and r0.font.name not in ('Cambria Math','Consolas'):r0.font.name='Times New Roman'

widths={0:[1.45,5.35],1:[1.6,2.0,3.2],2:[.8,2.,2.,2.],3:[1.50,1.65,.7,.8,2.15]}
for ti,t in enumerate(doc.tables):
    title=['Table I. Evidence quantities and access boundaries','Table II. Internal participant forecast evaluation','Table III. Full minus simple supervised delivery differences','Table IV. IIT Patna physical results pending'][ti]
    cp=doc.add_paragraph(title,style='Caption');cp.paragraph_format.keep_with_next=True
    t._tbl.addprevious(cp._p)
    t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    ww=widths.get(ti,[6.8/len(t.columns)]*len(t.columns))
    for ci,col in enumerate(t.columns):col.width=Inches(ww[ci])
    props=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for side in ('top','left','bottom','right','insideH','insideV'):
        el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
    props.append(borders)
    for ri,row in enumerate(t.rows):
        if ri==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
        nosplit=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(nosplit)
        for ci,cell in enumerate(row.cells):
            cell.width=Inches(ww[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcp=cell._tc.get_or_add_tcPr();marg=OxmlElement('w:tcMar')
            for side in ('top','bottom','left','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'80');e.set(qn('w:type'),'dxa');marg.append(e)
            tcp.append(marg)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E7E6E6' if ri==0 else 'FFF2CC' if ti==3 else 'FFFFFF');tcp.append(shade)
            for p0 in cell.paragraphs:
                p0.paragraph_format.first_line_indent=Inches(0);p0.paragraph_format.space_after=Pt(2);p0.paragraph_format.space_before=Pt(2);p0.paragraph_format.line_spacing=1
                p0.paragraph_format.keep_with_next=ri < len(t.rows)-1
                for r0 in p0.runs:r0.font.name='Times New Roman';r0.font.size=Pt(9);r0.font.bold=ri==0
doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.core_properties.title=TITLE
finaldoc=OUT/'GECOv6_Manuscript.docx';doc.save(finaldoc)

# IEEEtran uses native TeX mathematics/tables and BibTeX IEEE reference order.
body=[];ti=0
for b in blocks[5:]:
    if b['t']=='Header':
        level=b['c'][0];name=re.sub(r'^(?:[IVX]+|[A-Z])\.\s*','',plain(b))
        cmd='section' if level==2 else 'subsection'
        if level==2 and not re.match(r'^[IVX]+\.',plain(b)):cmd+='*'
        if plain(b).startswith('VIII.'):body.append(r'\Needspace{15\baselineskip}')
        body.append('\\'+cmd+'{'+latex_inline([{'t':'Str','c':name}])+'}')
        if plain(b).startswith('B. Completed'):
            for j,(stem,cap) in enumerate(FIGS,1):
                width='.88' if j==1 else '.92'
                body.append(r'\begin{figure*}[!t]\centering\includegraphics[width='+width+r'\textwidth]{paper_figures/Figure'+str(j)+r'.pdf}\caption{'+latex_inline([{'t':'Str','c':cap}])+r'}\label{fig:'+str(j)+r'}\end{figure*}')
    elif b['t']=='Table':ti+=1;body.append(latex_table(b,ti))
    elif b['t']=='Div' and 'pending' in b['c'][0][1]:
        body.append(r'\begin{tcolorbox}[breakable,colback=pendingbg,colframe=pendingborder,boxrule=.5pt,arc=0pt,left=4pt,right=4pt,top=4pt,bottom=4pt]'+cv(tex_cites(b['c'][1]),'latex')+r'\end{tcolorbox}')
    elif b['t']=='CodeBlock':
        body.append(r'\begin{quote}\footnotesize\ttfamily\raggedright'+'\n'+ '\n'.join(latex_inline([{'t':'Str','c':line}])+r'\\' for line in b['c'][1].splitlines())+'\n'+r'\end{quote}')
    elif b['t']=='Para' and len(b['c'])==1 and b['c'][0]['t']=='Math':
        expression=b['c'][0]['c'][1]
        if r'\dot Q_2=' in expression and r'\tag{6}' in expression:
            first=body.pop().strip().removeprefix(r'\[').removesuffix(r'\]').strip()
            second=expression.replace(r'\tag{6}', '').replace(r'\quad', r'\qquad')
            body.append(r'\[\begin{gathered}'+first+r'\\'+second+r'\end{gathered}\tag{6}\]')
        elif any(v in expression for v in (r'\dot G=',r'\dot I=',r'E^+=')):
            tag=re.search(r'\\tag\{(\d+)\}',expression)
            expression=re.sub(r'\\tag\{\d+\}','',expression).replace(r'\quad',r'\\')
            body.append(r'\[\begin{gathered}'+expression+r'\end{gathered}'+(r'\tag{'+tag.group(1)+'}' if tag else '')+r'\]')
        else:body.append(cv(tex_cites([b]),'latex'))
    elif b['t']=='RawBlock':continue
    else:
        body.append(cv(tex_cites([b]),'latex'))
        if b['t']=='Para' and plain(b).startswith('Figure 3 links'):
            body.append(r'\begin{figure*}[!t]\centering\includegraphics[width=\textwidth]{paper_figures/Figure3.pdf}\caption{'+latex_inline([{'t':'Str','c':RIGCAP}])+r'}\label{fig:3}\end{figure*}')

preamble=r'''\documentclass[journal,10pt,letterpaper]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,graphicx,booktabs,tabularx,array}
\usepackage[table]{xcolor}
\usepackage[most]{tcolorbox}
\usepackage{microtype}
\usepackage{needspace}
\usepackage[hidelinks]{hyperref}
\usepackage{url}
\definecolor{pendingbg}{HTML}{FFF2CC}
\definecolor{pendingborder}{HTML}{BF9000}
\DeclareUnicodeCharacter{03B1}{\ensuremath{\alpha}}
\DeclareUnicodeCharacter{03B3}{\ensuremath{\gamma}}
\DeclareUnicodeCharacter{03C1}{\ensuremath{\rho}}
\DeclareUnicodeCharacter{03B5}{\ensuremath{\epsilon}}
\DeclareUnicodeCharacter{03C3}{\ensuremath{\sigma}}
\DeclareUnicodeCharacter{03BC}{\ensuremath{\mu}}
\DeclareUnicodeCharacter{0394}{\ensuremath{\Delta}}
\DeclareUnicodeCharacter{2190}{\ensuremath{\leftarrow}}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\DeclareUnicodeCharacter{0307}{\ensuremath{\dot{\phantom{x}}}}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\setlength{\emergencystretch}{1em}
\begin{document}
'''
tex=preamble+'\n\\title{'+TITLE+'}\n'+r'\author{Author information pending the research team}'+'\n'+r'\maketitle'+'\n'+r'\begin{abstract}'+latex_inline([{'t':'Str','c':abstract}])+r'\end{abstract}'+'\n'+r'\begin{IEEEkeywords}'+latex_inline([{'t':'Str','c':keywords}])+r'\end{IEEEkeywords}'+'\n'+'\n\n'.join(body)+'\n'+r'\bibliographystyle{IEEEtran}\bibliography{paper_references}'+'\n'+r'\end{document}'
tp=OUT/'GECOv6_Manuscript.tex';tp.write_text(tex)
cache_path.write_text(json.dumps(CV_CACHE))
(OUT/'paper_references.bib').write_text(print_bib)
logs=[]
texcmd=[TEX,'-interaction=nonstopmode','-halt-on-error','-output-directory',str(WORK),str(tp)]
for args in [texcmd, [BIBTEX,'GECOv6_Manuscript'],texcmd,texcmd]:
    # Bibliography is copied beside engine working directory to keep paths portable.
    (WORK/'paper_references.bib').write_text(print_bib)
    try:
        res=subprocess.run(args,text=True,capture_output=True,check=True,cwd=OUT if args[0]==TEX else WORK)
        logs.append(res.stdout+res.stderr)
    except subprocess.CalledProcessError as e:
        logs.append(e.stdout+e.stderr);(WORK/'paper_build.log').write_text('\n'.join(logs));raise
(WORK/'paper_build.log').write_text('\n'.join(logs))
pdf=OUT/'GECOv6_Manuscript.pdf';pdf.write_bytes((WORK/pdf.name).read_bytes())
receipt={'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'docx_sha256':hashlib.sha256(finaldoc.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'bibliography_sha256':hashlib.sha256(BIB.read_bytes()).hexdigest(),'figures':[str(ROOT/(s+'.pdf')) for s,_ in FIGS]+[str(figdir/'Figure3.pdf')],'python':'bundled dependency runtime','pandoc':PANDOC,'tex':TEX,'docx_equations':'Pandoc OMML, retained in python-docx','pdf_layout':'IEEEtran journal10pt two columns','docx_layout':'Single column11pt Times editable review manuscript','pending_user_instruction_overrides_generic_no_callout_style':True,'pdf_marker':'Already run by coordinator; not repeated','docx_marker':'Run exactly once before first authoring command'}
(WORK/'paper_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
