"""Check final native scene contracts against the exact retained forest input."""
import argparse,hashlib,json,sys,gc
from pathlib import Path
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def serial(value):
 if isinstance(value,(str,int,float,bool,type(None))):return value
 try:return [serial(x) for x in value]
 except TypeError:return str(value)
def matrix(o):return [list(row) for row in o.matrix_world]
def nodes(tree):
 if not tree:return None
 return {'nodes':[{'name':n.name,'type':n.bl_idname,'inputs':[(i.identifier,serial(i.default_value)) for i in n.inputs if hasattr(i,'default_value')]} for n in tree.nodes],
         'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in tree.links]}
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
 s=bpy.context.scene;s.frame_set(1)
 d={'controllers':{},'cameras':{},'lights':{},'wood_coordinates':{},'world':nodes(s.world.node_tree) if s.world else None,'display':{k:getattr(s.view_settings,k) for k in ('view_transform','look','exposure','gamma')}}
 for o in s.objects:
  if o.type=='CAMERA':d['cameras'][o.name]={'matrix':matrix(o),'lens':o.data.lens,'sensor_width':o.data.sensor_width,'sensor_height':o.data.sensor_height,'shift_x':o.data.shift_x,'shift_y':o.data.shift_y,'sensor_fit':o.data.sensor_fit}
  if o.type=='LIGHT':d['lights'][o.name]={'matrix':matrix(o),'type':o.data.type,'energy':o.data.energy,'color':list(o.data.color),'nodes':nodes(o.data.node_tree),'angle':getattr(o.data,'angle',None)}
  if o.type!='MESH' or len(o.data.polygons):continue
  h=hashlib.sha256();co=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',co);h.update(co.tobytes())
  attrs={}
  for at in o.data.attributes:
   if at.domain=='POINT' and at.data_type=='FLOAT_VECTOR':
    v=np.empty(len(at.data)*3,np.float32);at.data.foreach_get('vector',v);attrs[at.name]=hashlib.sha256(v.tobytes()).hexdigest()
  d['controllers'][o.name]={'matrix':matrix(o),'points':len(o.data.vertices),'position_sha256':h.hexdigest(),'vector_attributes':attrs,'original_count':o.get('gt6_instance_count',0)}
 for o in bpy.data.objects:
  if o.type=='MESH' and o.name.endswith('_wood'):
   co=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',co)
   d['wood_coordinates'][o.name]={'vertices':len(o.data.vertices),'sha256':hashlib.sha256(co.tobytes()).hexdigest()}
 return d

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--scene',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 baseline=snapshot(a.baseline);gc.collect();final=snapshot(a.scene)
 checks={k:baseline[k]==final[k] for k in baseline}
 bindings=json.loads((ROOT/'evidence/forest_integration.json').read_text())
 missing=[]
 for row in bindings['prototype_bindings']:
  col=bpy.data.collections.get(row['collection'])
  if col is None or not len(col.objects):missing.append(row['collection'])
 checks['all_replaced_collections_nonempty']=not missing
 checks['no_linked_external_blend_libraries']=len(bpy.data.libraries)==0
 checks['all_file_images_packed']=all(im.packed_file is not None for im in bpy.data.images if im.source=='FILE')
 graphs=[]
 for o in bpy.data.objects:
  if 'repair_branch_graph' not in o:continue
  graph=json.loads(o['repair_branch_graph']);ids={n['id'] for n in graph}
  legal=all(n.get('parent') is None or n['parent'] in ids and n['parent']!=n['id'] for n in graph)
  # Parent references must terminate at a root rather than a cycle.
  parents={n['id']:n.get('parent') for n in graph}
  for child in ids:
   seen=set();node=child
   while node is not None:
    if node in seen:legal=False;break
    seen.add(node);node=parents.get(node)
  graphs.append({'object':o.name,'nodes':len(graph),'valid_hierarchy':legal})
 checks['all_graphs_are_rooted_acyclic']=bool(graphs) and all(x['valid_hierarchy'] for x in graphs)
 original_count=sum(x['original_count'] for x in final['controllers'].values())
 checks['original_root_count_18940']=original_count==18940
 r={'completed':True,'passed':all(checks.values()),'baseline':str(a.baseline),'baseline_sha256':sha(a.baseline),'scene':str(a.scene),'scene_sha256':sha(a.scene),'checks':checks,'original_planting_roots':original_count,'controller_meshes':len(final['controllers']),'plant_graphs':graphs,'missing_replaced_collections':missing,'scope':'Final saved native data, not visual quality or complete global collisions.'}
 (ROOT/'evidence/final_scene_contract.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='plant_graphs'},indent=2),flush=True)
 if not r['passed']:raise RuntimeError('A final scene contract failed; inspect recorded checks.')
if __name__=='__main__':main()
