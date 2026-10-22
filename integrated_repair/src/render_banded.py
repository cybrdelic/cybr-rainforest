"""Low-memory native full-resolution rendering with resumable exact pixel bands.
Run with system Python (stdlib only); array extraction runs only after Blender exits.
"""
from __future__ import annotations
from pathlib import Path
import argparse,subprocess,os,json,time,hashlib,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--blender',required=True);ap.add_argument('--python',default=shutil.which('python3') or sys.executable);ap.add_argument('--scene',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--camera',default='04_BARK_AND_LITTER');ap.add_argument('--width',type=int,default=1280);ap.add_argument('--height',type=int,default=960);ap.add_argument('--samples',type=int,default=48);ap.add_argument('--band-rows',type=int,default=240);ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
    if min(a.width,a.height,a.samples,a.band_rows,a.threads)<=0:ap.error('All dimensions/sample counts must be positive')
    if not a.scene.is_file():ap.error('Scene is missing')
    a.scene=a.scene.resolve();a.output=a.output.resolve();a.output.parent.mkdir(parents=True,exist_ok=True)
    raw=ROOT/'raw_bands'/a.output.stem;raw.mkdir(parents=True,exist_ok=True)
    plan={'scene':str(a.scene),'scene_sha256':sha(a.scene),'width':a.width,'height':a.height,'samples':a.samples,'band_rows':a.band_rows,'camera':a.camera,'output':str(a.output),'geometry_culled_for_memory':False,'upscaling':False}
    pp=raw/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise RuntimeError('A different plan exists: use a new output basename')
    pp.write_text(json.dumps(plan,indent=2));status=a.output.with_suffix('.pipeline.json');state={'completed':False,'plan':plan,'stages':[]}
    env=dict(os.environ,MALLOC_ARENA_MAX='2',OMP_NUM_THREADS=str(a.threads),MALLOC_TRIM_THRESHOLD_='131072')
    base=[a.blender,'-b','-t',str(a.threads),'--python-exit-code','1','-P']
    def run(name,cmd):
        state['running']=name;status.write_text(json.dumps(state,indent=2));start=time.monotonic()
        with (raw/(name+'.log')).open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
        state['stages'].append({'stage':name,'returncode':result.returncode,'seconds':time.monotonic()-start});status.write_text(json.dumps(state,indent=2))
        if result.returncode:raise RuntimeError(name+' failed; completed earlier bands remain resumable')
    for mode,spp in [('radiance',a.samples),('guides',4),('normals',4)]:
        for index,top in enumerate(range(0,a.height,a.band_rows)):
            bottom=min(a.height,top+a.band_rows);p=raw/f'{mode}_{index:02d}.exr';rp=p.with_suffix('.json')
            if p.is_file() and rp.is_file():
                rec=json.loads(rp.read_text())
                if rec.get('completed') and rec['scene_sha256']==plan['scene_sha256'] and rec['image_sha256']==sha(p) and rec['mode']==mode and rec['samples']==spp and rec.get('crop_top',0)==top and rec.get('crop_bottom',a.height)==bottom:
                    state['stages'].append({'stage':p.stem,'verified_resume':True});continue
            run(p.stem,base+[str(ROOT/'src/render_forest.py'),'--','--scene',str(a.scene),'--output',str(p),'--camera',a.camera,'--width',str(a.width),'--height',str(a.height),'--samples',str(spp),'--mode',mode,'--top',str(top),'--bottom',str(bottom)])
    manifest=raw/'assembled.json'
    run('assemble',[a.python,str(ROOT/'src/assemble_bands.py'),'--plan',str(pp),'--output',str(manifest)])
    run('denoise',base+[str(ROOT/'legacy/src/denoise_checkpoint.py'),'--','--manifest',str(manifest),'--output',str(a.output)])
    rec=json.loads(a.output.with_suffix('.json').read_text())
    if not rec.get('completed') or sha(a.output)!=rec['image_sha256']:raise RuntimeError('Final output did not verify')
    state['completed']=True;state['running']=None;status.write_text(json.dumps(state,indent=2));print('BAND_DELIVERY_COMPLETE',a.output)
if __name__=='__main__':main()
