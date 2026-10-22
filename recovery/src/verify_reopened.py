import bpy,json,sys,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'GREEN_TERROR_RECONSTRUCTED_BASELINE.blend'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
t=time.time();bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
s=bpy.context.scene
images=[]
for im in bpy.data.images:
 if im.source=='FILE':
  if not im.packed_file:raise RuntimeError('Unpacked active file texture '+im.name)
  images.append({'name':im.name,'packed_bytes':len(im.packed_file.data),'sha256':hashlib.sha256(im.packed_file.data).hexdigest()})
if bpy.data.libraries:raise RuntimeError('External Blender library detected')
roots=sum(o.get('gt6_instance_count',0) for o in s.objects)
cams={o.name:{'matrix':[list(row) for row in o.matrix_world],'lens':o.data.lens} for o in s.objects if o.type=='CAMERA'}
assert '04_BARK_AND_LITTER' in cams and '02_ROOTS_AND_UNDERSTORY' in cams
r={'completed':True,'native_reopened':True,'scene':str(p),'scene_sha256':sha(p),'scene_bytes':p.stat().st_size,'native_version':bpy.app.version_string,'native_build':bpy.app.build_hash.decode(),'packed_images':images,'packed_image_count':len(images),'external_blend_libraries':len(bpy.data.libraries),'original_planting_root_count':roots,'comparison_cameras':cams,'seconds':time.time()-t,'scope':'Input integrity and reopen/portability check; not a V14 build or visual-quality approval'}
(ROOT/'evidence/NATIVE_REOPEN.json').write_text(json.dumps(r,indent=2));print('REOPENED_OK',len(images),roots,flush=True)
