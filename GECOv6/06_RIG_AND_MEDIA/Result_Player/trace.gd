extends Control
var cases:Array=[]
var case_index:=0
var sample:=0
var frame_no:=0
var movie:=false
var qa:=false
var playing:=false
var elapsed:=0.0
var axes:Dictionary={}
var font:Font=ThemeDB.fallback_font
var colors=[Color('#42CEBF'),Color('#F0AD63')]
var ink=Color('#F1F6FA')
var gray=Color('#91A8B8')
var bg=Color('#0A1825')
var selector:OptionButton
var slider:HSlider
var glossary={'clean':'Clean conditions','excess_2x':'Actuator command multiplied by two','stuck_on':'Stuck-on actuator adds delivery','cgm_missing':'CGM report is missing','excess_bias_report_mask':'Excess + CGM bias + masked network mass report'}
func _ready():
 cases=JSON.parse_string(FileAccess.get_file_as_string('res://cases.json'));axes=JSON.parse_string(FileAccess.get_file_as_string('res://axes.json'))
 var args=OS.get_cmdline_user_args();movie='--movie' in args;qa='--qa' in args
 for arg in args:
  if arg.begins_with('--case='):case_index=int(arg.get_slice('=',1))
 selector=OptionButton.new();selector.position=Vector2(1370,880);selector.size=Vector2(500,44)
 for c in cases:selector.add_item(c.family+' / '+c.condition)
 selector.select(case_index);selector.item_selected.connect(func(i):case_index=i;sample=0;elapsed=0;queue_redraw());add_child(selector)
 slider=HSlider.new();slider.position=Vector2(160,936);slider.size=Vector2(1080,30);slider.min_value=0;slider.max_value=575;slider.step=1
 slider.value_changed.connect(func(v):sample=int(v);queue_redraw());add_child(slider)
 if movie or qa:selector.visible=false;slider.visible=false
 if '--self-test' in args:
  assert(cases.size()==10)
  for c in cases:
   assert(c.arms.size()==2)
   for a in c.arms:assert(a.columns.sample.size()==576)
  print('PASS fixed10cases, paired arms, complete576samples and shared axes');get_tree().quit()
func _unhandled_key_input(event):
 if event is InputEventKey and event.pressed:
  if event.keycode==KEY_SPACE:playing=not playing
  elif event.keycode==KEY_RIGHT:sample=min(575,sample+1)
  elif event.keycode==KEY_LEFT:sample=max(0,sample-1)
  elif event.keycode==KEY_HOME:sample=0;elapsed=0
  queue_redraw()
func _process(delta):
 if movie:
  # Two seconds of context, every sample for two frames, then five seconds final hold.
  sample=clampi(int((frame_no-48)/2),0,575);frame_no+=1
  if frame_no>48+1152+120:get_tree().quit();return
 elif qa:
  if frame_no>=cases.size()*3:get_tree().quit();return
  case_index=int(frame_no/3);sample=[0,167,575][frame_no%3];frame_no+=1
 elif playing:
  elapsed+=delta;sample=min(575,int(elapsed*12));slider.set_value_no_signal(sample)
 queue_redraw()
func txt(x:float,y:float,t:String,size:int=24,color:Color=Color.WHITE):draw_string(font,Vector2(x,y),t,HORIZONTAL_ALIGNMENT_LEFT,-1,size,color)
func val(v,decimals:int=3)->String:
 return 'missing' if v==null else String.num(float(v),decimals)
func point(i:int,v:float,rect:Rect2,lo:float,hi:float)->Vector2:
 return Vector2(rect.position.x+rect.size.x*(i+1)/576.,rect.end.y-rect.size.y*(v-lo)/(hi-lo))
func plot_axes(rect:Rect2,lo:float,hi:float,title:String):
 draw_rect(rect,Color('#102333'))
 var fx=rect.position.x+rect.size.x*12/48.;var fw=rect.size.x*2/48.
 draw_rect(Rect2(fx,rect.position.y,fw,rect.size.y),Color(.7,.35,.2,.20))
 txt(rect.position.x,rect.position.y-17,title,25,ink)
 for j in range(5):
  var y=rect.end.y-j*rect.size.y/4.;draw_line(Vector2(rect.position.x,y),Vector2(rect.end.x,y),Color('#2D4353'),1)
  txt(rect.position.x-78,y+8,String.num(lo+(hi-lo)*j/4.,0),21,gray)
 for h in range(0,49,6):
  var x=rect.position.x+rect.size.x*h/48.;draw_line(Vector2(x,rect.position.y),Vector2(x,rect.end.y),Color('#263B4B'),1)
  txt(x-12,rect.end.y+27,str(h),20,gray)
 var now=rect.position.x+rect.size.x*(sample+1)/576.;draw_line(Vector2(now,rect.position.y),Vector2(now,rect.end.y),Color('#DAEAF3'),1.3)
