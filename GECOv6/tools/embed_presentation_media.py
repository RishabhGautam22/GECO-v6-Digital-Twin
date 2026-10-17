"""Add native, embedded PowerPoint movies to Artifact Tool poster objects.

All media bytes remain identical to the separately delivered MP4 assets. This
OOXML packaging step does not rasterize slide content or change chart workbooks.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import json,hashlib,posixpath
R=Path(__file__).resolve().parents[1];O=R/'05_PRESENTATION'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
REL='http://schemas.openxmlformats.org/package/2006/relationships';CT='http://schemas.openxmlformats.org/package/2006/content-types'
def q(x):a,b=x.split(':');return '{'+NS[a]+'}'+b
spec=json.loads((O/'SLIDE_CONTENT.json').read_text())
with ZipFile(O/'GECOv6_Research_Seminar_base.pptx') as z:parts={n:z.read(n) for n in z.namelist()}
cts=E.fromstring(parts['[Content_Types].xml'])
if not any(x.get('Extension')=='mp4' for x in cts):E.SubElement(cts,'{'+CT+'}Default',Extension='mp4',ContentType='video/mp4')
receipts=[]
for n,d in enumerate(spec,1):
    if d['kind']!='video':continue
    name=f'ppt/slides/slide{n}.xml';relname=f'ppt/slides/_rels/slide{n}.xml.rels';root=E.fromstring(parts[name]);rels=E.fromstring(parts[relname])
    candidates=root.findall('.//p:pic',NS) # Manifest video slide has exactly one poster picture; Artifact Tool does not retain supplied alt metadata.
    assert len(candidates)==1,(n,len(candidates));pic=candidates[0];nv=pic.find('p:nvPicPr',NS);cpr=nv.find('p:cNvPr',NS);sid=cpr.get('id');cpr.set('name',Path(d['video']).name)
    E.SubElement(cpr,q('a:hlinkClick'),{'action':'ppaction://media'})
    nvpr=nv.find('p:nvPr',NS)
    if nvpr is None:nvpr=E.SubElement(nv,q('p:nvPr'))
    video_id='rIdGECOvideo';media_id='rIdGECOmedia';media_name=f'geco-{n:02d}.mp4';target='../media/'+media_name
    E.SubElement(nvpr,q('a:videoFile'),{q('r:link'):video_id})
    extlst=E.SubElement(nvpr,q('p:extLst'));ext=E.SubElement(extlst,q('p:ext'),uri='{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}')
    E.SubElement(ext,q('p14:media'),{q('r:embed'):media_id})
    E.SubElement(rels,'{'+REL+'}Relationship',Id=video_id,Type=NS['r']+'/video',Target=target)
    E.SubElement(rels,'{'+REL+'}Relationship',Id=media_id,Type='http://schemas.microsoft.com/office/2007/relationships/media',Target=target)
    # Media timing node: click-to-play, with no automatic slide advance.
    timing=E.SubElement(root,q('p:timing'));tn=E.SubElement(timing,q('p:tnLst'));par=E.SubElement(tn,q('p:par'));ctn=E.SubElement(par,q('p:cTn'),id='1',dur='indefinite',restart='never',nodeType='tmRoot');cl=E.SubElement(ctn,q('p:childTnLst'));video=E.SubElement(cl,q('p:video'),fullScrn='1');cm=E.SubElement(video,q('p:cMediaNode'),vol='80000');c=E.SubElement(cm,q('p:cTn'),id='2',fill='hold',display='0');sc=E.SubElement(c,q('p:stCondLst'));E.SubElement(sc,q('p:cond'),delay='indefinite');tgt=E.SubElement(cm,q('p:tgtEl'));E.SubElement(tgt,q('p:spTgt'),spid=sid)
    payload=(R/d['video']).read_bytes();parts['ppt/media/'+media_name]=payload
    parts[name]=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True);parts[relname]=E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
    receipts.append({'slide':n,'file':d['video'],'package_part':'ppt/media/'+media_name,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),'evidence':d['evidence']})
parts['[Content_Types].xml']=E.tostring(cts,xml_declaration=True,encoding='UTF-8',standalone=True)
out=O/'GECOv6_Research_Seminar.pptx'
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=6) as z:
    for name,body in parts.items():z.writestr(name,body)
with ZipFile(out) as z:
    assert z.testzip() is None
    for r in receipts:assert hashlib.sha256(z.read(r['package_part'])).hexdigest()==r['sha256']
(O/'EMBEDDED_MEDIA.json').write_text(json.dumps({'pptx_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'slide_count':len(spec),'embedded_movies':len(receipts),'all_media_internal':True,'package_and_hash_check':'PASS','native_application_playback':'Separate receipt required','media':receipts},indent=2))
print(out, len(receipts),'embedded movies')
