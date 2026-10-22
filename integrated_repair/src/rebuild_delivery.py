"""Rebuild the delivered repairs from the exact retained V11 baseline.

Run from the extracted source package. Input .blend bytes are never overwritten.
Authoring is deterministic by seed; Blender file metadata can change on resaving.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASELINE_SHA='16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e'

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

def main()->None:
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--blender',default=os.environ.get('BLENDER','blender'))
 p.add_argument('--baseline',type=Path,required=True)
 p.add_argument('--threads',type=int,default=4)
 p.add_argument('--overwrite',action='store_true')
 p.add_argument('--dry-run',action='store_true')
 a=p.parse_args()
 if a.threads<1:p.error('--threads must be positive')
 baseline=a.baseline.resolve()
 if not baseline.is_file() or sha(baseline)!=BASELINE_SHA:p.error('The baseline must be the exact preserved V11 model. See README.md for its identity.')
 exe=shutil.which(a.blender)
 if not exe and not a.dry_run:p.error('Blender is missing; pass --blender /path/to/blender')
 exe=exe or a.blender
 dest=ROOT/'GREEN_TERROR_FOREST_REPAIRED_FINAL.blend'
 if baseline==dest.resolve():p.error('The output must never overwrite the baseline')
 if dest.exists() and not a.overwrite and not a.dry_run:p.error('Final model already exists. Use another unpacked source folder or explicitly pass --overwrite.')
 env=dict(os.environ,GREEN_TERROR_BASELINE=str(baseline),MALLOC_ARENA_MAX='2',MALLOC_TRIM_THRESHOLD_='131072',OMP_NUM_THREADS=str(a.threads))
 b=[exe,'-b','-t',str(a.threads),'--python-exit-code','1','-P']
 steps=[('contact_study',b+[str(ROOT/'src/build_repaired_assets.py'),'--','patch']),
        ('full_forest_bindings',b+[str(ROOT/'src/integrate_forest.py')]),
        ('surface_cleanup',b+[str(ROOT/'src/finalize_models.py'),'--','patch','forest']),
        ('plant_hierarchies',b+[str(ROOT/'src/refine_architecture.py')]),
        ('coherent_leaf_bindings',b+[str(ROOT/'src/repair_climber_bindings.py')])]
 state={'completed':False,'baseline':str(baseline),'baseline_sha256':BASELINE_SHA,'commands':steps,'stages':[],'not_claimed':'Technical rebuilding is not approval of final visual quality.'}
 if a.dry_run:print(json.dumps(state,indent=2));return
 ev=ROOT/'evidence';ev.mkdir(exist_ok=True)
 for name,cmd in steps:
  start=time.monotonic()
  with (ev/f'rebuild_{name}.log').open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  state['stages'].append({'name':name,'returncode':r.returncode,'seconds':time.monotonic()-start})
  (ev/'rebuild_execution.json').write_text(json.dumps(state,indent=2))
  if r.returncode:raise RuntimeError(f'Rebuild failed in {name}; inspect its log. No completion is being claimed.')
 src=ROOT/'GREEN_TERROR_FOREST_LEAF_BINDING_TEST.blend'
 record=json.loads((ev/'climber_binding_review.json').read_text())
 if not record.get('completed') or sha(src)!=record['scene_sha256']:raise RuntimeError('Final candidate does not match its native completion record')
 shutil.copyfile(src,dest)
 with (ev/'rebuild_validation.log').open('w') as f:
  r=subprocess.run(b+[str(ROOT/'src/validate_models.py'),'--',str(dest),str(ROOT/'GROUND_SECTION_FINAL.blend')],env=env,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('Native reopen validation failed')
 for model in (dest,ROOT/'GROUND_SECTION_FINAL.blend'):
  val=json.loads((ev/f'validation_{model.stem}.json').read_text())
  if not val.get('passed') or val['scene_sha256']!=sha(model):raise RuntimeError(f'Invalid saved model: {model.name}')
 if sha(baseline)!=BASELINE_SHA:raise RuntimeError('Baseline input was modified')
 state.update(completed=True,output=str(dest),output_sha256=sha(dest),baseline_unchanged=True)
 (ev/'rebuild_execution.json').write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
if __name__=='__main__':main()
