"""Build a fresh private release archive, preserving all payload bytes."""
from pathlib import Path
import datetime,hashlib,json,os,sys,zipfile
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'09_REPRODUCIBILITY'))
from verify_package import verify_zip,digest,MANIFEST
OUT=R.parent/'GECOv6_Complete_Package.zip'
EXCLUDED={'.work','node_modules','__pycache__','.pytest_cache','.godot','.git','.venv','paper_work'}
def omitted(rel):
 return any(p in EXCLUDED or p.startswith('.chart-data-') for p in rel.parts) or rel.name=='.DS_Store' or rel.suffix in ('.pyc','.blend1') or rel.name.startswith('~$')
def build():
 assert not OUT.exists(),f'Refusing to replace existing {OUT}'
 files=[]
 for base,dirs,names in os.walk(R,followlinks=False):
  base=Path(base);dirs[:]=sorted(d for d in dirs if not omitted((base/d).relative_to(R)) and not (base/d).is_symlink())
  for n in sorted(names):
   p=base/n;rel=p.relative_to(R)
   if omitted(rel) or str(rel)==MANIFEST:continue
   assert not p.is_symlink(),f'Unresolved symlink {p}'
   with p.open('rb') as f:h,size=digest(f)
   files.append({'path':rel.as_posix(),'bytes':size,'sha256':h})
 files.sort(key=lambda e:e['path'])
 prior=next(e for e in files if e['path']=='10_PRIOR_RELEASE/GECOv5_All_In_One_Private.zip')
 assert prior['sha256']=='33ddc95142a56e94bd095cf651dc3a0a35119e26e42c41a3430ef23a4e297242'
 manifest={'schema':'geco-release-manifest-v1','release':'GECOv6','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Private complete working handoff; original sources and prior release preserved; no new public redistribution permission implied.','payload_count':len(files),'payload_bytes':sum(e['bytes'] for e in files),'manifest_self_excluded':True,'excluded_build_material':['.work/','.chart-data-*/','node_modules/','__pycache__/','.pytest_cache/','.godot/','.git/','.venv/','paper_work/','.DS_Store','*.pyc','*.blend1','~$* Office lock files'],'files':files}
 (R/MANIFEST).write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'phase':'manifest','payload_files':len(files),'payload_bytes':manifest['payload_bytes'],'prior_archive_hash':'PASS'}),flush=True)
 partial=OUT.with_suffix('.zip.partial');assert not partial.exists()
 stored={'.zip','.gz','.mp4','.png','.jpg','.jpeg','.pdf','.docx','.pptx','.xlsx','.blend','.glb'}
 with zipfile.ZipFile(partial,'w',allowZip64=True,compresslevel=6) as z:
  for e in files+[{'path':MANIFEST}]:
   p=R/e['path'];ct=zipfile.ZIP_STORED if p.suffix.lower() in stored else zipfile.ZIP_DEFLATED
   z.write(p,arcname='GECOv6/'+e['path'],compress_type=ct)
 print(json.dumps({'phase':'archive_written','archive_bytes':partial.stat().st_size}),flush=True)
 result=verify_zip(partial);assert result['status']=='PASS',result
 partial.rename(OUT);result['archive']=OUT.name
 result['prior_release_sha256']=prior['sha256'];result['prior_release_preserved_byte_for_byte']=True
 (R.parent/'GECOv6_Complete_Package_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
 (R.parent/'GECOv6_Complete_Package.sha256').write_text(result['archive_sha256']+'  '+OUT.name+'\n')
 print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':build()
