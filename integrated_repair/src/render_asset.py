# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
import bpy,sys,argparse,time,json,hashlib,os
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--out',required=True);ap.add_argument('--lighting',default='soft',choices=['soft','side','back']);ap.add_argument('--width',type=int,default=1600);ap.add_argument('--height',type=int,default=1200);ap.add_argument('--samples',type=int,default=96);ap.add_argument('--denoise',type=int,default=1);ap.add_argument('--angle',type=float,default=0);ap.add_argument('--linear',type=int,default=0);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
base=Path(__file__).resolve().parents[1]
a.scene=str((base/Path(a.scene)).resolve());a.out=str((base/Path(a.out)).resolve())
bpy.ops.wm.open_mainfile(filepath=a.scene,use_scripts=False,load_ui=False);s=bpy.context.scene;s.timeline_markers.clear();s.render.resolution_x=a.width;s.render.resolution_y=a.height;s.render.resolution_percentage=100;s.cycles.samples=a.samples;s.cycles.adaptive_min_samples=min(24,a.samples);s.cycles.use_denoising=bool(a.denoise)
for setting,value in [('debug_bvh_layout','EMBREE'),('debug_bvh_type','STATIC_BVH'),('debug_use_compact_bvh',True),('debug_use_spatial_splits',False)]:
 if hasattr(s.cycles,setting):setattr(s.cycles,setting,value)
for vl in s.view_layers:
 vl.samples=0
 if a.linear:vl.cycles.denoising_store_passes=True
if a.linear:
 s.cycles.use_denoising=False;configure_exr(s,multilayer=True)
for n in ['Key_soft','Key_side','Key_back']:bpy.data.objects[n].hide_render=True
bpy.data.objects['Key_'+a.lighting].hide_render=False
if a.angle:
 import math
 from mathutils import Matrix
 target=Vector((0,0,.3));s.camera.location=target+Matrix.Rotation(math.radians(a.angle),3,'Z')@(s.camera.location-target);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
p=Path(a.out);p.parent.mkdir(exist_ok=True,parents=True);s.render.filepath=str(p)
rec={'completed':False,'scene':a.scene,'scene_sha256':hashlib.file_digest(open(a.scene,'rb'),'sha256').hexdigest(),'width':a.width,'height':a.height,'samples_max':a.samples,'denoised':bool(a.denoise) and not bool(a.linear),'linear_checkpoint':bool(a.linear),'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma,'lighting':a.lighting,'angle':a.angle,'renderer':'CYCLES','native_blender':bpy.app.version_string,'image_generation_used':False,'upscaled':False,'camera_matrix':[list(r) for r in s.camera.matrix_world]}
p.with_suffix('.json').write_text(json.dumps(rec,indent=2));t=time.monotonic();print('RENDER_START',str(p),flush=True)
bpy.ops.render.render(write_still=True)
rec['camera_matrix']=[list(r) for r in s.camera.matrix_world]
rec.update(completed=True,seconds=time.monotonic()-t,peak_rss_mb=peak_rss_mib(),image_sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),output=str(p))
p.with_suffix('.json').write_text(json.dumps(rec,indent=2));print('RENDER_COMPLETE',str(p),flush=True)
