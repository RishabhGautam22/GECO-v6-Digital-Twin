"""GECOv5 conceptual assembly. Editable native geometry; no as-built claim.
Run with Blender --background --factory-startup --disable-autoexec --python this_file.
All source dimensions below are illustrative millimetres, shared with the SCAD export.
"""
from pathlib import Path
import bpy,math,json,sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'06_RIG_AND_MEDIA/native';R=ROOT/'06_RIG_AND_MEDIA/stills';R.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.length_unit='MILLIMETERS';s.unit_settings.scale_length=1
s.render.engine='BLENDER_EEVEE';s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.fps=24
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.40,.46,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.2
s.view_settings.view_transform='AgX';s.view_settings.exposure=-.8
colors={'aluminum':(.59,.65,.69,1),'white':(.83,.87,.87,1),'dark':(.035,.06,.09,1),'board':(.025,.21,.14,1),'fluid':(.015,.36,.28,1),'blue':(.025,.42,.60,1),'orange':(.93,.25,.045,1),'glass':(.49,.70,.78,1),'black':(.025,.03,.04,1),'red':(.55,.035,.035,1)}
M={}
for k,c in colors.items():
 m=bpy.data.materials.new(k);m.diffuse_color=c;m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.36;p.inputs['Metallic'].default_value=.7 if k=='aluminum' else .05
 if k=='glass':p.inputs['Transmission Weight'].default_value=.5;p.inputs['Roughness'].default_value=.16
 M[k]=m
parts=[];scad=[]
def record(o,id,role,loc,dim):
 o['component_id']=id;o['role']=role;o['geometry_status']='CONCEPTUAL_ILLUSTRATIVE_MM'
 parts.append({'id':id,'name':o.name,'role':role,'position_mm':loc,'dimensions_mm':dim,'status':'CONCEPTUAL','confidence':'illustrative; no vendor drawing or metrology','source':'tools/rig_foundation.py; expanded by tools/build_rig.py'})
def cube(id,role,loc,dim,mat='aluminum',bevel=1):
 bpy.ops.mesh.primitive_cube_add(size=1,location=[v/1000 for v in loc]);o=bpy.context.object;o.name=id+' '+role;o.dimensions=[v/1000 for v in dim];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(M[mat])
 if bevel:m=o.modifiers.new('Edge breaks','BEVEL');m.width=bevel/1000;m.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 record(o,id,role,loc,dim);scad.append(f'translate({loc}) cube('+('[base_length,base_width,12]' if id=='B01' else str(dim))+', center=true);');return o
