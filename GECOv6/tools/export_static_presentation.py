"""Make a static PDF edition with media posters, avoiding LibreOffice video omission."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
import json, hashlib, subprocess, argparse
R=Path(__file__).resolve().parents[1]; O=R/'05_PRESENTATION'
p=argparse.ArgumentParser();p.add_argument('--soffice',default='soffice');a=p.parse_args()
source=O/'GECOv6_Research_Seminar_base.pptx'
static=O/'GECOv6_Research_Seminar_Static.pptx'
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
changes=[]
with ZipFile(source) as zi, ZipFile(static,'w',ZIP_DEFLATED) as zo:
 for n in zi.namelist():
  b=zi.read(n)
  if n.startswith('ppt/slides/slide') and n.endswith('.xml'):
   root=etree.fromstring(b)
   for t in root.findall('.//a:t',ns):
    s=t.text or ''
    if 'PLAY: TAB' in s or 'Play with Tab' in s:
     t.text=s.replace('PLAY: TAB, THEN ENTER','VIDEO IN POWERPOINT').replace('Play with Tab, then Enter.','Static poster; video in PowerPoint.');changes.append({'part':n,'before':s,'after':t.text})
   b=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
  zo.writestr(n,b)
cmd=[a.soffice,'-env:UserInstallation='+ (R/'.work/lo_ppt_static').as_uri(),'--headless','--convert-to','pdf','--outdir',str(O),str(static)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
(O/'PDF_EXPORT_LOG.txt').write_text(r.stdout+r.stderr)
if r.returncode:raise RuntimeError(r.stderr)
export=static.with_suffix('.pdf');final=O/'GECOv6_Research_Seminar.pdf';final.write_bytes(export.read_bytes());export.unlink()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(O/'STATIC_PDF_EXPORT.json').write_text(json.dumps({'source_base_sha256':sha(source),'static_pptx_sha256':sha(static),'pdf_sha256':sha(final),'slides':49,'changes':changes,'scope':'Static edition retains source-linked poster images. Media playback remains in the primary PPTX.','initial_export_issue':'LibreOffice omitted video-bearing picture regions from the primary media-embedded PPTX. Initial export withdrawn; static source used for corrected PDF.','command':cmd,'exit_code':r.returncode},indent=2))
print('Static PDF exported',len(changes),'caption changes')
