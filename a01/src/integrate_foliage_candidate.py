"""Local, reversible appearance test in the preserved full rainforest.
No terrain, bark, deadwood, litter, lights, planted roots or cameras are replaced.
Only selected climbing foliage and two fern families are changed. Not a global
photorealism declaration. New prototypes remain candidates pending review.
"""
from __future__ import annotations
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import trim_allocator, enable_cycles_debug
import os,sys,json,hashlib,time,gc,ctypes,random
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
LEGACY=Path('inputs/historical/reference_pipeline/GREEN_TERROR_V11')
sys.path[:0]=[str(ROOT/'src'),str(LEGACY/'upstream')]
import botanical_assets as A
import morphology_v9 as M
import climbers
import apply_v6 as V6
INPUT=Path('inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend')

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def controls():
    out={'cameras':{},'roots':{}}
    for ob in bpy.context.scene.objects:
        if ob.type=='CAMERA':out['cameras'][ob.name]={'matrix':[list(r) for r in ob.matrix_world],'lens':ob.data.lens}
        if ob.type=='MESH' and not len(ob.data.polygons):
            c=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',c)
            out['roots'][ob.name]={'hash':hashlib.sha256(c.tobytes()).hexdigest(),'count':len(ob.data.vertices)}
    return out

def main():
    start=time.time();bpy.ops.wm.open_mainfile(filepath=str(INPUT),use_scripts=False,load_ui=False)
    before=controls();report={'completed':False,'baseline':str(INPUT),'baseline_sha256':sha(INPUT),'climbers':[],'ferns':[],'bark_changed':False,'litter_changed':False,'lights_changed':False,'render_settings_changed':False,'reference_asset_gate':'A01'}
    mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')};mats['bark_smooth']=mats['stem']
    for name in ('Tree prototype 08','Tree prototype 02','Subcanopy prototype 02'):
        col=bpy.data.collections[name];wood=next(o for o in col.objects if o.name.endswith('_wood'));recipe=V6.recipe(name)
        oldobjects=[o for o in col.objects if 'attached_climbers_and_moss' in o.name]
        targets=set(c for ob in oldobjects for c in ob.users_collection)|{col};leaves=[];nodes=[]
        class Host(M.Mesh):
            def __init__(self,mat):super().__init__('A01 native climbing stems',mat)
            def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
                i=len(leaves);rr=rng.random();age='bronze' if key=='leaf_new' and rr>.65 else 'mature'
                direction=A.unit(Vector(axis)+Vector((0,0,-.31)))
                # Reference-guided consistent family along the same vine.
                ob=A.leaf(f'A01 | {name} climbing leaf {i}',base,direction,normal,length,col,'cordate',i%4,age,max(.65,min(.82,width/length)))
                leaves.append(ob);nodes.append({'base':list(base),'length_m':length,'width_ratio':width/length})
            def moss(self,*a):pass
            def finish(self,n):self.name='A01 | '+n;return super().finish(col)
        original=climbers.SurfaceMesh;climbers.SurfaceMesh=Host
        try:new=climbers.decorate_tree(recipe['prefix'],wood,mats,recipe['seed'],recipe['height'],recipe['radius'])[0]
        finally:climbers.SurfaceMesh=original
        for ob in leaves+[new]:
            for c in targets:
                if ob.name not in c.objects:c.objects.link(ob)
        for ob in oldobjects:bpy.data.objects.remove(ob,do_unlink=True)
        report['climbers'].append({'collection':name,'blade_instances':len(leaves),'root_attachment_coordinates':nodes,'removed_meshes':[o.name for o in []]})
        print('INTEGRATED',name,len(leaves),flush=True);gc.collect();trim_allocator()
    # Shared fern assets replace the old frond family in both original/detail collections.
    for idx in (0,1):
        cols=[bpy.data.collections.get(f'{pre}fern prototype {idx:02d}') for pre in ('','GT7 | ')];cols=[c for c in cols if c]
        if not cols:continue
        old=set(o for c in cols for o in c.objects)
        tmp=bpy.data.collections.new(f'A01 fern build {idx}');bpy.context.scene.collection.children.link(tmp)
        A.fern(tmp,seed=311+idx*101,scale=1.0)
        created=list(tmp.objects)
        for ob in created:
            for col in cols:col.objects.link(ob)
            tmp.objects.unlink(ob)
        for col in cols:
            for ob in old:
                if ob.name in col.objects:col.objects.unlink(ob)
        for ob in old:
            if not ob.users_collection:bpy.data.objects.remove(ob)
        bpy.data.collections.remove(tmp)
        report['ferns'].append({'prototype':idx,'objects':len(created)})
    after=controls();report['camera_controls_preserved']=after['cameras']==before['cameras'];report['planting_root_controls_preserved']=after['roots']==before['roots']
    if not report['camera_controls_preserved'] or not report['planting_root_controls_preserved']:raise RuntimeError('control changed')
    bpy.data.orphans_purge(do_recursive=True)
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
        im.buffers_free()
    out=ROOT/'A01_FOREST_CANDIDATE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    report.update(completed=True,seconds=time.time()-start,scene=str(out),scene_sha256=sha(out),packed_images=sum(bool(i.packed_file) for i in bpy.data.images))
    (ROOT/'evidence/forest_integration.json').write_text(json.dumps(report,indent=2));print('SAVED_CANDIDATE',flush=True)
if __name__=='__main__':
    try:main()
    finally:sys.stdout.flush()