def cyl(id,role,loc,r,h,mat='aluminum',axis='Z'):
 rot=(0,math.pi/2,0) if axis=='X' else ((math.pi/2,0,0) if axis=='Y' else (0,0,0))
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r/1000,depth=h/1000,location=[v/1000 for v in loc],rotation=rot);o=bpy.context.object;o.name=id+' '+role;o.data.materials.append(M[mat]);bpy.ops.object.shade_smooth();record(o,id,role,loc,[r*2,r*2,h]);scad.append(f'translate({loc}) rotate({[0,90,0] if axis=="X" else ([90,0,0] if axis=="Y" else [0,0,0])}) cylinder(r={r},h={h},center=true,$fn=64);');return o
def path(id,role,points,r,mat):
 c=bpy.data.curves.new(id,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=r/1000;c.bevel_resolution=5
 p=c.splines.new('BEZIER');p.bezier_points.add(len(points)-1)
 for b,co in zip(p.bezier_points,points):b.co=[v/1000 for v in co];b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(id+' '+role,c);bpy.context.collection.objects.link(o);o.data.materials.append(M[mat]);record(o,id,role,points[0],{'path_mm':points,'radius_mm':r})
 for a,b in zip(points,points[1:]):scad.append(f'hull() {{ translate({a}) sphere(r={r},$fn=16); translate({b}) sphere(r={r},$fn=16); }}')
 return o
def label(text,loc,size=7):
 c=bpy.data.curves.new('Label '+text,'FONT');c.body=text;c.size=size/1000;c.align_x='CENTER';o=bpy.data.objects.new('Label '+text,c);bpy.context.collection.objects.link(o);o.location=[v/1000 for v in loc];o.data.materials.append(M['dark']);return o
cube('B01','Bench base',[300,210,0],[600,420,12],'white',3)
for x in [30,570]:
 for y in [30,390]:cyl(f'B02_{x}_{y}','Isolating foot',[x,y,-12],14,12,'black')
cube('M01','Syringe pump base',[190,145,22],[290,122,12])
for y in [105,183]:cube('M02_'+str(y),'Linear rail',[190,y,41],[258,12,14],'aluminum',.5)
cube('M03','Motor',[70,144,67],[42,42,42],'dark',2)
cyl('M04','Flexible coupling',[101,144,67],9,20,'aluminum','X')
cyl('M05','Lead screw',[212,144,67],4,210,'aluminum','X')
for x in range(114,316,4):cyl('M05t_'+str(x),'Illustrative screw ridge',[x,144,67],4.7,1.3,'aluminum','X')
cube('M06','Lead screw end bearing',[319,144,67],[14,26,26],'dark')
cube('M07','Carriage',[145,144,56],[25,100,12],'blue')
cube('M08','Plunger pusher',[150,144,88],[10,66,62],'blue')
for x in [215,284]:
 cube('M09_'+str(x),'Syringe cradle',[x,144,79],[13,50,20],'white')
 cyl('M10_'+str(x),'Cradle top saddle',[x,144,92],18,12,'white','X')
cyl('S01','Syringe barrel',[239,144,102],15,116,'glass','X')
cyl('S02','Fluid inside barrel',[255,144,102],12,77,'blue','X')
cyl('S03','Plunger seal',[211,144,102],12.5,7,'dark','X')
cyl('S04','Plunger rod',[181,144,102],3,57,'white','X')
cyl('S05','Plunger flange',[153,144,102],17,4,'white','X')
cyl('S06','Syringe finger flange',[181,144,102],20,3,'white','X')
cyl('S07','Outlet fitting',[305,144,102],5,16,'white','X')
for x in range(198,286,8):
 cube('S08_'+str(x),'Illustrative graduation',[x,129,103],[.7,.7,5 if x%16 else 8],'dark',0)
cube('V01','Proposed pinch valve',[365,135,49],[44,42,66],'orange',3)
cube('V02','Valve mounting foot',[365,135,18],[66,68,8])
cube('T01','Balance enclosure',[488,144,27],[154,150,42],'white',6)
cyl('T02','Balance pan',[488,158,54],61,7)
cube('T03','Balance display',[487,84,45],[72,25,3],'dark')
label('MASS  g',[487,84,47],5)
cyl('R01','Receiving vessel',[488,158,103],36,88,'glass')
# Open vessel cavity. The boolean is a geometry aid, not a fluid simulation.
vessel=bpy.context.object
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.032,depth=.090,location=(.488,.158,.109));cavity=bpy.context.object
mod=vessel.modifiers.new('Open receiving cavity','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cavity
bpy.context.view_layer.objects.active=vessel;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cavity,do_unlink=True)
cyl('R02','Saline in receiver',[488,158,75],32,28,'blue')
path('F01','Continuous saline path',[[313,144,102],[339,144,105],[355,135,81],[376,135,81],[430,149,152],[488,158,158],[488,158,139]],2.1,'fluid')
cube('T04','Independent monitor',[491,295,31],[105,88,34],'dark',4)
cube('T05','Monitor PCB',[491,295,49],[92,76,2],'board')
cube('T06','Trip driver',[535,291,56],[19,25,12],'orange')
cube('G01','Gateway host',[275,311,33],[108,92,38],'dark',4)
cube('P01','Pump endpoint PCB',[115,303,23],[82,60,3],'board')
cube('P02','Stepper driver',[118,300,33],[24,20,17],'aluminum')
cube('C01','CGM emulator',[61,358,24],[54,36,18],'blue',3)
cube('E01','Isolated supply concept',[396,337,31],[66,80,35],'white',3)
for id,pts,col in [('W01',[[529,283,56],[559,269,58],[561,233,37],[383,220,37],[367,156,68]],'orange'),('W02',[[469,286,51],[452,257,54],[471,228,40],[488,215,38]],'black'),('W03',[[129,282,26],[110,255,24],[68,222,40],[64,166,65]],'black'),('W04',[[306,304,38],[366,281,30],[469,292,44]],'blue'),('W05',[[244,304,38],[177,277,25],[135,303,28]],'blue'),('W06',[[397,303,42],[434,279,37],[469,290,44]],'orange')]:path(id,'Conceptual electrical connection',pts,1.6,col)
