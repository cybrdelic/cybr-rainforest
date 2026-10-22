"""Lossless deduplication: identical fern meshes share the same native datablock."""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr, trim_allocator, enable_cycles_debug
import bpy,numpy as np,json,gc,ctypes,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GREEN_TERROR_V11.blend'),use_scripts=False)
r={'completed':False,'identical_mesh_pairs':[],'removed_selection_attributes':0,'geometry_decimated':False,'instances_removed':False}

def arr(data,key,components,dtype):
    a=np.empty(len(data)*components,dtype);data.foreach_get(key,a);return a

def equal(a,b):
    assert len(a.vertices)==len(b.vertices) and len(a.polygons)==len(b.polygons) and len(a.loops)==len(b.loops)
    for d,key,c,ty in [('vertices','co',3,np.float32),('loops','vertex_index',1,np.int32),('polygons','material_index',1,np.int32),('polygons','use_smooth',1,np.bool_)]:
        assert np.array_equal(arr(getattr(a,d),key,c,ty),arr(getattr(b,d),key,c,ty))
    assert list(a.materials)==list(b.materials)
    for n,key,c in [('gt6_color','color',4),('gt7_anatomical_uv','vector',3),('gt8_wetness','value',1)]:
        assert np.array_equal(arr(a.attributes[n].data,key,c,np.float32),arr(b.attributes[n].data,key,c,np.float32))

for i in range(4):
    a=bpy.data.objects[f'GT11 | fern prototype {i:02d}'];b=bpy.data.objects[f'GT11 | GT7 | fern prototype {i:02d}'];equal(a.data,b.data)
    old=b.data;b.data=a.data;bpy.data.meshes.remove(old);r['identical_mesh_pairs'].append([a.name,b.name])
for me in bpy.data.meshes:
    for at in list(me.attributes):
        if at.name in ('.select_vert','.select_edge','.select_poly'):
            me.attributes.remove(at);r['removed_selection_attributes']+=1
bpy.context.scene.cycles.debug_bvh_type='STATIC_BVH'
bpy.data.orphans_purge(do_recursive=True);gc.collect();trim_allocator()
out=ROOT/'GREEN_TERROR_V11_NATIVE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
with out.open('rb') as f:r['scene_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
r.update(completed=True,peak_MB=peak_rss_mib())
(ROOT/'evidence/lossless_sharing.json').write_text(json.dumps(r,indent=2));print('LOSSLESS_SHARING_DONE',r)
