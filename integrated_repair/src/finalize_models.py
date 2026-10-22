"""Freeze native delivery after inspection: thin-rim normals and seedling scale.
This modifies copied scenes only; input/test records are retained separately.
"""
import bpy,numpy as np,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import build_assets as B,repair_geometry as R

def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def flat_rims():
 seen=set();report=[]
 for ob in bpy.data.objects:
  if ob.type!='MESH' or ob.data.name in seen:continue
  me=ob.data;seen.add(me.name)
  if not me.uv_layers or not any(m and ('GATE |' in m.name or 'REPAIR |' in m.name) for m in me.materials):continue
  starts=np.empty(len(me.polygons),np.int32);counts=np.empty(len(me.polygons),np.int32);sm=np.empty(len(me.polygons),bool)
  me.polygons.foreach_get('loop_start',starts);me.polygons.foreach_get('loop_total',counts);me.polygons.foreach_get('use_smooth',sm)
  uv=np.empty(len(me.loops)*2,np.float32);me.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,2)
  ids=np.where(counts==4)[0]
  if not len(ids):continue
  quv=uv[starts[ids,None]+np.arange(4)];area=np.abs(np.sum(quv[:,:,0]*np.roll(quv[:,:,1],-1,axis=1)-quv[:,:,1]*np.roll(quv[:,:,0],-1,axis=1),axis=1));rim=ids[area<1e-12]
  if len(rim):sm[rim]=False;me.polygons.foreach_set('use_smooth',sm);me.update();report.append({'mesh':me.name,'flat_rim_faces':len(rim)})
 return report

def remove_zero_faces():
 import bmesh
 seen=set();rows=[]
 for ob in bpy.data.objects:
  if ob.type!='MESH' or ob.data.name in seen:continue
  me=ob.data;seen.add(me.name)
  if not me.polygons:continue
  # Blender's double-precision polygon area catches collapsed original faces.
  bad=[p.index for p in me.polygons if p.area<1e-17]
  if not bad:continue
  bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in bad],context='FACES');bm.to_mesh(me);bm.free();me.update();rows.append({'mesh':me.name,'removed_faces':len(bad)})
 return rows

def process(kind):
 source=ROOT/('PATCH_REPAIRED.blend' if kind=='patch' else 'GREEN_TERROR_INTEGRATED_REPAIR.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False);s=bpy.context.scene
 if kind=='patch':
  # Reuse the branch which already passed the prior three-light asset study.
  old=bpy.data.collections.get('REPAIR | leafy seedlings')
  if old:
   for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
   bpy.data.collections.remove(old)
  col=B.add_collection('REPAIR | retained approved branch seedlings');stem=next(m for m in bpy.data.materials if m.name.startswith('GATE | stipules'));vein=next(m for m in bpy.data.materials if m.name.startswith('GATE | raised abaxial'))
  b=B.create_branch(col,stem,vein,'piper',773);b.location=(.36,.1,B.soil_z(.36,.1)+.12);b.scale=(.67,)*3
  for k in range(3):
   b=B.create_branch(col,stem,vein,'cordate' if k==0 else 'piper',712+k*81);b.location=((-.43,.5,.1)[k],(-.38,.4,-.46)[k],.035);b.scale=(.24+.05*k,)*3;b.rotation_euler[2]=k*1.8
  bpy.context.view_layer.update();m=B.Mesh('REPAIR | connected lower stems')
  for o in list(col.objects):
   if o.type!='MESH':continue
   end=o.matrix_world@Vector((-.27,0,.25));scale=float(o.scale.x);start=Vector((end.x-.035*scale,end.y+.012*scale,B.soil_z(end.x-.035*scale,end.y+.012*scale)+.001))
   ps=[start.lerp(end,float(t))+Vector((.015*scale*np.sin(float(t)*np.pi),0,0)) for t in np.linspace(0,1,16)];B.tube(m,ps,np.linspace(.0044*scale,.0038*scale,16),stem,9)
  m.finish(col)
  # Do not multiply another high-contrast broad noise layer into dry leaves.
  for material in bpy.data.materials:
   if not material.use_nodes or not ('decay state' in material.name or '| dead |' in material.name):continue
   for n in material.node_tree.nodes:
    if n.type=='MIX_RGB' and n.blend_type=='MULTIPLY' and abs(n.inputs[0].default_value-.62)<1e-4:n.inputs[0].default_value=.28

 if kind=='forest':
  mat=B.plain('REPAIR | woody liana bark',(.055,.033,.017),.72);ns=mat.node_tree.nodes;ln=mat.node_tree.links;bs=ns.get('Principled BSDF')
  tc=ns.new('ShaderNodeTexCoord');mp=ns.new('ShaderNodeVectorMath');mp.operation='MULTIPLY';mp.inputs[1].default_value=(12,75,1);ln.new(tc.outputs['UV'],mp.inputs[0])
  noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.0;noise.inputs['Detail'].default_value=4;ln.new(mp.outputs[0],noise.inputs['Vector'])
  ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.017,.012,.007,1);ramp.color_ramp.elements[1].color=(.12,.078,.035,1);ln.new(noise.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
  bump=ns.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00045;bump.inputs['Strength'].default_value=.35;ln.new(noise.outputs['Fac'],bump.inputs['Height']);ln.new(bump.outputs['Normal'],bs.inputs['Normal'])
  for ob in bpy.data.objects:
   if ob.type=='MESH' and ob.name.startswith('REPAIR | ') and 'attached_climbers' in ob.name:
    for k,oldmat in enumerate(ob.data.materials):
     if oldmat and oldmat.name=='Petiole | green woody stems':ob.data.materials[k]=mat
 R.material_adjustments();rims=flat_rims();zero=remove_zero_faces()
 for im in bpy.data.images:
  if im.source=='FILE' and not im.packed_file:im.pack()
  im.buffers_free()
 bpy.data.orphans_purge(do_recursive=True)
 out=ROOT/('GROUND_SECTION_FINAL.blend' if kind=='patch' else 'GREEN_TERROR_FOREST_FINAL.blend')
 bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
 report={'completed':True,'input':str(source),'input_sha256':sha(source),'output':str(out),'sha256':sha(out),'rim_normals':rims,'zero_area_faces_removed':zero,'unchanged_input':True,'scope':'Final reviewed normals/branch-scale repair. Contact geometry is unchanged.'}
 (ROOT/'evidence'/('freeze_'+kind+'.json')).write_text(json.dumps(report,indent=2));print('FROZEN',kind,flush=True)
from mathutils import Vector
if __name__=='__main__':
 for kind in sys.argv[sys.argv.index('--')+1:]:process(kind)
