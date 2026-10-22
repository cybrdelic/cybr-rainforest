import bpy,json,os,resource
from collections import Counter
p='inputs/historical/GREEN_TERROR_V9/GREEN_TERROR_V9_STREAMING.blend'
bpy.ops.wm.open_mainfile(filepath=p,load_ui=False,use_scripts=False)
s=bpy.context.scene
r={'version':bpy.app.version_string,'cameras':[],'images':[],'objects':[],'collections':[],'materials':[],'counts':{'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes)}}
for c in bpy.data.collections:
 r['collections'].append({'name':c.name,'objects':[x.name for x in c.objects],'children':[x.name for x in c.children]})
for o in bpy.data.objects:
 if o.type=='CAMERA':r['cameras'].append({'name':o.name,'matrix':[list(v) for v in o.matrix_world],'lens':o.data.lens})
 if o.type=='MESH':r['objects'].append({'name':o.name,'mesh':o.data.name,'v':len(o.data.vertices),'faces':len(o.data.polygons),'materials':[m.name if m else None for m in o.data.materials],'attrs':[a.name for a in o.data.attributes],'collections':[c.name for c in o.users_collection]})
for i in bpy.data.images:r['images'].append({'name':i.name,'path':i.filepath,'packed':bool(i.packed_file)})
for m in bpy.data.materials:
 r['materials'].append({'name':m.name,'nodes':[(n.name,n.type) for n in m.node_tree.nodes] if m.use_nodes else []})
r['rss']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
r['scene']={'camera':s.camera.name,'world':s.world.name,'exposure':s.view_settings.exposure,'look':s.view_settings.look,'samples':s.cycles.samples}
open('inputs/historical/GREEN_TERROR_V11/evidence/scene_inventory.json','w').write(json.dumps(r,indent=2))
print('INSPECT_DONE',r['counts'],r['rss'],flush=True)
