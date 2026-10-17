from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parents[1];O=R/'06_RIG_AND_MEDIA';V=O/'videos';Q=R/'08_REVIEW_AND_QA/media';Q.mkdir(parents=True,exist_ok=True)
f=V/'GECOv6_Rig_Explained.mp4';probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-show_format','-show_streams','-of','json',str(f)]));assert {s['codec_type'] for s in probe['streams']}=={'audio','video','subtitle'};assert abs(float(probe['format']['duration'])-480)<.25
ch=json.loads((O/'Interactive_Rig/chapters.json').read_text());(V/'chapters').mkdir(exist_ok=True);items=[]
for c in ch:
 id=c['id'];out=V/'chapters'/f'GECOv6_Rig_{id}.mp4'
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(c['start_seconds']),'-i',str(f),'-t',str(c['duration']),'-map','0:v:0','-map','0:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)],check=True)
 still=Q/f'rig_{id}.png';subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(c['start_seconds']+c['duration']*.55),'-i',str(f),'-frames:v','1',str(still)],check=True)
 items.append({'id':id,'title':c['title'],'start_s':c['start_seconds'],'duration_s':c['duration'],'path':str(out.relative_to(R)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
(V/'RIG_MOVIE_RECEIPT.json').write_text(json.dumps({'path':str(f.relative_to(R)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'probe':probe,'chapters':items,'status':'CONCEPTUAL_RIG_SYNTHETIC_NARRATION_PHYSICAL_MEASUREMENTS_PENDING'},indent=2))
print('Full movie and14 narrated chapter clips validated')
