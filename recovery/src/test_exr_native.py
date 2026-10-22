import bpy, sys, json, hashlib, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from exr_compat import configure_exr
start=time.time()
bpy.ops.wm.read_factory_settings(use_empty=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.cycles.use_denoising=False
s.render.resolution_x=32;s.render.resolution_y=24;s.render.resolution_percentage=100
s.render.threads_mode='FIXED';s.render.threads=1;s.render.use_compositing=False
rows=[]
for multi in (False,True):
 rec=configure_exr(s,multilayer=multi);p=ROOT/'evidence'/('multilayer_smoke.exr' if multi else 'singlelayer_smoke.exr');s.render.filepath=str(p)
 bpy.ops.render.render(write_still=True)
 if not p.is_file():raise RuntimeError('EXR not produced '+str(p))
 with p.open('rb') as f:
  magic=f.read(4)
 if magic!=bytes.fromhex('762f3101'): raise RuntimeError('Invalid OpenEXR magic')
 rec.update(multilayer_requested=multi,path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),exr_magic_valid=True)
 rows.append(rec)
report={'completed':True,'scope':'Native EXR API and write test on factory scene, NOT a forest realism test','native_version':bpy.app.version_string,'native_build':bpy.app.build_hash.decode(),'exports':rows,'seconds':time.time()-start}
(ROOT/'evidence/EXR_NATIVE_TEST.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
