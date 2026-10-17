"""Native conceptual GECOv6 rig and educational camera views. No measured dimensions."""
from pathlib import Path
import json,sys,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
exec(compile((ROOT/'tools/rig_foundation.py').read_text(),str(ROOT/'tools/rig_foundation.py'),'exec'))
# Expanded presentation base; all part dimensions remain illustrative.
base=bpy.data.objects['B01 Bench base'];base.location=(.400,.270,0);base.dimensions=(.800,.540,.012)
parts[0]['position_mm']=[400,270,0];parts[0]['dimensions_mm']=[800,540,12]
scad[0]='translate([400,270,0]) cube([base_length,base_width,12],center=true);'
# Place the four feet near the expanded base corners.
for obj in bpy.data.objects:
 if obj.name.startswith('B02_'):
  obj.location.x=.770 if obj.location.x>.5 else .030
  obj.location.y=.510 if obj.location.y>.3 else .030
  pid=obj.get('component_id')
  for rec in parts:
   if rec['id']==pid:rec['position_mm']=[round(v*1000,6) for v in obj.location]
scad=[line.replace('translate([570,','translate([770,').replace(', 390, -12])',', 510, -12])') if 'cylinder(r=14,h=12' in line else line for line in scad]
# Clear the syringe bore through each saddle so the illustration does not imply solid interference.
for xx in (215,284):
 obj=bpy.data.objects['M10_'+str(xx)+' Cradle top saddle']
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.01575,depth=.020,location=(xx/1000,.144,.102),rotation=(0,math.pi/2,0))
 cutter=bpy.context.object;mod=obj.modifiers.new('Illustrative bore clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
 for j,line in enumerate(scad):
  if f'translate([{xx}, 144, 92])' in line:scad[j]='difference(){'+line+f'translate([{xx},144,102]) rotate([0,90,0]) cylinder(r=15.75,h=20,center=true,$fn=64);'+'}'
for j,line in enumerate(scad):
 if 'translate([488, 158, 103])' in line:scad[j]='difference(){'+line+'translate([488,158,109]) cylinder(r=32,h=90,center=true,$fn=64);}'

# Separate acquisition computer and recording screen.
cube('L01','Independent acquisition computer',[673,283,23],[162,112,12],'dark',3)
cube('L02','Acquisition screen frame',[673,332,92],[164,9,116],'dark',3)
cube('L03','Acquisition screen',[673,326,92],[148,1,99],'blue',1)
for j in range(4):cube('L04_'+str(j),'Keyboard row',[672,265+j*10,30],[126,5,1.3],'aluminum',.3)
# Sensor probe and separate temperature acquisition module.
cube('D01','Temperature acquisition module',[677,424,24],[84,50,25],'white',2)
cyl('D02','Temperature probe in separate sample',[725,450,47],1.6,47,'aluminum')
cyl('D04','Separate temperature sample vial',[725,450,31],12,48,'glass')
cyl('D05','Temperature sample fluid',[725,450,23],10,25,'blue')
path('D03','Probe lead',[[725,450,71],[735,427,79],[699,405,61],[677,413,35]],1.0,'dark')
# Reference camera records the receiver and timing marker; it is not an automatically calibrated flowmeter.
cyl('A01','Reference camera post',[699,125,63],5,114,'dark')
cube('A02','Reference camera foot',[699,125,10],[66,66,8],'dark',2)
cube('A03','Reference camera body',[691,125,139],[59,44,38],'dark',3)
cyl('A04','Reference camera lens',[655,125,139],13,31,'black','X')
cube('A05','Clock marker module',[559,160,91],[20,23,18],'orange',2)
cyl('A06','Clock marker light',[548,156,103],5,5,'orange')
# Calibration artifacts show the required method, with no fabricated class or certification.
for j,(rad,h) in enumerate([(11,25),(14,30),(17,35)]):
 cyl('K0'+str(j+1),'Reference mass selection pending',[80+45*j,456,12+h/2],rad,h,'aluminum')
 cyl('K1'+str(j+1),'Reference mass handle',[80+45*j,456,12+h],rad*.45,8,'aluminum')
cube('K20','Reference mass tray',[127,456,10],[148,61,7],'dark',2)
# Explicit replay/data links and recording link; colored by role, not protocol assurance.
path('W07','Replay data connection',[[61,347,31],[76,330,54],[168,361,58],[242,341,50]],1.5,'blue')
path('W08','Measurement record connection',[[523,311,50],[552,357,40],[598,347,29],[626,303,31]],1.5,'blue')
path('W09','Timestamp reference connection',[[683,266,31],[612,220,25],[559,178,88]],1.3,'orange')
# Neutral floor enlarged to keep the entire expanded rig inside all views.
cube('B03','Render backdrop',[400,270,-34],[10000,10000,20],'white',0)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,size in [('Key',[.15,-.25,1.05],25,1.1),('Fill',[1.0,.2,.8],12,.9),('Back',[.3,1.0,.9],18,.8)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=energy;ld.shape='DISK';ld.size=size;lo=bpy.data.objects.new(name,ld);bpy.context.collection.objects.link(lo);lo.location=loc;aim(lo,[.4,.27,.05])
cd=bpy.data.cameras.new('Educational camera');cam=bpy.data.objects.new('Educational camera',cd);bpy.context.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';cd.lens=45
# A native ground label preserves conceptual status in portable scene views.
for text,loc,size in [('GECOv6  CONCEPTUAL SALINE RIG',[385,30,10],10),('IIT PATNA MEASUREMENTS PENDING',[400,515,10],8)]:label(text,loc,size)
views=[
 ('rig_overview',[1.15,-.84,.93],[.4,.27,.065],1.09),
 ('pump_mechanism',[.47,-.35,.40],[.192,.144,.076],.39),
 ('syringe_path',[.49,-.32,.45],[.275,.145,.10],.40),
 ('mass_measurement',[.87,-.17,.48],[.492,.155,.092],.36),
 ('local_trip',[.79,.73,.51],[.44,.251,.063],.52),
 ('gateway_endpoint',[.32,.64,.57],[.215,.319,.045],.41),
 ('reference_recording',[1.09,.01,.65],[.667,.257,.080],.51),
 ('calibration_temperature',[.68,.94,.72],[.389,.438,.045],.72),
 ('rig_overhead',[.4,.27,1.6],[.4,.27,0],.92),
 ('rig_exploded',[1.14,-.86,1.02],[.4,.27,.10],1.15),
]
s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';s.view_settings.exposure=-1.2
s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True;s.cycles.device='CPU';backend='CPU'
pref=bpy.context.preferences.addons['cycles'].preferences
for candidate in ['METAL','OPTIX','CUDA','HIP','ONEAPI']:
 try:
  pref.compute_device_type=candidate;pref.get_devices()
  if any(d.type==candidate for d in pref.devices):
   for d in pref.devices:d.use=d.type==candidate
   backend=candidate;s.cycles.device='GPU';break
 except (TypeError,ValueError,RuntimeError):pass
print('Render backend',backend,flush=True)
cam.location=views[0][1];aim(cam,views[0][2]);cd.ortho_scale=views[0][3]
s.render.resolution_x=2560;s.render.resolution_y=1440
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'COMPONENTS.json').write_text(json.dumps({'version':'GECOv6-concept','units':'mm','status':'CONCEPTUAL_IIT_PATNA_MEASUREMENTS_PENDING','not_measured':['component dimensions','syringe bore and pitch','balance uncertainty','fluid density','flow cessation','clock alignment','recovery behavior'],'parts':parts},indent=2))
(OUT/'GECOv6_Rig_Concept.scad').write_text('// Concept only, millimetres. Component-specific tolerances and fit pending.\nbase_length=800;base_width=540;\n'+'\n'.join(x for x in scad if '10000' not in x))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GECOv6_Rig_Concept.blend'))
# GLB carries geometry only; lighting/camera will be supplied by the interactive viewer.
export_objects=[o for o in bpy.data.objects if o.type in ('MESH','CURVE','FONT') and not o.name.startswith('B03')]
bpy.ops.object.select_all(action='DESELECT')
for o in export_objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GECOv6_Rig_Concept.glb'),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
render_list=views[:1] if '--preview' in sys.argv else views
receipt=[]
for name,loc,target,scale in render_list:
 cam.location=loc;aim(cam,target);cd.ortho_scale=scale
 moved=[]
 if name=='rig_exploded':
  for o in bpy.data.objects:
   if o.name.startswith(('S0','M08','M09','M10')):moved.append(o);o.location.z+=.075
 s.render.resolution_x=1280 if '--preview' in sys.argv else (3840 if name=='rig_overview' else 2560);s.render.resolution_y=int(s.render.resolution_x*9/16);s.render.filepath=str(R/(name+'.png'));bpy.ops.render.render(write_still=True)
 for o in moved:o.location.z-=.075
 receipt.append({'view':name,'file':str(Path(s.render.filepath).relative_to(ROOT)),'camera_m':loc,'target_m':target,'orthographic_scale_m':scale,'resolution':[s.render.resolution_x,s.render.resolution_y]})
(OUT/'RENDER_RECEIPT.json').write_text(json.dumps({'blender':bpy.app.version_string,'engine':'Cycles','samples':40,'denoising':True,'backend':backend,'views':receipt,'status':'Conceptual geometry, not physical evidence'},indent=2))