func curve(values:Array,rect:Rect2,lo:float,hi:float,color:Color):
 var points=PackedVector2Array()
 for i in range(sample+1):points.append(point(i,float(values[i]),rect,lo,hi))
 if points.size()>1:draw_polyline(points,color,2.3,true)
 elif points.size()==1:draw_circle(points[0],3,color)
func _draw():
 if cases.is_empty():return
 var c=cases[case_index]
 draw_rect(Rect2(0,0,1920,1080),bg)
 txt(50,64,'GECOv6   Full follow-up, matched comparison',43,ink)
 txt(52,108,glossary.get(c.condition,c.condition),31,Color('#D7E7F1'))
 txt(52,144,c.family+'   /   '+c.unit+'   /   seed '+str(int(c.seed))+'   /   fixed clean requests',22,gray)
 txt(1370,107,'SIMULATION RESULT',24,Color('#FFD27B'))
 txt(1370,145,'IIT Patna measurements pending',22,Color('#FFD27B'))
 var g=Rect2(160,217,1080,252);var d=Rect2(160,570,1080,216)
 plot_axes(g,axes.glucose_min,axes.glucose_max,'Evaluator glucose (mg/dL)');plot_axes(d,0,axes.delivery_max,'Cumulative true emission (research U)')
 curve(c.reference.glucose,g,axes.glucose_min,axes.glucose_max,Color('#7D92A1'));curve(c.reference.emitted,d,0,axes.delivery_max,Color('#7D92A1'))
 for a in range(2):
  var r=c.arms[a].columns;curve(r.true_glucose_mgdl,g,axes.glucose_min,axes.glucose_max,colors[a]);curve(r.cumulative_emitted_u,d,0,axes.delivery_max,colors[a])
  var y=235+a*285
  txt(1370,y,'FULL + SUPERVISED' if a==0 else 'SIMPLE + SUPERVISED',27,colors[a])
  txt(1370,y+42,'State after sample: '+r.recovery_state[sample],23,ink)
  txt(1370,y+79,'Excess vs clean     '+val(r.cumulative_excess_u[sample])+' U',24,ink)
  txt(1370,y+114,'Deficit vs clean       '+val(r.cumulative_deficit_u[sample])+' U',24,ink)
  txt(1370,y+149,'Request / permit / emitted',22,gray)
  txt(1370,y+182,val(r.requested_u[sample])+' / '+val(r.authorized_u[sample])+' / '+val(r.actual_emitted_u[sample])+' U',25,ink)
  txt(1370,y+217,'Domain-flagged samples: '+str(int(r.cumulative_domain_flags[sample])),21,Color('#FFD27B'))
  txt(1370,y+250,'Reported CGM: '+val(r.reported_cgm_mgdl[sample],1)+' mg/dL',21,gray)
  var sy=858+a*27
  txt(62,sy+16,'Full' if a==0 else 'Simple',20,colors[a])
  for k in range(sample+1):
   var state=r.state_before_emission[k];var color=Color('#25756F') if state=='RUN' else Color('#D57A44') if state=='LATCHED' else Color('#C0AC50')
   draw_rect(Rect2(160+1080.*k/576.,sy,1080./576.+.4,16),color)
 txt(160,510,'Teal: full     Amber: simple     Gray: common clean reference     Shaded window: scheduled condition 12–14 h',20,gray)
 txt(460,833,'Simulation time (hours)',22,gray)
 txt(1370,864,'Time '+val((sample+1)*5./60.,2)+' h   /   sample '+str(sample+1)+' of 576',25,ink)
 txt(1370,906,'Local / network mass (full), g',21,gray)
 txt(1370,938,val(c.arms[0].columns.local_measured_delta_g[sample])+' / '+val(c.arms[0].columns.network_reported_delta_g[sample]),25,ink)
 txt(160,946,'Recovery strip: RUN   /   LATCHED   /   VERIFY or PROBATION',22,gray)
 txt(52,997,'Fixed example chosen before outcomes. The full 48-hour record and both excess and deficit remain visible.',23,ink)
 txt(52,1040,'Five-minute observations; no new samples invented. Domain flags limit physiological interpretation.',22,Color('#FFD27B'))
