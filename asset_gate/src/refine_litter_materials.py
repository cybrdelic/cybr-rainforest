"""Native dry-lamina look-development variant; no geometry or contacts moved.
Reduces exaggerated microscopic relief, keeps the authored six decay tints,
and separates the thin rim's normals from the broad blade surfaces.
"""
from pathlib import Path
import bpy,numpy as np,json,hashlib
R=Path(__file__).resolve().parents[1];source=R/'PATCH_ASSET_GATE.blend';bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False,load_ui=False)
ob=bpy.data.objects['GATE | rigidly settled curled litter'];me=ob.data;tints=[(.65,.58,.47),(1.15,.97,.65),(.87,.95,.83),(1.28,1.02,.80),(.70,.66,.63),(.94,.74,.51)];changes=[]
for slot,mat in enumerate(list(me.materials)):
 if 'thin lamina' not in mat.name and 'decay state' not in mat.name:continue
 if mat.get('gate_dry_paper',False):continue
 new=mat.copy();new.name=mat.name+' | dry-paper refinement';new['gate_dry_paper']=True;me.materials[slot]=new;ns=new.node_tree.nodes;ln=new.node_tree.links
 tint=tints[int(mat.name.split('decay state ')[1].split()[0])] if 'decay state' in mat.name else (1.03,1.03,1.03)
 bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');sourcecol=bs.inputs['Base Color'].links[0].from_socket
 mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.62;mix.inputs[2].default_value=(.056*tint[0],.030*tint[1],.014*tint[2],1);ln.new(sourcecol,mix.inputs[1]);ln.new(mix.outputs[0],bs.inputs['Base Color'])
 for n in ns:
  if n.type=='BSDF_TRANSLUCENT':ln.new(mix.outputs[0],n.inputs['Color'])
  if n.type=='BUMP':n.inputs['Distance'].default_value*=.20;n.inputs['Strength'].default_value*=.7
 bs.inputs['Specular IOR Level'].default_value=.24
 changes.append(new.name)
starts=np.empty(len(me.polygons),np.int32);counts=np.empty(len(me.polygons),np.int32);sm=np.empty(len(me.polygons),bool)
me.polygons.foreach_get('loop_start',starts);me.polygons.foreach_get('loop_total',counts);me.polygons.foreach_get('use_smooth',sm)
uv=np.empty(len(me.loops)*2,np.float32);me.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,2)
ids=np.where(counts==4)[0];q=uv[starts[ids,None]+np.arange(4)];area=np.abs(np.sum(q[:,:,0]*np.roll(q[:,:,1],-1,axis=1)-q[:,:,1]*np.roll(q[:,:,0],-1,axis=1),axis=1));rim=ids[area<1e-12];sm[rim]=False;me.polygons.foreach_set('use_smooth',sm);me.update()
out=R/'PATCH_DRY_LAMINA_CANDIDATE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
(R/'evidence/DRY_LAMINA_VARIANT.json').write_text(json.dumps({'completed':True,'input':str(source),'input_sha256':hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),'output':str(out),'sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),'modified_materials':changes,'flat_rim_faces':len(rim),'vertex_positions_changed':False,'litter_contacts_changed':False,'look_is_authored_not_measured':True},indent=2))
