"""Factor millimetric moss into shared native geometry; retain full forest.

The macro-habitat field is continuous on each host. Shared microshoots have sixteen
seeded forms. Host thalli, crusts and lifted bark remain individually projected.
This is an authored representation change, not a lossless geometry claim.
"""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr, trim_allocator, enable_cycles_debug
import bpy,sys,os,json,math,random,hashlib,gc,ctypes,traceback
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'upstream')]
import morphology_v9 as M,morphology as F,surfaces as H,apply_v6 as A
Z=M.Z

def batch(col,rows,owner,name):
    pos=[];rot=[];sc=[]
    for p,n,a in rows:
        _,x,y=M.frame(n,Z);mat=Matrix((x,y,n)).transposed();q=mat.to_quaternion()@Quaternion(Z,a)
        pos.append(tuple(p+n*.0004));rot.append(tuple(q.to_euler()));sc.append((1,1,1))
    me=bpy.data.meshes.new(name);me.from_pydata(pos,[],[])
    for key,val in [('rotation',rot),('scale',sc)]:me.attributes.new('gt11_'+key,'FLOAT_VECTOR','POINT').data.foreach_set('vector',np.asarray(val,np.float32).ravel())
    ob=bpy.data.objects.new(name,me);owner.objects.link(ob)
    ng=bpy.data.node_groups.new(name+' instancer','GeometryNodeTree');ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    ns=ng.nodes;ln=ng.links;inp=ns.new('NodeGroupInput');out=ns.new('NodeGroupOutput');ci=ns.new('GeometryNodeCollectionInfo');ci.inputs['Collection'].default_value=col;ci.inputs['Separate Children'].default_value=True;ci.inputs['Reset Children'].default_value=True
    inst=ns.new('GeometryNodeInstanceOnPoints');inst.inputs['Pick Instance'].default_value=True;ln.new(inp.outputs[0],inst.inputs['Points']);ln.new(ci.outputs['Instances'],inst.inputs['Instance'])
    index=ns.new('GeometryNodeInputIndex');mod=ns.new('ShaderNodeMath');mod.operation='MODULO';mod.inputs[1].default_value=16;ln.new(index.outputs[0],mod.inputs[0]);ln.new(mod.outputs[0],inst.inputs['Instance Index'])
    for key,sock in [('rotation','Rotation'),('scale','Scale')]:n=ns.new('GeometryNodeInputNamedAttribute');n.data_type='FLOAT_VECTOR';n.inputs['Name'].default_value='gt11_'+key;ln.new(n.outputs['Attribute'],inst.inputs[sock])
    ln.new(inst.outputs[0],out.inputs[0]);ob.modifiers.new('Shared connected microshoots','NODES').node_group=ng
    return ob

def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GREEN_TERROR_V11_NATIVE.blend'),use_scripts=False);F.install()
    mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')};mats['water']=bpy.data.materials['GT8 | isolated dew lenses'];mats['bark_smooth']=mats['stem']
    library=bpy.data.collections.new('GT11 | shared moss shoot library')
    for i in range(16):
        rng=random.Random(91378+i*167);m=M.Mesh('GT11 microshoot form '+str(i),mats)
        d=M.hv(rng.random()*math.tau);lng=rng.uniform(.025,.06)
        pts=[d*lng*(t-.3)+Vector((0,.003*math.sin(t*7),.0005)) for t in np.linspace(0,1,7)];m.tube(pts,.00045,'moss',4,(.036,.043,.012))
        for k in range(3+(i%2)):
            p=pts[1+k];axis=M.unit(Z*.86+M.hv(i+k*2.39)*.25);height=rng.uniform(.007,.017);tip=p+axis*height
            m.tube([p,p.lerp(tip,.5),tip],[.0003,.0002,.00008],'moss',3,(.033,.047,.008))
            for j in range(7):
                root=p.lerp(tip,.12+j*.105);side=M.hv(i+j*2.399);L=height*rng.uniform(.48,.65);up=M.unit(side*.9+axis*.45);w=L*.23
                st=len(m.vertices);mid=root+up*L*.47;end=root+up*L
                color=M.mix((.020,.041,.006),(.057,.101,.013),rng.random())
                for q in [root,mid+side.cross(axis)*w,mid+axis*L*.1,end,mid-side.cross(axis)*w]:m.v(q,color)
                for f in [(0,1,2),(1,3,2),(2,3,4),(0,2,4)]:m.f(tuple(st+x for x in f),'moss')
        m.finish(library)
    # Reuse the original host sampler and large-form projection code verbatim;
    # replace only dense per-patch shoot baking by rows for the shared library.
    src=(ROOT/'src/surfaces.py').read_text();src=src.replace('accepted=0;max_gap=0.;candidate_count=budget*4','accepted=0;max_gap=0.;candidate_count=budget*4;instance_rows=[]')
    begin=src.index('        path=[];ns=[]');end=src.index('        if accepted%7==0:',begin)
    src=src[:begin]+"        instance_rows.append((p,n,az))\n"+src[end:]
    src=src.replace("return ob,{'host':wood.name", "return ob,instance_rows,{'host':wood.name")
    ns={'__name__':'factored_surfaces'};exec(compile(src,'factored_surfaces.py','exec'),ns)
    report={'completed':False,'removed_forests':0,'removed_placements':0,'microshoot_templates':16,'hosts':[],'representation':'Shared connected shoots; surface-fit large thalli, crusts and bark flakes. Same full stand, no geometry culling.'}
    for name,budget in [('Tree prototype 08',3400),('Tree prototype 02',2200),('Subcanopy prototype 02',2200),('Subcanopy prototype 03',2200)]:
        col=bpy.data.collections['GT7 | '+name];wood=next(o for o in col.objects if o.name.endswith('_wood'));rc=A.recipe(name)
        for ob in list(col.objects):
            if ob.name.endswith(' | attached succession'):
                col.objects.unlink(ob)
                if not ob.users_collection:bpy.data.objects.remove(ob)
        new,rows,r=ns['colonize'](wood,col,mats,rc['seed']%3000,budget)
        batch(library,rows,col,'GT11 | '+wood.name+' | microshoot anchors');report['hosts'].append(r)
        bpy.data.orphans_purge(do_recursive=True);gc.collect();trim_allocator();print('FACTORED',name,len(rows),flush=True)
    s=bpy.context.scene;s.cycles.debug_bvh_type='STATIC_BVH'
    out=ROOT/'GREEN_TERROR_V11_INSTANCED.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    report.update(completed=True,scene=str(out),scene_sha256=hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),peak_MB=peak_rss_mib())
    (ROOT/'evidence/microflora_instancing.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':
    try:main()
    except BaseException:traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
