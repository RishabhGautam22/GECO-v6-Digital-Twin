"""Compact vector evidence diagram beside the unmodified conceptual rig image."""
from pathlib import Path
import base64, hashlib, html, json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'04_PAPER/paper_figures';OUT.mkdir(exist_ok=True)
SRC=ROOT/'06_RIG_AND_MEDIA/stills/rig_overview.png'
W,H=540,278
c=canvas.Canvas(str(OUT/'Figure3.pdf'),pagesize=(W,H))
c.setTitle('Conceptual rig and pending delivery evidence chain')
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="540" height="278" viewBox="0 0 540 278">']
def box(x,y,w,h,fill='#FFFFFF',stroke='#ADB5BD'):
    c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke));c.setLineWidth(.7);c.rect(x,y,w,h,fill=1,stroke=1)
    svg.append(f'<rect x="{x}" y="{H-y-h}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="0.7"/>')
def text(x,y,s,size=9,bold=False,color='#17242F'):
    c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold' if bold else 'Helvetica',size);c.drawString(x,y,s)
    svg.append(f'<text x="{x}" y="{H-y}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(s)}</text>')
def arrow(x,y1,y2):
    c.setStrokeColor(HexColor('#205B69'));c.setFillColor(HexColor('#205B69'));c.setLineWidth(1.3);c.line(x,y1,x,y2+4)
    p=c.beginPath();p.moveTo(x,y2);p.lineTo(x-3,y2+5);p.lineTo(x+3,y2+5);p.close();c.drawPath(p,stroke=0,fill=1)
    svg.append(f'<path d="M{x},{H-y1} L{x},{H-y2-4} M{x},{H-y2} l-3,-5 h6 Z" fill="#205B69" stroke="#205B69" stroke-width="1.3"/>')
box(0,0,W,H,'#FFFFFF','#FFFFFF')
box(1,251,538,26,'#FFF2CC','#BF9000')
text(10,260,'IIT Patna measurement pending - conceptual apparatus, not as-built',11,True)
text(5,235,'(a) Proposed water/saline rig',10,True)
text(280,235,'(b) Required measurement chain',10,True)
# The source image is embedded whole: no geometry is altered or generated here.
c.drawImage(ImageReader(str(SRC)),2,83,width=264,height=148.5,mask='auto')
encoded=base64.b64encode(SRC.read_bytes()).decode()
svg.append(f'<image x="2" y="{H-83-148.5}" width="264" height="148.5" xlink:href="data:image/png;base64,{encoded}"/>')
text(6,72,'Syringe/drive; supported outlet; receiver/balance',8.4)
text(6,59,'Separate temperature vial; reference masses;',8.4)
text(6,47,'proposed camera/time marker and logger',8.4)
box(2,4,264,33,'#F1F3F5','#9AA6AF')
text(9,24,'Commands, acknowledgments and received reports',8.4,True)
text(9,12,'are logged separately from measured outlet delivery.',8.4)
box(280,189,257,35,'#EAF3F4','#205B69')
text(289,210,'1  Defined outlet + observation interval',9.5,True)
text(289,197,'Physical measurand; fluid and boundary specified',8.5)
arrow(405,188,170)
box(280,133,257,36,'#EAF3F4','#205B69')
text(289,155,'2  Signed native balance indication',9.5,True)
text(289,141,'Preserve signs, native clocks and instrument status',8.5)
arrow(405,132,114)
box(280,76,257,37,'#FFF2CC','#BF9000')
text(289,99,'3  Validated reconstruction - PENDING',9.5,True)
text(289,85,'Corrected outlet mass/volume with uncertainty',8.5)
text(284,60,'Requires reference-method, no-flow/low-flow,',8.5)
text(284,48,'density and synchronization validation (M01-M16).',8.5)
text(284,28,'Only then: a defensible virtual-patient input.',8.5,True)
text(284,13,'Balance or camera alone is not ground truth.',8.5)
c.save();svg.append('</svg>');(OUT/'Figure3.svg').write_text('\n'.join(svg))
(OUT/'Figure3_SOURCE.json').write_text(json.dumps({'source_image':str(SRC.relative_to(ROOT)),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'source_use':'Whole image, unchanged; conceptual visualization supplied by root.','new_graphic':'ReportLab vector rectangles, arrows and text; same editable SVG primitives.','claims':'Proposed acquisition/reconstruction chain, all physical validation pending; no actual components or measurements inferred.','script':'04_PAPER/paper_rig_figure.py'},indent=2)+'\n')
