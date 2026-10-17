"""Create a native Godot3D explanatory viewer; uses source geometry and chapter text."""
from pathlib import Path
import shutil,json
R=Path(__file__).resolve().parents[1];O=R/'06_RIG_AND_MEDIA/Interactive_Rig';O.mkdir(parents=True,exist_ok=True)
shutil.copy2(R/'06_RIG_AND_MEDIA/native/GECOv6_Rig_Concept.glb',O/'rig.glb')
(O/'project.godot').write_text('''config_version=5
[application]
config/name="GECOv6 Saline Rig Explained"
run/main_scene="res://main.tscn"
[display]
window/size/viewport_width=1920
window/size/viewport_height=1080
window/size/window_width_override=1920
window/size/window_height_override=1080
window/stretch/mode="canvas_items"
[rendering]
renderer/rendering_method="gl_compatibility"
environment/defaults/default_clear_color=Color(0.025,0.055,0.085,1)
''')
(O/'main.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://rig.gd" id="1"]\n[node name="RigExplainer" type="Control"]\nlayout_mode=3\nanchors_preset=15\nanchor_right=1.0\nanchor_bottom=1.0\nscript=ExtResource("1")\n')
if not (O/'chapters.json').exists():
 (O/'chapters.json').write_text(json.dumps([{'id':'preview','title':'The saline research rig','narration':'The proposed rig separates commanded delivery, measured fluid and recorded evidence. Physical measurements from IIT Patna are still pending.','key_points':['Commanded amount','Collected mass','Independent timestamped record'],'visual_focus':'overview','measured_quantity':'Physical values will be filled after calibrated trials.','evidence_status':'CONCEPTUAL RIG','duration':12}]))
