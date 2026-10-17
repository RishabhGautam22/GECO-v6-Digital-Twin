extends Control
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
