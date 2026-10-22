"""Checkpointing synchronous production queue. Each native process logs its result.
Runs only explicit tasks and writes COMPLETE only after exit and file checks.
"""
import sys,os,subprocess,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLENDER='inputs/historical/native_runtime/blender/blender'
ENV={**os.environ,'MALLOC_ARENA_MAX':'2','MALLOC_TRIM_THRESHOLD_':'131072','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'2'}
def native(script,args,logname):
    cmd=[BLENDER,'-b','-t','4','--python-exit-code','1','-P',str(ROOT/'src'/script)]
    if args:cmd+=['--']+list(map(str,args))
    with (ROOT/'evidence'/logname).open('w') as f:
        r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=ENV)
    if r.returncode:raise RuntimeError(f'{logname}: native exit {r.returncode}')
def studio(spec,light,width,samples):
    name=f'{spec.upper()}_{light.upper()}'
    native('studio.py',['--specimen',spec,'--light',light,'--width',width,'--samples',samples,'--output',ROOT/'renders'/f'{name}.png'],name+'.log')
def forest(scene,name,width=1280,height=960,samples=48,camera='04_BARK_AND_LITTER'):
    folder=ROOT/'render_work'/name;folder.mkdir(parents=True,exist_ok=True)
    for mode in ('radiance','guides','normals'):
        out=folder/f'{mode}.exr'
        native('render.py',['--scene',scene,'--camera',camera,'--width',width,'--height',height,'--samples',samples if mode=='radiance' else 8,'--mode',mode,'--output',out],name+'_'+mode+'.log')
    cmd=['python3',str(ROOT/'src/finish.py'),'--radiance',str(folder/'radiance.exr'),'--guides',str(folder/'guides.exr'),'--normals',str(folder/'normals.exr'),'--output',str(folder/'linear.json')]
    with (ROOT/'evidence'/f'{name}_extract.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=ENV)
    if r.returncode:raise RuntimeError('EXR extraction failed')
    native('denoise_checkpoint.py',['--manifest',folder/'linear.json','--output',ROOT/'renders'/f'{name}.png'],name+'_finish.log')
if __name__=='__main__':
    start=time.time()
    try:
        mode=sys.argv[1]
        if mode=='studio':
            studio('macro','soft',2048,128);studio('branch','soft',1600,128);studio('branch','grazing',1600,128);studio('branch','back',1600,128);studio('fern','soft',1600,128);studio('woody','soft',1600,128)
        elif mode=='integrate':native('integrate_foliage_candidate.py',[],'integration.log')
        elif mode=='forest':
            forest('inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend','FOREST_CONTROL')
            forest(str(ROOT/'A01_FOREST_CANDIDATE.blend'),'FOREST_CANDIDATE')
        (ROOT/'evidence'/f'queue_{mode}.json').write_text(json.dumps({'completed':True,'seconds':time.time()-start},indent=2))
    except Exception as e:
        (ROOT/'evidence'/f'queue_{mode}.json').write_text(json.dumps({'completed':False,'error':str(e),'seconds':time.time()-start},indent=2));raise
