"""Verify the delivered GECOv6 folder or complete ZIP using only Python stdlib.

Run from any directory: python /path/GECOv6/09_REPRODUCIBILITY/verify_package.py
Or: python verify_package.py --zip /path/GECOv6_Complete_Package.zip
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,zipfile
MANIFEST='CHECKSUM_MANIFEST.json'
def digest(stream):
 h=hashlib.sha256();size=0
 for b in iter(lambda:stream.read(1024*1024),b''):h.update(b);size+=len(b)
 return h.hexdigest(),size
def check_manifest(m):
 assert m['schema']=='geco-release-manifest-v1'
 paths=[e['path'] for e in m['files']];assert len(paths)==len(set(paths))
 for p in paths:
  assert not PurePosixPath(p).is_absolute() and '..' not in PurePosixPath(p).parts
 return m['files']
def verify_folder(root):
 m=json.loads((root/MANIFEST).read_text());entries=check_manifest(m);fail=[]
 for e in entries:
  p=root/e['path']
  if not p.is_file():fail.append({'file':e['path'],'reason':'missing'});continue
  with p.open('rb') as f:h,n=digest(f)
  if (h,n)!=(e['sha256'],e['bytes']):fail.append({'file':e['path'],'reason':'hash_or_size_mismatch'})
 return {'mode':'folder','payload_files_checked':len(entries),'bytes_checked':sum(e['bytes'] for e in entries),'failures':fail,'status':'PASS' if not fail else 'FAIL'}
def verify_zip(path):
 fail=[]
 with zipfile.ZipFile(path) as z:
  prefix='GECOv6/';names=z.namelist();assert len(names)==len(set(names)),'duplicate ZIP entries'
  m=json.loads(z.read(prefix+MANIFEST));entries=check_manifest(m)
  expected={prefix+e['path'] for e in entries}|{prefix+MANIFEST}
  assert set(names)==expected,{'extra':list(set(names)-expected),'missing':list(expected-set(names))}
  for e in entries:
   with z.open(prefix+e['path']) as f:h,n=digest(f)
   if (h,n)!=(e['sha256'],e['bytes']):fail.append({'file':e['path'],'reason':'hash_or_size_mismatch'})
  mh=hashlib.sha256(z.read(prefix+MANIFEST)).hexdigest()
 with path.open('rb') as f:zh,zn=digest(f)
 return {'mode':'zip','archive':path.name,'archive_sha256':zh,'archive_bytes':zn,'manifest_sha256':mh,'payload_files_checked':len(entries),'zip_entries':len(names),'bytes_checked':sum(e['bytes'] for e in entries),'failures':fail,'status':'PASS' if not fail else 'FAIL'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--zip',type=Path);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
 result=verify_zip(a.zip) if a.zip else verify_folder(a.root);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='PASS' else 1)
