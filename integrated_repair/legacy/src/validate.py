"""Reopen candidate and compare original stand/camera/light controls to baseline."""
import bpy,sys,os,json,hashlib,resource,gc,ctypes
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def capture():
 points={};camera={};lights={}
 for ob in bpy.context.scene.objects:
  if ob.type=='CAMERA':camera[ob.name]={'matrix':[list(v) for v in ob.matrix_world],'lens':ob.data.lens}
  if ob.type=='LIGHT':lights[ob.name]={'matrix':[list(v) for v in ob.matrix_world],'energy':ob.data.energy,'color':list(ob.data.color),'type':ob.data.type}
  if ob.type=='MESH' and len(ob.data.polygons)==0 and ob.data.attributes.get('gt6_rotation'):
   h=hashlib.sha256();a=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',a);h.update(a.tobytes())
   for name in ('gt6_rotation','gt6_scale'):
    v=ob.data.attributes.get(name)
    if v:a=np.empty(len(v.data)*3,np.float32);v.data.foreach_get('vector',a);h.update(a.tobytes())
   points[ob.name]={'sha256':h.hexdigest(),'count':ob.get('gt6_instance_count',0),'vertices':len(ob.data.vertices),'matrix':[list(v) for v in ob.matrix_world]}
 s=bpy.context.scene
 world=[{'name':n.name,'strength':float(n.inputs['Strength'].default_value),'color':list(n.inputs['Color'].default_value)} for n in s.world.node_tree.nodes if n.type=='BACKGROUND']
 return {'points':points,'cameras':camera,'lights':lights,'world':world,'exposure':s.view_settings.exposure,'look':s.view_settings.look}
def main():
 baseline=ROOT/'BASELINE_RELINKED.blend';model=ROOT/'GREEN_TERROR_V11_STRUCTURE.blend'
 bpy.ops.wm.open_mainfile(filepath=str(baseline),use_scripts=False,load_ui=False);before=capture()
 bpy.ops.wm.read_factory_settings(use_empty=True);gc.collect();ctypes.CDLL(None).malloc_trim(0)
 bpy.ops.wm.open_mainfile(filepath=str(model),use_scripts=False,load_ui=False);after=capture()
 checks={k:before[k]==after[k] for k in before}
 images=[]
 for im in bpy.data.images:
  if im.source!='FILE' or not im.users:continue
  packed=im.packed_file is not None;images.append({'name':im.name,'packed':packed,'sha256':hashlib.sha256(im.packed_file.data).hexdigest() if packed else None})
 checks['all_used_file_images_packed']=all(i['packed'] for i in images)
 geometry=[];finite=True
 for me in bpy.data.meshes:
  a=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',a);f=bool(np.isfinite(a).all());finite&=f
  geometry.append({'name':me.name,'vertices':len(me.vertices),'polygons':len(me.polygons),'finite':f})
 checks['finite_coordinates']=finite
 r={'completed':True,'passed':all(checks.values()),'checks':checks,'scene':str(model),'scene_sha256':sha(model),'baseline_sha256':sha(baseline),'baseline_revision':'Preserved V9 checkpoint, texture paths repaired','original_placements':sum(i['count'] for i in after['points'].values()),'native_version':bpy.app.version_string,'native_build':bpy.app.build_hash.decode(),'packed_images':images,'meshes':geometry,'static_frame':bpy.context.scene.frame_current,'animation_verified':False,'peak_rss_mb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
 (ROOT/'evidence/native_reopen.json').write_text(json.dumps(r,indent=2));print('NATIVE_REOPEN',r['passed'],checks,flush=True)
 if not r['passed']:raise AssertionError('Reopen validation failed')
if __name__=='__main__':
 try:main()
 except BaseException:
  import traceback;traceback.print_exc();sys.stdout.flush();os._exit(1)
 sys.stdout.flush();os._exit(0)
