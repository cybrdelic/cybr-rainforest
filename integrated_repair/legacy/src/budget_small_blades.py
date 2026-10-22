"""Budget small-leaf surface tessellation; keep new branching and hero laminae.

This is a lower geometric LOD for small shrub/midstory blades, NOT removal of
plants, branches, detail fields, large leaves, or background forest geometry.
"""
import bpy,sys,os,json,traceback,random,re,hashlib,gc,ctypes,resource
from pathlib import Path
from functools import lru_cache
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'upstream')]
import morphology_v9 as M,morphology as F,apply_v6 as A

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GREEN_TERROR_V11_RENDER.blend'),use_scripts=False);F.install()
    oldtop=M.regular_topology
    @lru_cache(maxsize=3)
    def lod(d):
        if d>=2:return oldtop(d)
        nr,nc=(12,6) if d else (6,2)
        co=[(i/nr,-1+2*j/nc) for i in range(nr+1) for j in range(nc+1)];fs=[]
        for i in range(nr):
            for j in range(nc):a=i*(nc+1)+j;b=a+nc+1;fs.append((a,b,b+1,a+1))
        boundary=list(range(nc+1))+[i*(nc+1)+nc for i in range(1,nr+1)]+[nr*(nc+1)+j for j in range(nc-1,-1,-1)]+[i*(nc+1) for i in range(nr-1,0,-1)]
        return co,fs,boundary
    M.regular_topology=lod
    mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')};mats['water']=bpy.data.materials['GT8 | isolated dew lenses'];mats['bark_smooth']=mats['stem']
    # Reuse the *original V9-derived dimensions* so this is not cumulative growth.
    initial=json.loads((ROOT/'evidence/build.json').read_text());dims={x['collection']:x for x in initial['plants']}
    report={'completed':False,'full_forest_retained':True,'hero_leaf_grid_unchanged':[64,22],'small_leaf_grids':{'midstory':[6,2],'shrub':[12,6]},'replacements':[]}
    for col in list(bpy.data.collections):
        small=re.fullmatch(r'GT8 \| shrub prototype (\d+) \| architecture (\d+)',col.name);mid=re.fullmatch(r'GT9 \| GT7 \| Midstory prototype (\d+) \| growth history (\d+)',col.name)
        if not(small or mid):continue
        i,v=map(int,(small or mid).groups());d=dims[col.name];lo,hi=A.bounds(col);m=M.Mesh('GT11 | '+col.name,mats)
        if small:F.understory(m,33731+i*971+v*367,min(2.8,d['prior_height']),i+v)
        else:F.architectural_tree(m,847311+i*977+v*281,d['prior_height'],d['prior_xy_radius'],i+v)
        previous=list(col.objects);before=sum(len(o.data.vertices) for o in previous if o.type=='MESH');new=m.finish(col)
        for ob in previous:
            col.objects.unlink(ob)
            if not ob.users_collection:bpy.data.objects.remove(ob)
        bpy.data.orphans_purge(do_recursive=True);gc.collect();ctypes.CDLL(None).malloc_trim(0)
        report['replacements'].append({'collection':col.name,'before_vertices':before,'after_vertices':len(new.data.vertices),'counted_structures':dict(m.counts)})
        print('SMALL_BLADE_BUDGET',col.name,before,len(new.data.vertices),flush=True)
    bpy.context.scene.cycles.debug_bvh_layout='BVH2';bpy.context.scene.cycles.debug_use_compact_bvh=True
    out=ROOT/'GREEN_TERROR_V11_BUDGETED.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    report.update(completed=True,scene_sha256=hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),peak_MB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    (ROOT/'evidence/small_blade_budget.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':
    try:main()
    except BaseException:traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