(O/'rig.gd').write_text(r'''extends Control
var chapters:Array=[]
var chapter:=0
var frame_no:=0
var local_time:=0.0
var movie:=false
var playing:=false
var qa:=false
var elapsed:=0.0
var starts:Array=[]
var total_duration:=0.0
var font:Font=ThemeDB.fallback_font
var vp:SubViewport
var camera:Camera3D
var rig:Node3D
var markers:Array=[]
var targets:Dictionary={}
var vpc:SubViewportContainer
var world:Node3D
var selector:OptionButton
var highlight:StandardMaterial3D
var normal_bg:=Color('#081421')
var ink:=Color('#F3F7FB')
var accent:=Color('#4BD7CB')
var amber:=Color('#FFD27B')
var shot:Dictionary={}
var labels_overlay:Control
var routes:Dictionary={
 'dataflow':[['C01','G01'],['G01','P01'],['P01','M03'],['T04','G01'],['T04','L01']],
 'syringe':[['S07','V01'],['V01','R01']],
 'mass':[['R01','T01'],['T01','T04'],['T04','L01']],
 'trip':[['T04','V01'],['T04','P01']],
 'recording':[['T04','L01'],['A05','A03'],['D01','L01']],
 'gateway':[['C01','G01'],['G01','P01'],['P01','G01']],
 'overview':[['G01','P01'],['S07','V01'],['V01','R01'],['T01','T04']],
 'measurement':[['T01','T04'],['T04','L01']],
 'recovery':[['L01','T04'],['T04','P01']],
 'calibration':[['D02','D01'],['D01','L01']],
 'temperature':[['D02','D01'],['D01','L01']]}
var focus_sets:Dictionary={
 'overview':['M03','S01','V01','T01','T04','G01','L01'],
 'mechanism':['M03','M04','M05','M07','M08'],
 'syringe':['S01','S03','S04','S07','F01','V01'],
 'mass':['R01','T01','T02','T03'],
 'trip':['T04','T05','T06','V01','E01'],
 'gateway':['C01','G01','P01','P02'],
 'recording':['L01','L02','A03','A05'],
 'calibration':['K20','D01','D02','D04'],
 'dataflow':['C01','G01','P01','T04','L01'],
 'measurement':['R01','T01','D01','A03'],
 'temperature':['D01','D02','D04'],
 'recovery':['T04','V01','L01'],
 'future':['K20','A03','D01','L01']}
var focus_camera:Dictionary={
 'overview':[Vector3(.40,.08,-.27),1.04],
 'mechanism':[Vector3(.185,.07,-.144),.43],
 'syringe':[Vector3(.29,.09,-.15),.48],
 'mass':[Vector3(.49,.09,-.158),.42],
 'trip':[Vector3(.445,.07,-.27),.62],
 'gateway':[Vector3(.22,.045,-.315),.54],
 'recording':[Vector3(.67,.085,-.26),.59],
 'calibration':[Vector3(.42,.06,-.448),.85],
 'dataflow':[Vector3(.37,.06,-.27),.95],
 'measurement':[Vector3(.55,.07,-.23),.72],
 'temperature':[Vector3(.70,.05,-.43),.36],
 'recovery':[Vector3(.44,.06,-.24),.68],
 'future':[Vector3(.4,.07,-.27),1.02]}
func _ready():
 chapters=JSON.parse_string(FileAccess.get_file_as_string('res://chapters.json'))
 for c in chapters:starts.append(total_duration);total_duration+=float(c.duration)
 movie='--movie' in OS.get_cmdline_user_args()
 qa='--qa' in OS.get_cmdline_user_args()
 vpc=SubViewportContainer.new();vpc.position=Vector2(48,193);vpc.size=Vector2(1220,686);vpc.stretch=true;add_child(vpc)
 vp=SubViewport.new();vp.size=Vector2i(1220,686);vp.render_target_update_mode=SubViewport.UPDATE_ALWAYS;vp.own_world_3d=true;vp.msaa_3d=Viewport.MSAA_4X;vpc.add_child(vp)
 world=Node3D.new();vp.add_child(world)
 var env=WorldEnvironment.new();var e=Environment.new();e.background_mode=Environment.BG_COLOR;e.background_color=Color('#E8EEF2');e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;e.ambient_light_color=Color.WHITE;e.ambient_light_energy=.20;e.tonemap_mode=Environment.TONE_MAPPER_FILMIC;env.environment=e;world.add_child(env)
 for pos in [Vector3(1,1.4,.8),Vector3(-.2,.9,-.8)]:
  var li=DirectionalLight3D.new();li.light_energy=.16;li.shadow_enabled=true;world.add_child(li);li.position=pos;li.look_at(Vector3(.4,0,-.27),Vector3.UP)
 rig=load('res://rig.glb').instantiate();world.add_child(rig)
 collect_targets(rig)
 var palette={'white':'#9DAFB9','black':'#142634','aluminum':'#657986','dark':'#1D3446','blue':'#156282','glass':'#668993','orange':'#B85C26','fluid':'#177565','board':'#245846'}
 for mesh in meshes(rig):
  for idx in range(mesh.mesh.get_surface_count()):
   var original=mesh.get_active_material(idx)
   if original is StandardMaterial3D:
    var replacement=StandardMaterial3D.new();replacement.albedo_color=Color(palette.get(original.resource_name,'#8A9BA5'));replacement.roughness=.65;replacement.metallic=.12
    mesh.set_surface_override_material(idx,replacement)
 camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.005;camera.far=20;world.add_child(camera);camera.current=true
 highlight=StandardMaterial3D.new();highlight.albedo_color=Color('#13A995');highlight.metallic=.25;highlight.roughness=.45
 for i in range(6):
  var mesh=MeshInstance3D.new();var sphere=SphereMesh.new();sphere.radius=.005;sphere.height=.010;mesh.mesh=sphere;var mat=StandardMaterial3D.new();mat.albedo_color=Color('#EF7D39');mat.emission_enabled=true;mat.emission=Color('#D96F2F');mat.emission_energy_multiplier=1.3;mesh.material_override=mat;world.add_child(mesh);markers.append(mesh)
 selector=OptionButton.new();selector.position=Vector2(1297,187);selector.size=Vector2(570,50)
 for c in chapters:selector.add_item(c.title)
 selector.item_selected.connect(func(i):chapter=i;elapsed=starts[i];update_shot();queue_redraw());add_child(selector)
 var play=Button.new();play.text='Play / pause   Space';play.position=Vector2(1297,880);play.size=Vector2(260,46);play.pressed.connect(func():playing=not playing);add_child(play)
 if movie or qa:selector.visible=false;play.visible=false
 update_shot()
 labels_overlay=load('res://labels_overlay.gd').new();labels_overlay.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(labels_overlay)
 if '--self-test' in OS.get_cmdline_user_args():
  assert(targets.has('G01'));assert(targets.has('T01'));assert(targets.has('D02'));assert(chapters.size()>0)
  print('PASS rig import, component lookup, chapters and cameras; ',targets.size(),' objects')
  get_tree().quit()
func collect_targets(n:Node):
 if n is Node3D:
  var id=String(n.name).split('_')[0].split(' ')[0]
  if not targets.has(id):targets[id]=n
 for child in n.get_children():collect_targets(child)
func meshes(n:Node)->Array:
 var result:Array=[]
 if n is MeshInstance3D:result.append(n)
 for child in n.get_children():result.append_array(meshes(child))
 return result
func update_shot():
 var focus=chapters[chapter].get('visual_focus','overview')
 shot={'focus':focus,'ids':focus_sets.get(focus,focus_sets.overview),'camera':focus_camera.get(focus,focus_camera.overview)}
 for mesh in meshes(rig):mesh.material_override=null
 if focus!='overview' and focus!='dataflow':
  for id in shot.ids:
   if targets.has(id):
    for mesh in meshes(targets[id]):mesh.material_override=highlight
 if selector:selector.select(chapter)
func _unhandled_key_input(event):
 if event is InputEventKey and event.pressed:
  if event.keycode==KEY_SPACE:playing=not playing
  elif event.keycode==KEY_RIGHT:chapter=min(chapter+1,chapters.size()-1);elapsed=starts[chapter];update_shot()
  elif event.keycode==KEY_LEFT:chapter=max(0,chapter-1);elapsed=starts[chapter];update_shot()
  elif event.keycode==KEY_HOME:chapter=0;elapsed=0;update_shot()
  queue_redraw()
func _process(delta):
 if chapters.is_empty():return
 if qa:
  if frame_no>=chapters.size()*2:get_tree().quit();return
  chapter=int(frame_no/2);elapsed=starts[chapter]+2;frame_no+=1;update_shot()
 elif movie:
  elapsed=frame_no/24.0;frame_no+=1
  if elapsed>=total_duration+.125:get_tree().quit();return
 elif playing:elapsed=min(total_duration-.001,elapsed+delta)
 var idx=chapter
 while idx+1<chapters.size() and elapsed>=starts[idx+1]:idx+=1
 if idx!=chapter:chapter=idx;update_shot()
 local_time=elapsed-starts[chapter]
 var target:Vector3=shot.camera[0];var scale:float=shot.camera[1]
 var angle=.67+.08*sin(local_time*.21)
 var offset=Vector3(cos(angle),.83,sin(angle))*.78
 camera.position=target+offset;camera.size=scale*.74;camera.look_at(target,Vector3.UP)
 var route:Array=routes.get(shot.focus,routes.overview)
 for j in range(markers.size()):
  markers[j].visible=j<route.size()
  if j<route.size() and targets.has(route[j][0]) and targets.has(route[j][1]):
   var a:Vector3=targets[route[j][0]].global_position+Vector3(0,.025,0)
   var b:Vector3=targets[route[j][1]].global_position+Vector3(0,.025,0)
   var route_color=Color('#48AEE8')
   if route[j][0] in ['S07','V01']:route_color=Color('#35C6AA')
   elif shot.focus in ['trip','recovery'] or route[j][0]=='A05':route_color=Color('#EF7D39')
   markers[j].material_override.albedo_color=route_color
   markers[j].material_override.emission=route_color
   markers[j].position=a.lerp(b,fmod(local_time*.30+j*.18,1.0))
 if labels_overlay:labels_overlay.queue_redraw()
 queue_redraw()
func text_at(pos:Vector2,value:String,size:int,color:Color=Color.WHITE):draw_string(font,pos,value,HORIZONTAL_ALIGNMENT_LEFT,-1,size,color)
func wrapped(pos:Vector2,value:String,size:int,width:float,color:Color=Color.WHITE,line_h:float=40):
 var words=value.split(' ');var line='';var y=pos.y
 for word in words:
  var test=line+(' ' if line!='' else '')+word
  if font.get_string_size(test,HORIZONTAL_ALIGNMENT_LEFT,-1,size).x>width and line!='':text_at(Vector2(pos.x,y),line,size,color);y+=line_h;line=word
  else:line=test
 if line!='':text_at(Vector2(pos.x,y),line,size,color);y+=line_h
 return y
func _draw():
 if chapters.is_empty():return
 var c=chapters[chapter]
 draw_rect(Rect2(0,0,1920,1080),normal_bg)
 text_at(Vector2(48,70),'GECOv6   The saline rig explained',49,ink)
 text_at(Vector2(50,113),'CONCEPTUAL ASSEMBLY   /   IIT PATNA PHYSICAL MEASUREMENTS PENDING',23,amber)
 text_at(Vector2(50,160),'%02d / %02d   %s' % [chapter+1,chapters.size(),c.title],31,accent)
 var y=285.0
 for point in c.key_points:
  text_at(Vector2(1300,y),'•',31,accent)
  y=wrapped(Vector2(1332,y),point,30,510,ink,40)+30
 y=max(600,y+12)
 text_at(Vector2(1300,y),'MEASUREMENT OR CHECK',20,amber)
 wrapped(Vector2(1300,y+40),c.get('measured_quantity',''),26,550,ink,36)
 # Native viewport sits above the background; labels are projected into its coordinate system in its own overlay.
 text_at(Vector2(50,926),'Animated tokens illustrate connections. They do not encode a measured flow rate.',24,Color('#C0CFDC'))
 text_at(Vector2(50,963),'Blue: data    Orange: trip / timing    Teal: fluid path to the receiver',22,Color('#C0CFDC'))
 draw_rect(Rect2(50,1005,1816,4),Color('#263C4E'));draw_rect(Rect2(50,1005,1816*elapsed/max(1,total_duration),4),accent)
 text_at(Vector2(50,1048),'Independent evidence requires calibrated instruments and synchronized physical trials.',22,ink)
 text_at(Vector2(1690,1048),'%02d:%02d' % [int(elapsed)/60,int(elapsed)%60],23,amber)
''')
print(O)

