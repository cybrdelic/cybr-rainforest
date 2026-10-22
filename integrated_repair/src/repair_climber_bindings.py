"""Keep the accepted leaf family's proportions and growth habit in the forest.
The earlier adapter used inherited wide generic blade ratios and changed family
per blade. This native integration changes neither the woody host nor root poses.
"""
from pathlib import Path
import bpy,sys,json,random,hashlib,gc,ctypes,re
from collections import Counter
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'legacy/upstream')]
import build_assets as B,repair_geometry as R,apply_v6 as A,climbers
from finalize_models import flat_rims,remove_zero_faces
source=ROOT/'GREEN_TERROR_FOREST_REPAIRED.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
stem=next(m for m in bpy.data.materials if m.name.startswith('GATE | stipules'));vein=next(m for m in bpy.data.materials if m.name.startswith('GATE | raised abaxial'));woody=bpy.data.materials['REPAIR | woody liana bark']
records=[];Z=Vector((0,0,1));cameras={o.name:[list(x) for x in o.matrix_world] for o in bpy.context.scene.objects if o.type=='CAMERA'}
for c in list(bpy.data.collections):
 if not re.fullmatch(r'(Tree|Subcanopy|Emergent) prototype \d+',c.name):continue
 wood=next((o for o in c.objects if o.name.endswith('_wood')),None);old=[o for o in c.objects if 'attached_climbers_and_moss' in o.name]
 if not wood or not old:continue
 if c.name.startswith('Emergent'):
  i=int(c.name[-2:]);height=max(v.co.z for v in wood.data.vertices);rc={'height':height,'radius':height*.01,'seed':90371+i*127,'prefix':wood.name[:-5]}
 else:rc=A.recipe(c.name)
 hero=c.name in ('Tree prototype 08','Tree prototype 02','Subcanopy prototype 02','Subcanopy prototype 03');vine_rows=[]
 class Host(B.Mesh):
  def __init__(self,m):super().__init__('REPAIR | coherent climbers');self.counts=Counter()
  def tube(self,points,radii,key='stem',sides=6):B.tube(self,points,radii,woody if key=='bark_smooth' else stem,sides)
  def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
   sd=int(rng.random()*999999);rr=random.Random(sd);vine=int(self.counts['climbing_stems'])
   fam=('piper','cordate','piper')[(rc['seed']+vine)%3]
   n=B.unit(normal);side=Vector(axis)-n*Vector(axis).dot(n)-Z*Vector(axis).dot(Z)
   side=B.unit(side,n.cross(Z))
   young=key=='leaf_new'
   # Mature blades hang from their petiole; terminal juvenile flushes can rise.
   elevation=rr.uniform(.10,.40) if young else rr.uniform(-.84,-.40)
   direction=B.unit(side*rr.uniform(.48,.75)+Z*elevation+n*rr.uniform(.14,.28))
   face=B.unit(n+side*rr.uniform(-.12,.12))
   ratio=rr.uniform(.63,.71) if fam=='cordate' else rr.uniform(.37,.44)
   B.leaf(self,base,direction,face,length,length*ratio,fam,sd,B.leafmaterial(fam,'young' if young else 'mature'),vein,1 if hero else 0,False,hero)
   vine_rows.append({'vine':vine,'family':fam,'length_m':length,'width_ratio':ratio,'maturity':'young' if young else 'mature','axis_z':direction.z,'petiole_attachment':list(base)})
  def moss(self,*args):pass
  def finish(self,name):self.name='REPAIR | '+name;return super().finish(c)
 previous=climbers.SurfaceMesh;climbers.SurfaceMesh=Host
 try:new=climbers.decorate_tree(rc['prefix'],wood,{},rc['seed'],rc['height'],rc['radius'])[0]
 finally:climbers.SurfaceMesh=previous
 for o in old:
  for col in list(o.users_collection):
   if new.name not in col.objects:col.objects.link(new)
   col.objects.unlink(o)
  bpy.data.objects.remove(o)
 byvine={}
 for row in vine_rows:byvine.setdefault(row['vine'],set()).add(row['family'])
 if not all(len(v)==1 for v in byvine.values()):raise RuntimeError('A vine mixes blade families')
 new['leaf_family_binding']='One family per vine; developmental variation within that family'
 records.append({'host':wood.name,'leaves':vine_rows,'one_family_per_vine':True,'wood_unchanged':True})
 bpy.data.orphans_purge(do_recursive=True);gc.collect();ctypes.CDLL(None).malloc_trim(0)
 print('COHERENT_CLIMBER',wood.name,len(vine_rows),flush=True)
# Preserve the basal family's shape through the juvenile-to-mature sequence;
# rebuild only actual referenced meshes using recorded construction heights.
basal_records=[];done=set();binding=json.loads((ROOT/'evidence/forest_integration.json').read_text())
for row in binding['prototype_bindings']:
 if row['family']!='broadleaf':continue
 for name in row['replacement_objects']:
  if name in done:continue
  done.add(name);old=bpy.data.objects.get(name)
  if old is None:continue
  match=re.search(r'REPAIR \| broadleaf basal plant (\d+)',old.name)
  group=re.search(r'broadleaf prototype (\d+)',row['collection'])
  if not match or not group:continue
  seed=int(match.group(1));fam='cordate' if int(group.group(1))%2==0 else 'piper';height=min(1.3,max(.45,row['original_bounds_height']))
  nc=bpy.data.collections.new('Temporary basal family repair');new=R.basal_plant(nc,stem,vein,seed,height,fam,lod=False);new.matrix_world=old.matrix_world.copy()
  for col in list(old.users_collection):
   col.objects.link(new);col.objects.unlink(old)
  bpy.data.objects.remove(old);nc.objects.unlink(new);bpy.data.collections.remove(nc)
  basal_records.append({'seed':seed,'family':fam,'height_parameter':height,'old_object':name,'new_object':new.name})

if cameras!={o.name:[list(x) for x in o.matrix_world] for o in bpy.context.scene.objects if o.type=='CAMERA'}:raise RuntimeError('Camera changed')
rims=flat_rims();zero=remove_zero_faces();bpy.data.orphans_purge(do_recursive=True)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
 im.buffers_free()
out=ROOT/'GREEN_TERROR_FOREST_LEAF_BINDING_TEST.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
(ROOT/'evidence/climber_binding_review.json').write_text(json.dumps({'completed':True,'source':str(source),'source_sha256':hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),'output':str(out),'scene_sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),'camera_matrices_unchanged':True,'host_records':records,'basal_family_records':basal_records,'rim_repairs':rims,'zero_face_cleanup':zero},indent=2))
