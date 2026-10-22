"""Reopen portable asset scenes, audit native data, and render a packed-only smoke test.
Run as a fresh Blender background process AFTER all renders and models are frozen.
"""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
from pathlib import Path
import bpy,numpy as np,json,hashlib,shutil,time,sys
R=Path(__file__).resolve().parents[1];E=R/'evidence';C=R/'_clean_reopen';C.mkdir(exist_ok=True)
paths=['BRANCH_ASSET_GATE.blend','CORDATE_ASSET_GATE.blend','FERN_ASSET_GATE.blend','PATCH_ASSET_GATE.blend','LEAF_UPPER_INSPECTION.blend','LEAF_UNDERSIDE_INSPECTION.blend','BRANCH_INSPECTION_ANIMATION.blend']
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
rows=[]
for name in paths:
 p=R/name;copy=C/name;shutil.copyfile(p,copy);bpy.ops.wm.open_mainfile(filepath=str(copy),load_ui=False,use_scripts=False)
 s=bpy.context.scene;meshrows=[];image_rows=[]
 for m in bpy.data.meshes:
  m.calc_loop_triangles();co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3)
  tr=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',tr);tr=tr.reshape(-1,3)
  ar=np.linalg.norm(np.cross(co[tr[:,1]]-co[tr[:,0]],co[tr[:,2]]-co[tr[:,0]]),axis=1)*.5 if len(tr) else np.zeros(0)
  assert np.isfinite(co).all(),m.name;assert not np.any(ar<1e-14),m.name
  meshrows.append({'mesh':m.name,'vertices':len(co),'triangles':len(tr),'geometry_sha256':hashlib.sha256(co.tobytes()+tr.tobytes()).hexdigest(),'zero_area_triangles':int(np.sum(ar<1e-14))})
 for i in bpy.data.images:
  if i.source!='FILE':continue
  assert i.packed_file is not None,i.name
  image_rows.append({'name':i.name,'packed_bytes':len(i.packed_file.data),'sha256':hashlib.sha256(i.packed_file.data).hexdigest()})
 poses=[]
 if name=='BRANCH_INSPECTION_ANIMATION.blend':
  plan=json.loads((E/'VIDEO_PLAN.json').read_text());mx=0
  for item in plan['poses']:
   s.frame_set(item['frame']);bpy.context.view_layer.update();mat=np.array(s.camera.matrix_world)
   err=float(np.abs(mat-np.array(item['matrix'])).max());assert err<1e-5,(item['frame'],err);mx=max(mx,err)
  poses={'camera_poses_checked':len(plan['poses']),'maximum_matrix_difference':mx}
 rows.append({'scene':name,'sha256':digest(p),'reopened_sha256':digest(copy),'mesh_count':len(meshrows),'mesh_records':meshrows,'images':image_rows,'camera_pose_validation':poses})
 copy.unlink()
# Packed-image test: use a clean copy and force non-existent external image names
# in memory. Only packed bytes can satisfy these image references.
p=R/'PATCH_ASSET_GATE.blend';copy=C/p.name;shutil.copyfile(p,copy);bpy.ops.wm.open_mainfile(filepath=str(copy),load_ui=False,use_scripts=False);s=bpy.context.scene
for im in bpy.data.images:
 if im.source=='FILE':
  assert im.packed_file;im.filepath='//__intentionally_missing_external_texture__/'+im.name
s.render.resolution_x=320;s.render.resolution_y=240;s.render.resolution_percentage=100;s.cycles.samples=16;s.cycles.adaptive_min_samples=16;s.cycles.use_denoising=True
s.render.filepath=str(E/'packed_only_smoke.png');t=time.monotonic();bpy.ops.render.render(write_still=True);copy.unlink()
original=Path('inputs/historical/green_terror_original/GREEN_TERROR.blend');original_sha=digest(original);assert original_sha=='a39d6c6368e8dde7f0cc8eb745962136cf181b7cc2db4359e485ece44ed9ee04'
out={'completed':True,'scope':'Native portability/topology/camera validation, NOT photorealism certification','blender':bpy.app.version_string,'build':bpy.app.build_hash.decode(),'source_forest_unchanged':True,'original_sha256':original_sha,'scenes':rows,'packed_only_smoke':{'completed':True,'external_image_paths_deliberately_invalidated':True,'width':320,'height':240,'seconds':time.monotonic()-t,'file':'evidence/packed_only_smoke.png'},'no_image_generation':True,'peak_rss_mb':peak_rss_mib()}
(E/'PACKED_NATIVE_VALIDATION.json').write_text(json.dumps(out,indent=2));print('PACKED_DELIVERY_VALIDATED',flush=True)
