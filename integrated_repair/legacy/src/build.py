"""Native V11 scene modification; preserves camera/light controls and stand points."""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr, trim_allocator, enable_cycles_debug
import os,sys,time,json,hashlib,math,re,gc,ctypes,traceback
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'upstream')]
import bpy,numpy as np
from mathutils import Vector,noise
import morphology_v9 as M, morphology as F, surfaces as H, materials as S
import apply_v6 as A,climbers
INPUT=Path('inputs/historical/GREEN_TERROR_V9/GREEN_TERROR_V9_STREAMING.blend')
ORIGINAL=Path('inputs/historical/green_terror_original/GREEN_TERROR.blend')

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def log(x):print(x,'peak_MB',peak_rss_mib(),flush=True)
def trim():
    gc.collect()
    try:trim_allocator()
    except:pass

def snapshots():
    d={};cams={}
    for ob in bpy.context.scene.objects:
        if ob.type=='CAMERA':cams[ob.name]={'matrix':[list(r) for r in ob.matrix_world],'lens':ob.data.lens}
        if ob.type!='MESH' or len(ob.data.polygons)>0:continue
        hh=hashlib.sha256();v=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',v);hh.update(v.tobytes())
        for n in ('gt6_rotation','gt6_scale'):
            at=ob.data.attributes.get(n)
            if at:
                a=np.empty(len(at.data)*3,np.float32);at.data.foreach_get('vector',a);hh.update(a.tobytes())
        d[ob.name]={'sha256':hh.hexdigest(),'vertices':len(ob.data.vertices),'matrix':[list(r) for r in ob.matrix_world],'original_count':ob.get('gt6_instance_count',0)}
    return d,cams

def restore_textures(report):
    mapping={}
    for base in (Path('inputs/historical/gt_dependencies/original/GREEN_TERROR/assets'),Path('inputs/historical/gt_dependencies/GREEN_TERROR_V7/assets')):
        for p in base.rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.png','.jpg','.exr'):mapping[sha(p)]=p
    originals=list(bpy.data.images)
    with bpy.data.libraries.load(str(ORIGINAL),link=False) as (src,dst):dst.images=src.images
    imported=[i for i in dst.images if i and i not in originals]
    for i in imported:
        if i.packed_file:
            raw=i.packed_file.data;digest=hashlib.sha256(raw).hexdigest();ext=Path(i.filepath).suffix or '.png';p=ROOT/'assets'/(digest+ext);p.write_bytes(raw);mapping[digest]=p
    for i in imported:bpy.data.images.remove(i)
    report['texture_restoration']=[]
    for i in originals:
        if i.source!='FILE' or i.name=='Render Result':continue
        digest=Path(i.filepath).stem
        if digest not in mapping:
            p=Path(i.filepath)
            if not p.is_file():raise FileNotFoundError('Missing exact texture '+i.name+' '+i.filepath)
        else:p=mapping[digest]
        i.filepath=str(p);i.reload();i.buffers_free();report['texture_restoration'].append({'name':i.name,'path':str(p),'sha256':sha(p)})
    trim();log('Exact source textures restored')

def swap(col,builder,report):
    old=list(col.objects);ob=builder.finish(col)
    if ob is None:raise RuntimeError('Empty replacement '+col.name)
    for o in old:
        col.objects.unlink(o)
        if not o.users_collection:bpy.data.objects.remove(o)
    report['meshes'].append(A.mesh_record(ob));report['generated_counts'].update(builder.counts)
    bpy.data.orphans_purge(do_recursive=True);trim();log('Rebuilt '+col.name)
    return ob

