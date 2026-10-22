"""Apply tested branch/fern/contact assets to the retained native rainforest.
Never changes the input file. Swaps referenced prototypes (including the base
families previously missed by the historical chooser-only integrations).
"""
import os,sys,json,hashlib,time,gc,ctypes,re,random
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'legacy/upstream')]
import bpy,numpy as np
from mathutils import Vector
import build_assets as B,repair_geometry as R,climbers,apply_v6 as A
INPUT=Path(os.environ.get('GREEN_TERROR_BASELINE', 'inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend'))

def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def trim():
 gc.collect()
 try:ctypes.CDLL(None).malloc_trim(0)
 except:pass

def controllers():
 result={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or len(o.data.polygons):continue
  h=hashlib.sha256();a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
  for at in o.data.attributes:
   if at.domain=='POINT' and at.data_type=='FLOAT_VECTOR':
    data=np.empty(len(at.data)*3,np.float32);at.data.foreach_get('vector',data);h.update(data.tobytes())
  result[o.name]={'count':len(o.data.vertices),'sha256':h.hexdigest(),'original_count':o.get('gt6_instance_count',0)}
 return result

def replace(col,objs):
 for old in list(col.objects):col.objects.unlink(old)
 for o in objs:
  if o.name not in col.objects:col.objects.link(o)

def bounds(col):
 vals=[o.matrix_world@Vector(v) for o in col.objects if o.type=='MESH' for v in o.bound_box]
 if not vals:return .8,.8
 arr=np.array(vals);return float(np.ptp(arr[:,2])),float(max(np.ptp(arr[:,0]),np.ptp(arr[:,1])))

def fungal_materials():
 changes=[]
 for name in ('Woodland bracket | fungus_cap','Woodland bracket | fungus_pores','GT7 | fungus'):
  m=bpy.data.materials.get(name)
  if not m:continue
  m.use_nodes=True;ns=m.node_tree.nodes;ln=m.node_tree.links;ns.clear()
  out=ns.new('ShaderNodeOutputMaterial');bs=ns.new('ShaderNodeBsdfPrincipled');ln.new(bs.outputs[0],out.inputs['Surface'])
  coord=ns.new('ShaderNodeTexCoord');n=ns.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=26;n.inputs['Detail'].default_value=4;n.inputs['Roughness'].default_value=.68;ln.new(coord.outputs['Object'],n.inputs['Vector'])
  ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.036,.023,.012,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.25,.18,.085,1)
  if 'pores' in name:ramp.color_ramp.elements[0].color=(.12,.093,.055,1);ramp.color_ramp.elements[1].color=(.34,.29,.19,1)
  ln.new(n.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.73
  fine=ns.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=650;fine.inputs['Detail'].default_value=2;ln.new(coord.outputs['Object'],fine.inputs['Vector']);bump=ns.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00027;bump.inputs['Strength'].default_value=.4;ln.new(fine.outputs['Fac'],bump.inputs['Height']);ln.new(bump.outputs['Normal'],bs.inputs['Normal']);changes.append(name)
 return changes

def main():
 start=time.time();bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False);s=bpy.context.scene;s.frame_set(1);s.timeline_markers.clear()
 before=controllers();camera_before={o.name:[list(row) for row in o.matrix_world] for o in s.objects if o.type=='CAMERA'}
 report={'completed':False,'input':str(INPUT),'input_sha256':sha(INPUT),'image_generation_used':False,'scope':'full-stand prototype replacement; native camera and root transforms preserved','prototype_bindings':[],'climbers':[],'litter_clusters':[]}
 (B.EV/'forest_build_started.json').write_text(json.dumps(report,indent=2))
 stem=B.stemmaterial();vein=B.plain('GATE | raised abaxial veins',(.087,.111,.031),.65)
 # Cache replacements by developmental family; use the actual measured old
 # prototype height, not an arbitrary scale increase that enlarges every leaf.
 library={};oldcols=list(bpy.data.collections)
 for c in oldcols:
  fern=re.fullmatch(r'(?:GT7 \| )?fern prototype (\d+)',c.name)
  basal=re.fullmatch(r'(?:GT8 \| )?broadleaf prototype (\d+)(?: \| architecture (\d+))?',c.name)
  shrub=re.fullmatch(r'(?:GT8 \| )?shrub prototype (\d+)(?: \| architecture (\d+))?',c.name)
  mid=re.fullmatch(r'GT9 \| GT7 \| Midstory prototype (\d+) \| growth history (\d+)',c.name)
  if not any((fern,basal,shrub,mid)):continue
  H,W=bounds(c)
  if fern:
   i=int(fern.group(1));key=('fern',i)
   if key not in library:
    nc=bpy.data.collections.new('REPAIR_LIBRARY | fern %d'%i);root=R.fern_meshes(nc,stem,vein,881+i*91,lod=True)
    # Preserve a physically plausible crown span rather than the many-metre
    # recursive prototype bounds inherited by prior patch attempts.
    fac=min(1.65,max(.80,W/1.5));root.scale=(fac,)*3;library[key]=list(nc.objects)
   kind='fern'
  else:
   m=basal or shrub or mid;i=int(m.group(1));v=int(m.group(2) or 0);kind='broadleaf' if basal else 'shrub' if shrub else 'midstory';key=(kind,i,v%2)
   if key not in library:
    nc=bpy.data.collections.new('REPAIR_LIBRARY | %s %d %d'%(kind,i,v%2))
    if basal:o=R.basal_plant(nc,stem,vein,1117+i*97+v*17,min(1.3,max(.45,H)),'cordate' if i%2==0 else 'piper',lod=False)
    else:o=R.rooted_plant(nc,stem,vein,3317+i*97+v*17,min(5.2 if mid else 2.0,max(.8,H)),'cordate' if i%3==0 else 'piper',lod=True)
    library[key]=list(nc.objects)
  replace(c,library[key]);report['prototype_bindings'].append({'collection':c.name,'family':kind,'original_bounds_height':H,'replacement_objects':[o.name for o in library[key]]})
  print('BOUND',c.name,flush=True)
 # Recreate climbing leaves on the same woody supports. Keep all tested moss
 # point-instancing networks rather than turning every shoot into unique mesh.
 for c in oldcols:
  if not re.fullmatch(r'(Tree|Subcanopy|Emergent) prototype \d+',c.name):continue
  wood=next((o for o in c.objects if o.name.endswith('_wood')),None)
  if not wood:continue
  old=[o for o in c.objects if 'attached_climbers_and_moss' in o.name]
  if not old:continue
  if c.name.startswith('Emergent'):
   i=int(c.name[-2:]);height=max(v.co.z for v in wood.data.vertices);rc={'height':height,'radius':height*.01,'seed':90371+i*127,'prefix':wood.name[:-5]}
  else:rc=A.recipe(c.name)
  hero=c.name in ['Tree prototype 08','Tree prototype 02','Subcanopy prototype 02','Subcanopy prototype 03']
  class Host(B.Mesh):
   def __init__(self,materials):super().__init__('REPAIR | climbers');self.counts=Counter()
   def tube(self,points,radii,key='stem',sides=6):
    material=bpy.data.materials.get('Petiole | green woody stems') if key=='bark_smooth' else stem
    B.tube(self,points,radii,material,sides)
   def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
    sd=int(rng.random()*999999);fam='cordate' if sd%3==0 else 'piper';rr=random.Random(sd)
    # Existing lengths, attachment positions, and directions retained.
    B.leaf(self,base,axis,normal,length,width,fam,sd,B.leafmaterial(fam,'young' if key=='leaf_new' else 'mature'),vein,1 if hero else 0,False,hero)
    self.counts['leaves']+=1
   def moss(self,*args):pass
   def finish(self,name):self.name='REPAIR | '+name;return super().finish(c)
  old_class=climbers.SurfaceMesh;climbers.SurfaceMesh=Host
  try:new=climbers.decorate_tree(rc['prefix'],wood,{},rc['seed'],rc['height'],rc['radius'])[0]
  finally:climbers.SurfaceMesh=old_class
  for o in old:
   for collection in list(o.users_collection):
    if new.name not in collection.objects:collection.objects.link(new)
    collection.objects.unlink(o)
   bpy.data.objects.remove(o)
  report['climbers'].append({'host':wood.name,'new':new.name,'vertices':len(new.data.vertices)});print('CLIMBER',wood.name,flush=True)
 # Replace only the inherited large litter prototype groups here. The terrain
 # and older fine fragment fields remain, so no empty ground holes are created.
 for c in oldcols:
  m=re.fullmatch(r'DETAIL \| Litter prototype (\d+)',c.name)
  if not m:continue
  i=int(m.group(1));key=('litter',i%8)
  if key not in library:
   nc=bpy.data.collections.new('REPAIR_LIBRARY | settled litter %d'%(i%8))
   grid=R.SupportGrid(-.17,.17,-.16,.16,100,base_func=lambda x,y:np.zeros_like(x))
   _,rec=R.litter_patch(nc,stem,vein,grid,count=7,seed=4481+(i%8)*61);library[key]=list(nc.objects);report['litter_clusters'].append(rec)
  replace(c,library[key]);print('LITTER',c.name,flush=True)
 report['fungus_materials']=fungal_materials();R.material_adjustments()
 # No lighting/camera substitution in the controlled original-camera outputs.
 bpy.data.orphans_purge(do_recursive=True);trim()
 after=controllers();report['controller_transforms_preserved']=before==after;report['original_placements']=sum(x['original_count'] for x in before.values())
 if before!=after:raise RuntimeError('Placement or support controller geometry changed unexpectedly')
 now={o.name:[list(row) for row in o.matrix_world] for o in s.objects if o.type=='CAMERA'}
 if now!=camera_before:raise RuntimeError('Original camera matrices changed')
 report['camera_matrices_preserved']=True
 for im in bpy.data.images:
  if im.source=='FILE' and not im.packed_file:im.pack()
  im.buffers_free()
 report['packed_images']=len([im for im in bpy.data.images if im.packed_file]);s.camera=bpy.data.objects['04_BARK_AND_LITTER'];s['repair_lineage']='V11 forest + reference-informed asset-gate repair';s.cycles.samples=96
 out=ROOT/'GREEN_TERROR_INTEGRATED_REPAIR.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
 report.update(completed=True,scene=str(out),scene_sha256=sha(out),seconds=time.time()-start,source_unchanged=sha(INPUT)==report['input_sha256'])
 (B.EV/'forest_integration.json').write_text(json.dumps(report,indent=2));print('FOREST_REPAIR_SAVED',out,flush=True)
if __name__=='__main__':main()
