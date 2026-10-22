# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
import bpy,sys,os,json,time
from pathlib import Path
from collections import Counter
P=Path('inputs/historical/GREEN_TERROR_V11');bpy.ops.wm.open_mainfile(filepath=str(P/'GREEN_TERROR_V11_BUDGETED.blend'),use_scripts=False)
r={'vertices':sum(len(m.vertices) for m in bpy.data.meshes),'faces':sum(len(m.polygons) for m in bpy.data.meshes),'rss':peak_rss_mib()}
print('SOURCE',r,flush=True)
dg=bpy.context.evaluated_depsgraph_get();counts=Counter();roots=Counter();n=0
for i in dg.object_instances:
 n+=1
 if i.object.type=='MESH':counts[i.object.name]+=1
 if i.parent:roots[i.parent.name]+=1
 if n%25000==0:print('COUNT',n,'rss',peak_rss_mib(),flush=True)
r.update(instances=n,counts=counts.most_common(),parents=roots.most_common(),peak=peak_rss_mib())
(P/'evidence/instance_audit.json').write_text(json.dumps(r,indent=2));print('INSTANCE_DONE',n,'peak',r['peak'],flush=True);sys.stdout.flush();os._exit(0)