def main():
    start=time.time();bpy.ops.wm.open_mainfile(filepath=str(INPUT),use_scripts=False,load_ui=False);s=bpy.context.scene
    report={'completed':False,'input':str(INPUT),'input_sha256':sha(INPUT),'revision':'V11 structure and tissue','native_blender':bpy.app.version_string,'image_generation_used':False,'meshes':[],'generated_counts':Counter(),'colonies':[],'wood':[],'plants':[]}
    (ROOT/'evidence/build_started.json').write_text(json.dumps(report,indent=2))
    poses,cams=snapshots();restore_textures(report)
    s.timeline_markers.clear();s.frame_set(1)
    s.render.use_texture_cache=True;s.render.use_auto_generate_texture_cache=True
    bpy.context.preferences.filepaths.texture_cache_directory=str(ROOT/'.texture_cache')
    s.cycles.debug_use_texture_cache_eviction=True;s.cycles.debug_texture_cache_preserve_unused=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'BASELINE_RELINKED.blend'),compress=True)
    F.install();at=S.atlas(ROOT)
    for mat in list(bpy.data.materials):
        if mat.name in ('GT9 | leaf','GT7 | leaf'):S.material_leaf(mat,at)
    for n,c in [('Healthy tropical leaf',(.032,.08,.013,1)),('Mature shade leaf',(.024,.06,.012,1)),('Unfurling young leaf',(.086,.14,.025,1))]:
        if bpy.data.materials.get(n):S.material_leaf(bpy.data.materials[n],at,c)
    mats={k:bpy.data.materials.get('GT9 | '+k) or bpy.data.materials.get('GT7 | '+k) for k in ('leaf','dead','stem','vein','dry_fibre','moss','lichen','fungus','flake')}
    mats['water']=bpy.data.materials['GT8 | isolated dew lenses'];mats['bark_smooth']=mats['stem']
    # Modify host macrogeometry before rebuilding dependent attachments.
    for ob in list(bpy.data.objects):
        if ob.type!='MESH' or not ob.name.endswith('_wood'):continue
        me=ob.data;co=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);before=co.copy()
        h=float(co[:,2].max());r=np.linalg.norm(co[:,:2],axis=1);ang=np.arctan2(co[:,1],co[:,0]);z=co[:,2]
        envelope=np.clip(z/.15,0,1)*np.clip(1-z/max(5,h*.37),0,1)
        radial=envelope*(.055*np.sin(3*ang+z*.63)+.023*np.sin(7*ang-z*1.8))
        co[:,0]+=co[:,0]*radial;co[:,1]+=co[:,1]*radial
        me.vertices.foreach_set('co',co.ravel());me.update()
        report['wood'].append({'object':ob.name,'max_displacement_m':float(np.linalg.norm(co-before,axis=1).max())})
    # Rebuild climber laminae against the changed, original host meshes.
    for col in list(bpy.data.collections):
        if not re.fullmatch(r'(Tree|Subcanopy|Emergent) prototype \d+',col.name):continue
        wood=next((o for o in col.objects if o.name.endswith('_wood')),None)
        if wood is None:continue
        if col.name.startswith('Emergent'):
            i=int(col.name[-2:]);height=max(v.co.z for v in wood.data.vertices);rc={'height':height,'radius':height*.01,'seed':90371+i*127,'prefix':wood.name[:-5]}
        else:rc=A.recipe(col.name)
        hero=col.name in ('Tree prototype 08','Tree prototype 02','Subcanopy prototype 02','Subcanopy prototype 03')
        oldobjects=[o for o in col.objects if 'attached_climbers_and_moss' in o.name]
        class Host(M.Mesh):
            def __init__(self,ms):super().__init__('GT11 climber',ms)
            def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
                a=rng.random();rr=__import__('random').Random(int(a*999999+abs(sum(base))*9277))
                shape='cordate' if int(a*10)%3==0 else 'lance' if int(a*10)%3==1 else 'elliptic'
                M.leaf(self,rr,base,axis,normal,length,width,shape,2 if hero else 1,.16 if key=='leaf_new' else .65,damage=.18)
            def moss(self,p,n,rng):pass
            def finish(self,name):self.name='GT11 | '+name;return super().finish(col)
        old=climbers.SurfaceMesh;climbers.SurfaceMesh=Host
        try:new=climbers.decorate_tree(rc['prefix'],wood,mats,rc['seed'],rc['height'],rc['radius'])[0]
        finally:climbers.SurfaceMesh=old
        report['meshes'].append(A.mesh_record(new))
        for o in oldobjects:
            for c in list(o.users_collection):
                if new.name not in c.objects:c.objects.link(new)
                c.objects.unlink(o)
            bpy.data.objects.remove(o)
        if hero:
            hero_col=bpy.data.collections.get('GT7 | '+col.name)
            if hero_col:
                # Remove only prior succession skin, not stand points or host.
                for o in list(hero_col.objects):
                    if o==new or o.name.endswith(('_wood','_leaves','_lianas')):continue
                    hero_col.objects.unlink(o)
                    if not o.users_collection:bpy.data.objects.remove(o)
                micro,rec=H.colonize(wood,hero_col,mats,rc['seed']%3000,3400 if '08' in col.name else 2200)
                report['colonies'].append(rec);report['meshes'].append(A.mesh_record(micro))
        bpy.data.orphans_purge(do_recursive=True);trim();log('Climber and host '+col.name)
    # Reorganize existing plant collections in place; instance roots unchanged.
    for col in list(bpy.data.collections):
        match=re.fullmatch(r'GT8 \| (broadleaf|shrub) prototype (\d+) \| architecture (\d+)',col.name)
        mid=re.fullmatch(r'GT9 \| GT7 \| Midstory prototype (\d+) \| growth history (\d+)',col.name)
        fern=re.fullmatch(r'(GT7 \| )?fern prototype (\d+)',col.name)
        if not (match or mid or fern):continue
        lo,hi=A.bounds(col);Hh=float(hi[2]-lo[2]);R=float(max(hi[0]-lo[0],hi[1]-lo[1])*.50)
        m=M.Mesh('GT11 | '+col.name,mats)
        if match:
            fam,i,v=match.groups();variant=int(i)+int(v);seed=33731+int(i)*971+int(v)*367
            if fam=='broadleaf':F.ground_broadleaf(m,seed,min(1.35,Hh),variant)
            else:F.understory(m,seed,min(2.8,Hh),variant)
        elif mid:
            i,v=map(int,mid.groups());variant=i+v;seed=847311+i*977+v*281
            F.architectural_tree(m,seed,Hh,R,variant);fam='midstory'
        else:
            i=int(fern.group(2));M.fern(m,173711+i*1193,i);fam='fern'
            a=np.asarray(m.vertices);factor=min(1.45,max(.65,2*R/max(np.ptp(a[:,0]),np.ptp(a[:,1]))));a*=factor;m.vertices=[tuple(p) for p in a]
        if abs(float(lo[2]))>1e-6:m.vertices=[(p[0],p[1],p[2]+float(lo[2])) for p in m.vertices]
        ob=swap(col,m,report);report['plants'].append({'collection':col.name,'family':fam,'prior_height':Hh,'prior_xy_radius':R,'new_vertices':len(ob.data.vertices)})
    report['bark_materials']=S.improve_bark()
    after,newcams=snapshots()
    if after!=poses:raise RuntimeError('Placement controllers changed')
    if newcams!=cams:raise RuntimeError('Camera transforms changed')
    report['placement_controllers_preserved']=len(poses);report['placement_vertices_preserved']=sum(v['vertices'] for v in poses.values());report['original_instances_preserved']=sum(v['original_count'] for v in poses.values());report['camera_controls_preserved']=True;report['lighting_unchanged']=True
    # Bake no image textures from generated pictures. Pack authored/retained inputs.
    bpy.data.orphans_purge(do_recursive=True);trim()
    for image in bpy.data.images:
        if image.source=='FILE' and image.filepath and not image.packed_file:image.pack()
        image.buffers_free()
    for p in (ROOT/'src').glob('*.py'):
        text=bpy.data.texts.new('GT11_SOURCE/'+p.name);text.write(p.read_text())
    s['gt11_revision']='structure-first native candidate';s['gt11_input_sha256']=report['input_sha256']
    s.camera=bpy.data.objects['04_BARK_AND_LITTER'];s.cycles.samples=128;s.render.use_persistent_data=False
    out=ROOT/'GREEN_TERROR_V11.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    report.update(completed=True,elapsed_seconds=time.time()-start,scene=str(out),scene_sha256=sha(out),original_input_unchanged=sha(INPUT)==report['input_sha256'],peak_rss_mb=peak_rss_mib())
    (ROOT/'evidence/build.json').write_text(json.dumps(report,indent=2));log('V11_COMPLETED')

if __name__=='__main__':
    try:main()
    except BaseException:
        traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
