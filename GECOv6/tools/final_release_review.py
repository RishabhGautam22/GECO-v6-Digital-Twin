"""Record final root production review; no numerical or scientific result edits."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from PIL import Image
import hashlib,json,shutil,datetime
R=Path(__file__).resolve().parents[1]; Q=R/'08_REVIEW_AND_QA'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rec(p):return {'file':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
media=json.loads((R/'05_PRESENTATION/EMBEDDED_MEDIA.json').read_text())
pp=R/'05_PRESENTATION/GECOv6_Research_Seminar.pptx';assert sha(pp)==media['pptx_sha256']
write(Q/'presentation/NATIVE_POWERPOINT_PLAYBACK_QA.json',{
 'date':'2026-09-07','review':'Interactive native Microsoft PowerPoint on macOS; observed accessibility state and screenshots',
 'artifact':rec(pp),'opened_without_repair_prompt':True,'closed_without_save':True,'file_hash_unchanged':True,
 'activation':'Slide Show; type slide number then Return; Tab then Return activates embedded movie',
 'native_full_screen_video_start_verified_slides':[24,25,26,27,29,30,31,32,33],
 'additional_motion_observed':{'24':'sample 1 to 442','25':'sample 1 to 406','26':'sample 1 to 259','27':'sample 1 to final sample 576 / 48 hours','29':'main tour advanced from chapter 1 to chapter 2 / 00:34'},
 'native_chart_slide_8':'Four bars and labels 25.8,22.6,17.8,17.6; units, categories and participant-weighting caption visible; native chart exposed in accessibility tree',
 'scope_limit':'Playback startup/full-screen and selected progression observed. Not a continuous complete viewing or perceptual audio assessment of every movie. Full MP4 decode and separate endpoint/visual checks have their own receipts. Mouse activation is not claimed; documented keyboard path was tested.',
 'status':'PASS'})
shutil.copy2(R/'.work/presentation/finalization.json',Q/'presentation/BASE_PRESENTATION_FINALIZATION.json')
stills=[]
for p in sorted((R/'06_RIG_AND_MEDIA/stills').glob('*.png')):
 with Image.open(p) as im: dims=list(im.size)
 stills.append({**rec(p),'dimensions':dims,'individual_visual_review':'PASS'})
frames=[{**rec(p),'individual_visual_review':'PASS'} for p in sorted((Q/'media').glob('rig_C*.png'))]
assert len(stills)==10 and len(frames)==14
write(Q/'media/FINAL_RIG_PRODUCTION_QA.json',{
 'date':'2026-09-07','reviewer':'Root production review','stills':stills,'chapter_frames':frames,
 'native_sources':[rec(p) for p in sorted((R/'06_RIG_AND_MEDIA/native').glob('GECOv6_Rig_Concept.*')) if p.suffix in ['.blend','.glb','.scad']],
 'interactive_checks_previously_observed':{'rig':'PASS:70 component IDs and14 chapters','results':'PASS:10 cases,2 arms,576 source samples each'},
 'source_correction':'OpenSCAD foot positions aligned with the already corrected 800 by 540 mm Blender/GLB base: far foot centers 770 and 510 mm. Source generator and SCAD corrected; rendered geometry was already correct.',
 'visual_findings':'No unresolved blocking issue in ten individual stills and fourteen rig chapter frames. Clear concept/pending labels. Separate reference camera, time marker, environmental reference vial, receiver, load cell and local stop path.',
 'provenance':'Native 3D rendering; macOS Aman synthetic narration disclosed; animated path markers illustrate links rather than measured flow.',
 'scope_limit':'Illustrative geometry and explanatory media; not verified as-built hardware, fabrication certification, physical fluid measurement or clinical validation. No perceptual full-audio listening claim.',
 'status':'PASS'})
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,a):
  for k,v in a:
   if (k in ['href','src'] or (t=='option' and k=='value')) and v:self.links.append(v)
index=R/'00_START_HERE/OPEN_PACKAGE.html';html=Links();html.feed(index.read_text());checked=[]
for u in html.links:
 s=urlsplit(u)
 if s.scheme or s.netloc:raise AssertionError(('unexpected external URL',u))
 if not s.path:continue
 p=(index.parent/unquote(s.path)).resolve();assert p.exists(),u
 checked.append({'link':u,'resolved':p.relative_to(R).as_posix()})
write(Q/'PACKAGE_INDEX_LINK_QA.json',{'index':rec(index),'checked_links':checked,'count':len(checked),'external_requests':0,'status':'PASS'})
print(json.dumps({'native_movies':9,'stills':len(stills),'chapter_frames':len(frames),'index_links':len(checked),'status':'PASS'}))
