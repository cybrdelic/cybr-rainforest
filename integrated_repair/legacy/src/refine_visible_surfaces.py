"""Correct the first native QC: excessive ribbing and subpixel attached growth."""
import bpy,sys,os,math,json,random,re,gc,ctypes,hashlib,traceback
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'upstream')]
import morphology_v9 as M,morphology as F,apply_v6 as A,climbers

def main():
 source=ROOT/'GREEN_TERROR_V11_BUDGETED.blend';bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False);F.install()
 Old=F.AnatomicalBlade
 class Adjusted(Old):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs)
   factor={'cordate':.57,'elliptic':.34,'lance':.25,'pinnule':.25}.get(self.shape,.4)
   self.rib_strength*=factor*(.77+.23*self.age)
 M.LeafSurface=Adjusted
 mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')};mats['water']=bpy.data.materials['GT8 | isolated dew lenses'];mats['bark_smooth']=mats['stem']
 report={'completed':False,'input_sha256':hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),'reason':'First actual native QC had overly regular strong rib highlights, while attached microshoots were too small to read at the ground camera.','rebuilt_climbers':[],'rebuilt_basal_plants':[],'colony_scales':[],'relighting':False}
 for name in ('Tree prototype 08','Tree prototype 02','Subcanopy prototype 02','Subcanopy prototype 03'):
  col=bpy.data.collections[name];wood=next(o for o in col.objects if o.name.endswith('_wood'));rc=A.recipe(name);oldobjects=[o for o in col.objects if 'attached_climbers_and_moss' in o.name]
  class Host(M.Mesh):
   def __init__(self,ms):super().__init__('GT11 climber',ms)
   def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
    phase=rng.random();rr=random.Random(int(phase*999999+abs(sum(base))*9277));shape='cordate' if int(phase*10)%3==0 else 'lance' if int(phase*10)%3==1 else 'elliptic'
    M.leaf(self,rr,base,axis,normal,length,width,shape,2,.16 if key=='leaf_new' else .65,damage=.18)
   def moss(self,*a):pass
   def finish(self,name):self.name='GT11B | '+name;return super().finish(col)
  old=climbers.SurfaceMesh;climbers.SurfaceMesh=Host
  try:new=climbers.decorate_tree(rc['prefix'],wood,mats,rc['seed'],rc['height'],rc['radius'])[0]
  finally:climbers.SurfaceMesh=old
  for ob in oldobjects:
   for c in list(ob.users_collection):
    if new.name not in c.objects:c.objects.link(new)
    c.objects.unlink(ob)
   bpy.data.objects.remove(ob)
  report['rebuilt_climbers'].append(A.mesh_record(new));print('REFINED',name,flush=True)
  bpy.data.orphans_purge(do_recursive=True);gc.collect();ctypes.CDLL(None).malloc_trim(0)
 dims={x['collection']:x for x in json.loads((ROOT/'evidence/build.json').read_text())['plants']}
 for col in list(bpy.data.collections):
  m=re.fullmatch(r'GT8 \| broadleaf prototype (\d+) \| architecture (\d+)',col.name)
  if not m:continue
  i,v=map(int,m.groups());mesh=M.Mesh('GT11B | '+col.name,mats);old=list(col.objects);lo,hi=A.bounds(col)
  F.ground_broadleaf(mesh,33731+i*971+v*367,min(1.35,dims[col.name]['prior_height']),i+v)
  new=mesh.finish(col)
  for ob in old:
   col.objects.unlink(ob)
   if not ob.users_collection:bpy.data.objects.remove(ob)
  report['rebuilt_basal_plants'].append(A.mesh_record(new));bpy.data.orphans_purge(do_recursive=True);gc.collect();ctypes.CDLL(None).malloc_trim(0)
 for ob in bpy.data.objects:
  if not ob.name.endswith('microshoot anchors') or ob.type!='MESH':continue
  co=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',co);co=co.reshape(-1,3)
  f=1.6+.75*(.5+.5*np.sin(co[:,0]*3.3+co[:,1]*2.7+co[:,2]*1.1))
  ob.data.attributes['gt11_scale'].data.foreach_set('vector',np.repeat(f[:,None],3,axis=1).ravel());report['colony_scales'].append({'name':ob.name,'min':float(f.min()),'max':float(f.max())})
 for mat in [m for m in bpy.data.materials if m.get('gt11_tissue')]:
  ns=mat.node_tree.nodes;ln=mat.node_tree.links
  for n in ns:
   if n.type=='BUMP' and n.inputs['Distance'].default_value>.0001:n.inputs['Distance'].default_value=.00018
  if mat.name in ('GT9 | leaf','GT7 | leaf'):
   attr=ns.new('ShaderNodeAttribute');attr.attribute_name='gt8_wetness'
   rough=ns.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.18;rough.inputs['From Max'].default_value=.70;rough.inputs['To Min'].default_value=.55;rough.inputs['To Max'].default_value=.36;ln.new(attr.outputs['Fac'],rough.inputs['Value'])
   for n in ns:
    if n.type=='BSDF_PRINCIPLED':ln.new(rough.outputs[0],n.inputs['Roughness'])
 for image in bpy.data.images:
  if image.source=='FILE' and not image.packed_file:image.pack()
 for p in [ROOT/'src/refine_visible_surfaces.py']:
  t=bpy.data.texts.new('GT11_SOURCE/'+p.name);t.write(p.read_text())
 out=ROOT/'GREEN_TERROR_V11_STRUCTURE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
 report.update(completed=True,scene=str(out),scene_sha256=hashlib.file_digest(out.open('rb'),'sha256').hexdigest())
 (ROOT/'evidence/visible_surface_refinement.json').write_text(json.dumps(report,indent=2));print('REFINEMENT_SAVED',out,flush=True)
if __name__=='__main__':
 try:main()
 except BaseException:traceback.print_exc();sys.stdout.flush();os._exit(1)
 sys.stdout.flush();os._exit(0)
