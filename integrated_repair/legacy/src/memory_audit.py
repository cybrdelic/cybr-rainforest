# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
import bpy,numpy as np,json
from collections import Counter
bpy.ops.wm.open_mainfile(filepath='inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11.blend',use_scripts=False)
r={'v':sum(len(m.vertices) for m in bpy.data.meshes),'f':sum(len(m.polygons) for m in bpy.data.meshes),'edges':sum(len(m.edges) for m in bpy.data.meshes),'loops':sum(len(m.loops) for m in bpy.data.meshes),'meshes':len(bpy.data.meshes),'mods':[], 'props':[]}
for o in bpy.data.objects:
 for m in o.modifiers:
  if m.type!='NODES':r['mods'].append((o.name,m.type,[(p.identifier,str(getattr(m,p.identifier))) for p in m.bl_rna.properties if p.identifier in ('levels','render_levels','show_render')]))
for p in bpy.context.scene.cycles.bl_rna.properties:
 if any(t in p.identifier for t in ('bvh','memory','texture','compact','spatial')):r['props'].append((p.identifier,p.description,str(getattr(bpy.context.scene.cycles,p.identifier))))
r['rss']=peak_rss_mib();open('inputs/historical/GREEN_TERROR_V11/evidence/memory_audit.json','w').write(json.dumps(r,indent=2));print(r)
