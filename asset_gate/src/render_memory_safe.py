"""Host-side native render + independent denoise. No shell interpolation.
Example: python3 src/render_memory_safe.py --blender /path/to/blender \
  --scene PATCH_ASSET_GATE.blend --output review_renders/patch.png \
  --width 2048 --height 1365 --samples 96
"""
import argparse,subprocess,os
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--blender',required=True);ap.add_argument('--scene',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--width',type=int,default=2048);ap.add_argument('--height',type=int,default=1365);ap.add_argument('--samples',type=int,default=96);ap.add_argument('--lighting',choices=['soft','side','back'],default='soft');ap.add_argument('--angle',type=float,default=0);ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
if not a.scene.is_file():ap.error('Scene does not exist')
if min(a.width,a.height,a.samples,a.threads)<=0:ap.error('Dimensions, samples and thread count must be positive')
S=Path(__file__).resolve().parent;out=a.output.resolve();raw=out.parent/'linear_checkpoints'/(out.stem+'.exr');raw.parent.mkdir(parents=True,exist_ok=True)
common=[a.blender,'-b','-t',str(a.threads),'--python-exit-code','1','-P'];env=dict(os.environ,MALLOC_ARENA_MAX='2',OMP_NUM_THREADS=str(a.threads))
subprocess.run(common+[str(S/'render_asset.py'),'--','--scene',str(a.scene.resolve()),'--out',str(raw),'--width',str(a.width),'--height',str(a.height),'--samples',str(a.samples),'--lighting',a.lighting,'--angle',str(a.angle),'--linear','1'],check=True,env=env)
subprocess.run(common+[str(S/'denoise_linear_asset.py'),'--','--input',str(raw),'--output',str(out)],check=True,env=env)
print(out)
