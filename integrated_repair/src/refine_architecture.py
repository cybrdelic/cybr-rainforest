"""Replace actual referenced rooted meshes, not orphaned library names."""
import bpy,sys,re,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import build_assets as B,repair_geometry as R
from finalize_models import flat_rims,remove_zero_faces
source=ROOT/'GREEN_TERROR_FOREST_FINAL.blend';bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False,load_ui=False)
stem=next(m for m in bpy.data.materials if m.name.startswith('GATE | stipules'));vein=next(m for m in bpy.data.materials if m.name.startswith('GATE | raised abaxial'))
rows=[]
for old in list(bpy.data.objects):
 match=re.search(r'REPAIR \| rooted (piper|cordate) plant (\d+)',old.name)
 if old.type!='MESH' or not match:continue
 fam,sd=match.groups();seed=int(sd);H=max(v.co.z for v in old.data.vertices)
 nc=bpy.data.collections.new('REPAIR temporary graph builder');ob=R.rooted_plant(nc,stem,vein,seed,H,fam,lod=True)
 users=list(old.users_collection)
 for c in users:
  if ob.name not in c.objects:c.objects.link(ob)
  c.objects.unlink(old)
 bpy.data.objects.remove(old);nc.objects.unlink(ob);bpy.data.collections.remove(nc)
 rows.append({'collections':[c.name for c in users],'height':H,'seed':seed,'graph_nodes':ob['repair_branch_graph_nodes'],'vertices':len(ob.data.vertices)})
 print('GRAPH_REBUILT',ob.name,ob['repair_branch_graph_nodes'],flush=True)
if not rows:raise RuntimeError('No actual referenced meshes were rebuilt')
R.material_adjustments();rims=flat_rims();zero=remove_zero_faces();bpy.data.orphans_purge(do_recursive=True)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
 im.buffers_free()
out=ROOT/'GREEN_TERROR_FOREST_REPAIRED.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
(ROOT/'evidence/branch_graph_repair.json').write_text(json.dumps({'completed':True,'source':str(source),'output':str(out),'sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),'plants':rows,'rim_repairs':rims,'zero_face_cleanup':zero},indent=2))