(O/'labels_overlay.gd').write_text(r'''extends Control
var font:Font=ThemeDB.fallback_font
var labels={
 'overview':[['S01','Syringe'],['T01','Balance'],['T04','Local monitor']],
 'dataflow':[['C01','CGM replay'],['G01','Gateway'],['T04','Local monitor']],
 'gateway':[['C01','CGM replay'],['G01','Gateway'],['P01','Pump endpoint']],
 'mechanism':[['M03','Motor'],['M05','Lead screw'],['M08','Moving pusher']],
 'syringe':[['S01','Syringe barrel'],['S07','Outlet connector'],['V01','Proposed stop']],
 'mass':[['R01','Receiver'],['T01','Balance'],['T04','Local monitor']],
 'calibration':[['K20','Reference-mass tray'],['D02','Temperature probe'],['D01','Acquisition module']],
 'temperature':[['D01','Acquisition module'],['D02','Temperature probe'],['D04','Separate sample vial']],
 'measurement':[['R01','Defined receiver'],['T01','Signed indication'],['A03','Reference camera']],
 'recording':[['A03','Reference camera'],['A05','Time marker'],['L01','Acquisition computer']],
 'trip':[['T04','Monitor'],['V01','Proposed fluid stop'],['E01','Power electronics']],
 'recovery':[['T04','Monitor'],['V01','Proposed fluid stop'],['L01','Operator record']],
 'future':[['K20','Reference masses'],['D01','Temperature record'],['L01','Acquisition record']]}
func _draw():
 var host=get_parent()
 if not host.camera or host.shot.is_empty():return
 var items=labels.get(host.shot.focus,labels.overview)
 for i in range(items.size()):
  var id=items[i][0]
  if not host.targets.has(id):continue
  var target=host.camera.unproject_position(host.targets[id].global_position)+host.vpc.position
  if not Rect2(48,193,1220,686).has_point(target):continue
  var pos=Vector2(67+i*398,213)
  draw_line(pos+Vector2(160,43),target,Color('#223C50'),1.4,true)
  draw_circle(target,5,Color('#EF9A4C'))
  draw_rect(Rect2(pos,Vector2(363,43)),Color('#FFFFFF'))
  draw_string(font,pos+Vector2(10,29),id+'  '+items[i][1],HORIZONTAL_ALIGNMENT_LEFT,348,21,Color('#163747'))
''')
