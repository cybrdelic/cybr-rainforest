"""Full-resolution frond templates instantiated within original fern crowns."""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr, trim_allocator, enable_cycles_debug
import bpy,sys,os,json,math,random,gc,ctypes,traceback,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'upstream')]
import morphology_v9 as M,morphology as F,apply_v6 as A
Z=M.Z

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GREEN_TERROR_V11_INSTANCED.blend'),use_scripts=False);F.install()
    mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')};mats['water']=bpy.data.materials['GT8 | isolated dew lenses'];mats['bark_smooth']=mats['stem']
    targets=[]
    for c in list(bpy.data.collections):
        if c.name.startswith(('fern prototype','GT7 | fern prototype')):
            lo,hi=A.bounds(c);targets.append((c,float(max(hi[:2]-lo[:2])),float(lo[2]),int(c.name[-2:])))
            for o in list(c.objects):
                c.objects.unlink(o)
                if not o.users_collection:bpy.data.objects.remove(o)
    bpy.data.orphans_purge(do_recursive=True);gc.collect();trim_allocator()
    library=bpy.data.collections.new('GT11 | shared detailed fronds');objects=[]
    for i in range(8):
        rng=random.Random(13897+i*237);m=M.Mesh('GT11 detailed frond form '+str(i),mats);d=Vector((1,0,0));side=Vector((0,1,0));L=1.;rise=.39+.043*(i%5)
        def center(t):return d*L*t+side*L*.021*math.sin(t*4+i)+Z*(.028+L*(rise*math.sin(t*math.pi*.76)-.11*t*t))
        ts=np.linspace(0,1,38);m.tube([center(t) for t in ts],[.0041*(1-.955*t) for t in ts],'stem',6,(.031,.052,.012))
        count=19+i%3
        for j in range(count):
            t=.09+.86*j/count
            for sign in (-1,1):
                tt=min(.97,t+rng.uniform(-.008,.008));root=center(tt);axis=M.unit(side*sign+d*.28+Z*rng.uniform(-.04,.05));PL=.25*math.sin(math.pi*tt)**.8*rng.uniform(.9,1.06);end=root+axis*PL-Z*PL*.17
                m.tube([root,root.lerp(end,.5)+Z*.015,end],[.00075,.00043,.00010],'vein',4,(.04,.062,.017))
                if i%4==2:
                    M.leaf(m,rng,root,axis,Z,PL,PL*.22,'pinnule',1,.6,damage=.02,veins=False)
                else:
                    for k in range(1,8):
                        u=k/8;q=root.lerp(end,u)
                        for sg in (-1,1):
                            ax=M.unit(axis*.38+d*sg*.9+Z*.12);ln=PL*.28*math.sin(math.pi*u)**.7
                            M.leaf(m,rng,q,ax,Z,ln,ln*.39,'pinnule',0,rng.uniform(.48,.75),damage=0,veins=False)
        ob=m.finish(library);objects.append(ob);print('FROND_TEMPLATE',i,len(ob.data.vertices),flush=True)
    rep=[]
    for c,width,z,i in targets:
        rr=random.Random(4387+i*917);scale=width/2.25;ph=rr.random()*math.tau
        for j in range(9+(i%3)):
            src=objects[(j+i*2)%8];ob=bpy.data.objects.new('GT11 '+c.name+' frond '+str(j),src.data);c.objects.link(ob);ob.rotation_euler.z=ph+j*2.39996+rr.uniform(-.13,.13);q=scale*rr.uniform(.68,1.05);ob.scale=(q,q,q);ob.location.z=z
        rep.append({'collection':c.name,'instanced_fronds':9+i%3,'original_width':width})
    # Frond source objects can be unlinked from the scene; their meshes remain
    # referenced by explicit crown objects. Library owns no visible scene objects.
    for o in objects:
        library.objects.unlink(o)
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(library);bpy.data.orphans_purge(do_recursive=True)
    bpy.context.scene.cycles.debug_bvh_type='DYNAMIC_BVH'
    gc.collect();trim_allocator()
    out=ROOT/'GREEN_TERROR_V11_RENDER.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    report={'completed':True,'scene_sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),'frond_template_count':8,'fern_crowns':rep,'original_forest_placements_removed':0,'representation_changed':True,'no_render_geometry_culling':True,'peak_MB':peak_rss_mib()}
    (ROOT/'evidence/frond_instancing.json').write_text(json.dumps(report,indent=2));print('FROND_FACTORIZATION_DONE')
if __name__=='__main__':
    try:main()
    except BaseException:traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
