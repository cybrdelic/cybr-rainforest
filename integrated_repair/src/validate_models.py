"""Validate the actual native checkpoints, not merely the generation scripts."""
import bpy,numpy as np,json,hashlib,sys,time,os,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def validate(path):
 bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
 r={'completed':False,'scene':str(path),'scene_sha256':sha(path),'native_version':bpy.app.version_string,'images':[],'meshes':[],'errors':[]}
 seen=set()
 for im in bpy.data.images:
  if im.source!='FILE':continue
  if not im.packed_file:r['errors'].append('Unpacked texture: '+im.name);continue
  raw=im.packed_file.data;r['images'].append({'name':im.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 for o in bpy.data.objects:
  if o.type!='MESH' or o.data.name in seen:continue
  m=o.data;seen.add(m.name);co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3)
  m.calc_loop_triangles();tri=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',tri);tri=tri.reshape(-1,3)
  area=np.linalg.norm(np.cross(co[tri[:,1]]-co[tri[:,0]],co[tri[:,2]]-co[tri[:,0]]),axis=1)*.5 if len(tri) else np.zeros(0)
  numzero=int(np.sum(area<1e-16));finite=bool(np.isfinite(co).all());hh=hashlib.sha256(co.tobytes()+tri.tobytes()).hexdigest()
  r['meshes'].append({'name':m.name,'vertices':len(co),'triangles':len(tri),'nonfinite':not finite,'zero_area_triangles':numzero,'geometry_sha256':hh})
  if not finite:r['errors'].append('Nonfinite mesh: '+m.name)
  if numzero:r['errors'].append('Degenerate triangles: %s %d'%(m.name,numzero))
 r['mesh_count']=len(r['meshes']);r['total_unique_triangles']=sum(x['triangles'] for x in r['meshes']);r['total_zero_area_triangles']=sum(x['zero_area_triangles'] for x in r['meshes'])
 r['packed_texture_count']=len(r['images']);r['passed']=not r['errors'];r['completed']=True;r['not_claimed']='Technical checks do not prove photorealism, global collisions or biological accuracy.'
 out=ROOT/'evidence'/('validation_'+path.stem+'.json');out.write_text(json.dumps(r,indent=2));print('VALIDATED',path,r['passed'],r['total_zero_area_triangles'],flush=True)
if __name__=='__main__':
 for name in sys.argv[sys.argv.index('--')+1:]:validate(Path(name))
