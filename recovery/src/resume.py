"""Reconstruct the retained forest and render it with verified, resumable stages.

This rebuilds the integrated-repair baseline; it is not the uncompleted V14 art
revision. All stages use native Blender. No scene or image is substituted.

Example:
 python resume.py --blender /path/to/blender --baseline /path/to/V11.blend \
   --source-archive /path/to/GREEN_TERROR_INTEGRATED_REPAIR_SOURCE.zip \
   --workdir /path/to/recovery --render --width 960 --height 720 --samples 32
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path
EXPECTED_BASELINE='16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e'

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def atomic(path:Path,value:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.partial')
    temporary.write_text(json.dumps(value,indent=2));temporary.replace(path)

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',required=True,type=Path)
    p.add_argument('--baseline',required=True,type=Path)
    p.add_argument('--source-archive',required=True,type=Path)
    p.add_argument('--workdir',required=True,type=Path)
    p.add_argument('--render',action='store_true')
    p.add_argument('--width',type=int,default=960)
    p.add_argument('--height',type=int,default=720)
    p.add_argument('--samples',type=int,default=32)
    p.add_argument('--threads',type=int,default=4)
    p.add_argument('--band-rows',type=int,default=180)
    p.add_argument('--camera',default='04_BARK_AND_LITTER')
    a=p.parse_args()
    if min(a.width,a.height,a.samples,a.threads,a.band_rows)<=0:p.error('Dimensions, samples, threads and rows must be positive.')
    baseline=a.baseline.resolve();binary=a.blender.resolve();archive=a.source_archive.resolve();root=a.workdir.resolve()
    if not binary.is_file() or not os.access(binary,os.X_OK):p.error('A native Blender executable is required.')
    if not baseline.is_file() or sha(baseline)!=EXPECTED_BASELINE:p.error('The exact retained V11 model is required; no automatic fallback.')
    if not archive.is_file():p.error('Source archive is missing.')
    root.mkdir(parents=True,exist_ok=True);ev=root/'evidence';ev.mkdir(exist_ok=True)
    dep=root/'dependencies';dep.mkdir(exist_ok=True)
    unpack=dep/'GREEN_TERROR_ASSET_REPAIR';archive_digest=sha(archive)
    stamp=dep/'archive_identity.json'
    if stamp.is_file():
        if json.loads(stamp.read_text()).get('sha256')!=archive_digest:raise RuntimeError('Different source archive in existing work directory; use a new work directory.')
    else:
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                target=(dep/item.filename).resolve()
                if not target.is_relative_to(dep.resolve()):raise RuntimeError('Unsafe archive path.')
                if ((item.external_attr>>16)&0o170000)==0o120000:raise RuntimeError('Archive symlinks are not accepted.')
            z.extractall(dep)
        atomic(stamp,{'sha256':archive_digest})
    compat=Path(__file__).with_name('exr_compat.py')
    if not compat.is_file():raise RuntimeError('Keep exr_compat.py alongside resume.py.')
    shutil.copyfile(compat,unpack/'src/exr_compat.py')
    renderer=unpack/'src/render_forest.py';text=renderer.read_text()
    if 'from exr_compat import configure_exr' not in text:
        text=text.replace('ROOT=Path(__file__).resolve().parents[1]',"ROOT=Path(__file__).resolve().parents[1]\nsys.path.insert(0,str(ROOT/'src'))\nfrom exr_compat import configure_exr")
        anchor="    gc.collect();ctypes.CDLL(None).malloc_trim(0);save();print('NATIVE_RENDER_BEGIN',r,flush=True)"
        if anchor not in text:raise RuntimeError('Unrecognized native renderer: refusing a guessed patch.')
        text=text.replace(anchor,"    r['export_configuration']=configure_exr(s,multilayer=False)\n"+anchor)
        renderer.write_text(text)
    env=dict(os.environ,GREEN_TERROR_BASELINE=str(baseline),MALLOC_ARENA_MAX='2',MALLOC_TRIM_THRESHOLD_='131072',OMP_NUM_THREADS=str(a.threads))
    b=[str(binary),'-b','-t',str(a.threads),'--python-exit-code','1','-P']
    state={'scope':'Verified integrated-repair reconstruction, not V14 completion','completed':False,'source_archive_sha256':archive_digest,'baseline_sha256':EXPECTED_BASELINE,'steps':[]}
    def run(name,cmd,output:Path,inputs:list[Path]):
        identity={'command':cmd,'inputs':{str(i):sha(i) for i in inputs},'blender_sha256':sha(binary)}
        rec=ev/(name+'.json')
        if rec.is_file() and output.is_file():
            old=json.loads(rec.read_text())
            if old.get('completed') and old.get('identity')==identity and old.get('output_sha256')==sha(output):
                state['steps'].append({'name':name,'verified_resume':True});return
        state['stage']=name;atomic(ev/'STATUS.json',state);started=time.monotonic()
        with (ev/(name+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        d={'completed':False,'identity':identity,'returncode':r.returncode,'seconds':time.monotonic()-started,'output':str(output)}
        if r.returncode or not output.is_file():
            atomic(rec,d);raise RuntimeError(name+' failed: inspect '+str(ev/(name+'.log')))
        d.update(completed=True,output_sha256=sha(output),output_bytes=output.stat().st_size);atomic(rec,d)
        state['steps'].append({'name':name,'completed':True,'seconds':d['seconds']});atomic(ev/'STATUS.json',state)
    try:
        specs=[('01_integrate','integrate_forest.py',[],baseline,'GREEN_TERROR_INTEGRATED_REPAIR.blend'),
               ('02_finalize','finalize_models.py',['--','forest'],unpack/'GREEN_TERROR_INTEGRATED_REPAIR.blend','GREEN_TERROR_FOREST_FINAL.blend'),
               ('03_architecture','refine_architecture.py',[],unpack/'GREEN_TERROR_FOREST_FINAL.blend','GREEN_TERROR_FOREST_REPAIRED.blend'),
               ('04_bindings','repair_climber_bindings.py',[],unpack/'GREEN_TERROR_FOREST_REPAIRED.blend','GREEN_TERROR_FOREST_LEAF_BINDING_TEST.blend')]
        for name,script,extra,source,outname in specs:
            script_path=unpack/'src'/script
            run(name,b+[str(script_path)]+extra,unpack/outname,[source,script_path,archive])
        result=root/'GREEN_TERROR_RECONSTRUCTED_BASELINE.blend'
        shutil.copyfile(unpack/'GREEN_TERROR_FOREST_LEAF_BINDING_TEST.blend',result)
        if sha(baseline)!=EXPECTED_BASELINE:raise RuntimeError('Original input changed.')
        state.update(model=str(result),model_sha256=sha(result),original_input_unchanged=True)
        if a.render:
            image=root/'renders/RECOVERED_FOREST_PROOF.png';image.parent.mkdir(exist_ok=True)
            script=unpack/'src/render_banded.py'
            cmd=[sys.executable,str(script),'--blender',str(binary),'--scene',str(result),'--camera',a.camera,'--output',str(image),'--width',str(a.width),'--height',str(a.height),'--samples',str(a.samples),'--threads',str(a.threads),'--band-rows',str(a.band_rows)]
            run('05_native_render',cmd,image,[result,script,renderer,compat])
            record=json.loads(image.with_suffix('.json').read_text())
            if not record.get('completed') or record['image_sha256']!=sha(image) or record['scene_sha256']!=sha(result):raise RuntimeError('Image provenance mismatch.')
            state.update(render=str(image),render_sha256=sha(image))
        state.update(completed=True,stage='complete',visual_upgrade_claim=False,v14_artwork_complete=False)
    except BaseException as error:
        state.update(stage='failed',error=str(error));atomic(ev/'STATUS.json',state);raise
    atomic(ev/'STATUS.json',state);print(json.dumps(state,indent=2))
if __name__=='__main__':main()
