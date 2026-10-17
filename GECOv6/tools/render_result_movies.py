"""Native replay movies from all preselected case records; full sample coverage."""
from pathlib import Path
import subprocess,json,hashlib,sys
R=Path(__file__).resolve().parents[1];P=R/'06_RIG_AND_MEDIA/Result_Player'
O=R/'06_RIG_AND_MEDIA/videos/results';O.mkdir(parents=True,exist_ok=True)
cases=json.loads((P/'cases.json').read_text()); selected=[int(x) for x in sys.argv[1:]]
receipt=json.loads((O/'MOVIE_RECEIPT.json').read_text()) if selected else []
for i,case in enumerate(cases):
    if selected and i not in selected:continue
    receipt=[r for r in receipt if r['case']!=case['id']]
    name='GECOv6_'+case['id'];avi=R/'.work'/f'{name}.avi';mp4=O/f'{name}.mp4'
    with (O/f'{name}_render.log').open('w') as log:
        subprocess.run(['/Applications/Godot.app/Contents/MacOS/Godot','--path',str(P),'--rendering-method','gl_compatibility','--resolution','1920x1080','--fixed-fps','24','--write-movie',str(avi),'--','--movie',f'--case={i}'],check=True,stdout=log,stderr=subprocess.STDOUT)
    subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(avi),'-map','0:v','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-metadata','comment=GECOv6 frozen numerical trace. No narration; physical measurements pending.','-movflags','+faststart',str(mp4)],check=True)
    probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-show_format','-show_streams','-of','json',str(mp4)]))
    duration=float(probe['format']['duration']);assert duration>=54.9,(name,duration)
    for label,at in [('start',2.2),('fault',15.8),('end',duration-.3)]:
        subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(at),'-i',str(mp4),'-frames:v','1',str(O/f'{name}_{label}.png')],check=True)
    receipt.append({'case':case['id'],'path':str(mp4.relative_to(R)),'duration_s':duration,'frames':int(probe['streams'][0]['nb_frames']),'sha256':hashlib.sha256(mp4.read_bytes()).hexdigest(),'source_samples_per_arm':576,'has_audio':False,'status':'FROZEN_V6_SIMULATION_PLAYBACK','domain_limit':'Numerical/domain flags retained; no clinical interpretation'})
    (O/'MOVIE_RECEIPT.json').write_text(json.dumps(receipt,indent=2))
    avi.unlink()
    print(i+1,len(cases),name,duration,flush=True)
