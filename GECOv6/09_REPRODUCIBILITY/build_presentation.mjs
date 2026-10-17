import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const skill=process.env.GECO_PRESENTATION_SKILL_DIR??'./tools/presentations';
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const out=path.join(root,'05_PRESENTATION');const work=path.join(root,'.work/presentation');await fs.mkdir(work,{recursive:true});
const specs=JSON.parse(await fs.readFile(path.join(out,'SLIDE_CONTENT.json'),'utf8'));
const P=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#132E40',teal:'#168B8D',muted:'#506579',line:'#D8E3E8',paper:'#FFFFFF',light:'#EEF4F6',orange:'#AA4C2A'};
function box(s,name,x,y,w,h,txt,size=28,color=C.ink,bold=false,fill='none'){
 const sh=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});
 sh.text=txt;sh.text.style={typeface:'Arial',fontSize:size,color,bold,autoFit:'none',wrap:true};return sh;
}
const nativeTables=[],nativeCharts=[],createdSlides=[];
for(let i=0;i<specs.length;i++){
 const d=specs[i],s=P.slides.add();createdSlides.push(s);s.background.fill=C.paper;
 box(s,'title',64,42,1152,90,d.title,i===0?54:42,C.ink,true);
 box(s,'section',66,126,1148,28,d.section,15,C.teal,true);
 box(s,'footer',64,681,1152,22,`GECOv6   |   Nonclinical research   |   ${d.evidence.replaceAll('_',' ')}   |   ${i+1} / ${specs.length}`,13.5,C.muted);
 if(d.kind==='text'){
  let y=i===0?220:196;const gap=i===0?105:121;
  for(let j=0;j<d.paragraphs.length;j++)box(s,'body'+j,72,y+j*gap,1125,gap-14,d.paragraphs[j],i===0?(j===0?37:28):29,j===0?C.ink:C.muted,j===0);
 }else if(d.kind==='image'){
  s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,d.image))),contentType:'image/png',alt:d.title+'; '+d.caption,fit:'contain',position:{left:64,top:166,width:1152,height:443}});
  for(const [label,pos,to] of (d.callouts??[])){const lab=box(s,'component-label',...pos,label,18,C.ink,true,'#FFFFFF');const dot=s.shapes.add({geometry:'ellipse',position:{left:to[0]-2,top:to[1]-2,width:4,height:4},fill:C.ink,line:{fill:C.ink,width:1}});const leader=s.shapes.connect(lab,dot,{kind:'elbow',fromSide:pos[0]<600?'right':'left',line:{fill:C.ink,width:1.2},tail:{type:'arrow',width:'sm',length:'sm'}});leader.bringToFront();dot.bringToFront();lab.bringToFront();}
  box(s,'caption',72,611,1136,d.pending?33:56,d.caption,d.pending?18:20,C.muted);
 }else if(d.kind==='video'){
  box(s,'play-label',927,126,290,28,'PLAY: TAB, THEN ENTER',15,C.teal,true);
  const im=s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,d.poster))),contentType:'image/png',alt:'VIDEO_'+d.id,fit:'contain',position:{left:90,top:161,width:1100,height:440}});
  box(s,'caption',72,612,1136,d.pending?34:60,d.caption,d.pending?18:20,d.evidence.includes('LEGACY')?C.orange:C.muted);
 }else if(d.kind==='table'){
  const vals=d.values;const n=vals.length;const h=Math.min(d.pending?410:430,n*62);const cols=vals[0].length;
  const table=s.tables.add({rows:n,columns:cols,left:72,top:183,width:1136,height:h,values:vals,columnWidths:cols===2?[330,806]:cols===3?[340,400,396]:cols===4?[255,280,245,356]:Array(cols).fill(1136/cols)});
  table.borders.assign({style:'solid',fill:C.line,width:1});
  for(let r=0;r<n;r++)for(let c=0;c<cols;c++){
   const cell=table.getCell(r,c);cell.fill=r===0?C.ink:(r%2===0?C.light:'#FFFFFF');cell.text.style={typeface:'Arial',fontSize:n>7?20:23,bold:r===0,color:r===0?'#FFFFFF':C.ink,autoFit:'none'};
  }
  nativeTables.push(i+1);if(d.caption)box(s,'caption',72,d.pending?610:624,1136,d.pending?32:48,d.caption,18,C.muted);
 }else if(d.kind==='chart'){
  const chart=s.charts.add('bar',{position:{left:85,top:181,width:1110,height:415},categories:d.categories,series:d.series,barOptions:{direction:'column',grouping:'clustered',gapWidth:110},hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:18}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:{fontSize:18}},yAxis:{numberFormatCode:'0.0',min:0,textStyle:{fontSize:18}},xAxis:{textStyle:{fontSize:18}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
  applyPresentationChartFont(chart,{fontFamily:'Arial'});nativeCharts.push(i+1);box(s,'caption',72,620,1136,56,d.caption,20,C.muted);
 }else if(d.kind==='linechart'){
  const chart=s.charts.add('scatter',{scatterOptions:{style:'line'},position:{left:85,top:181,width:1110,height:415},categories:d.categories,series:d.series,hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:18}},yAxis:{numberFormatCode:'0.0',title:'Research U',textStyle:{fontSize:18}},xAxis:{min:10,max:48,majorUnit:6,title:'Simulation hour',textStyle:{fontSize:18}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
  applyPresentationChartFont(chart,{fontFamily:'Arial'});nativeCharts.push(i+1);box(s,'caption',72,620,1136,56,d.caption,20,C.muted);
 }else if(d.kind==='flow'){
  const nodes=d.nodes;const shapes=[];
  for(let j=0;j<nodes.length;j++){
   const x=72+(j<3?j:5-j)*400,y=220+Math.floor(j/3)*175;
   const sh=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:335,height:120},fill:j>3?C.light:'#FFFFFF',line:{fill:C.teal,width:2}});sh.text=nodes[j];sh.text.style={typeface:'Arial',fontSize:27,bold:true,color:C.ink,autoFit:'none'};shapes.push(sh);
  }
  [[0,1],[1,2],[2,3],[3,4],[4,5]].forEach(([a,b])=>s.shapes.connect(shapes[a],shapes[b],{kind:'elbow',fromSide:a===2?'bottom':a>=3?'left':'right',toSide:a===2?'top':a>=3?'right':'left',line:{fill:C.teal,width:2},tail:{type:'arrow',width:'med',length:'med'}}));
  if(d.injection){const inj=box(s,'injection',893,157,291,55,'Injected valid command',21,C.orange,true,'#FFFFFF');s.shapes.connect(inj,shapes[2],{kind:'straight',fromSide:'bottom',toSide:'top',line:{fill:C.orange,width:2},tail:{type:'arrow',width:'med',length:'med'}});}
  box(s,'caption',72,561,1136,d.pending?74:90,d.caption,24,C.muted);
 }
 if(d.pending)box(s,'pending',64,646,1152,30,'IIT Patna measurement pending',18,'#6B4D00',true,'#FFF2CC');
 const notes=`${d.id} — ${d.title}\nEvidence class: ${d.evidence}\nSupported claim IDs: ${d.claims.join(', ')||'Source-derived explanation'}\n${d.notes}\nSource locators:\n${d.sources.join('\n')}\nSource SHA-256:\n${Object.entries(d.source_hashes??{}).map(([a,b])=>a+' '+b).join('\n')}\nCritical limit: numerical findings depend on explicit model assumptions; conceptual geometry is not as-built. No physical performance or clinical safety is established.`;
 s.speakerNotes.textFrame.setText(notes);
}
const candidate=path.join(work,'candidate.pptx');await (await PresentationFile.exportPptx(P)).save(candidate);
await fs.writeFile(path.join(work,'requirements.json'),JSON.stringify({slides:specs.length,nativeTables,nativeCharts},null,2));
const finalPath=path.join(out,'GECOv6_Research_Seminar_base.pptx');
await fs.rm(finalPath,{force:true});
try {await fs.rename(path.join(work,'finalization.json'),path.join(work,'finalization-'+Date.now()+'.json'));} catch(e){if(e.code!=='ENOENT')throw e;}
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:'/usr/bin/python3',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...nativeTables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:specs.length,requiredNativeTableOwnerSlides:nativeTables,requiredNativeChartOwnerSlides:nativeCharts,materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(work,'finalization.json')});
console.log(JSON.stringify(result));
// Export native diagrams independently for reuse and visual inspection.
await fs.mkdir(path.join(work,'previews'),{recursive:true});
for(let i=0;i<specs.length;i++){
 const slide=createdSlides[i];
 if(!slide)break;
 const blob=await P.export({slide,format:'png',scale:1});await fs.writeFile(path.join(work,'previews',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
console.log('Slide production completed');
