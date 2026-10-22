"""Integrate v6 into the recovered original rainforest, not the C++ replacement.

A static frame-1 scene is saved separately. All original stand placements,
numbered cameras, host wood and packed scan images are preserved.
"""
from __future__ import annotations
import bpy,numpy as np,random,sys,os,json,math,hashlib,gc,resource,time,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from collections import Counter
SRC=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('GT6_WORK_DIR',str(SRC.parent)))
SOURCE=Path(os.environ.get('GT6_ORIGINAL',str(ROOT.parent/'green_terror_original/GREEN_TERROR.blend')))
EXPECTED='a39d6c6368e8dde7f0cc8eb745962136cf181b7cc2db4359e485ece44ed9ee04'
sys.path[:0]=[str(SRC),str(SRC/'upstream')]
import botany as B
SEED=481516

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def log(message):print(message,'RSS_MB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,flush=True)
def mesh_record(ob):
    me=ob.data;me.calc_loop_triangles();n=len(me.vertices)
    v=np.empty(n*3,np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    tri=np.empty(len(me.loop_triangles)*3,np.int32);me.loop_triangles.foreach_get('vertices',tri);tri=tri.reshape(-1,3)
    area=np.linalg.norm(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]),axis=1)*.5
    r={'name':ob.name,'vertices':n,'triangles':len(tri),'nonfinite_vertices':int((~np.isfinite(v)).any(axis=1).sum()),'zero_area_triangles':int((area<=1e-16).sum()),'minimum_triangle_area_m2':float(area.min()),'geometry_sha256':hashlib.sha256(v.tobytes()+tri.tobytes()).hexdigest()}
    if r['nonfinite_vertices'] or r['zero_area_triangles']:raise RuntimeError('New mesh failed validation: '+ob.name)
    return r

def bounds(collection):
    lo=np.full(3,np.inf);hi=np.full(3,-np.inf)
    for ob in collection.objects:
        if ob.type!='MESH':continue
        coordinates=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',coordinates);coordinates=coordinates.reshape(-1,3)
        if len(coordinates):lo=np.minimum(lo,coordinates.min(axis=0));hi=np.maximum(hi,coordinates.max(axis=0))
    return lo,hi

def recipe(name):
    kind,index=re.fullmatch(r'(Tree|Subcanopy) prototype (\d+)',name).groups();i=int(index)
    if kind=='Tree':
        h=(24,29,33,27,36,25,31,22,34,28)[i]
        return dict(height=h,radius=h*(.012,.009,.0105,.008,.0115,.0075,.010,.0068,.020,.0095)[i],seed=SEED+i*173,prefix=f'Tropical_{i:02d}')
    h,_,r=((18.,5.3,.011),(20.5,6.,.0085),(23.,6.7,.010),(24.,7.1,.013))[i]
    return dict(height=h,radius=h*r,seed=SEED+4700+i*193,prefix=f'Subcanopy_{i:02d}')

def bvh_for(ob):
    return BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],epsilon=.00001)

def host(original,materials,report):
    import climbers
    rc=recipe(original.name);wood=next(o for o in original.objects if o.name==rc['prefix']+'_wood');bvh=bvh_for(wood)
    def projector(point,normal):
        p,n,_,_=bvh.ray_cast(Vector(point)+Vector(normal)*.08,-Vector(normal),.16)
        return (p+n*.001,n) if p is not None else None
    original_builder=climbers.SurfaceMesh
    budget=120 if original.name=='Tree prototype 08' else 45
    class HostBuilder(B.MeshBuilder):
        def __init__(self,mats):super().__init__('GT6 | '+original.name+' | climbers',mats);self.moss_calls=0
        def tube(self,points,radii,key='stem',sides=5,color=None):
            color=color if color is not None else ((.033,.030,.021) if key=='bark_smooth' else (.045,.073,.022))
            return super().tube(points,radii,key,sides,color)
        def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
            variant=int(abs(math.sin(sum(base)*4.3))*3)
            B.blade(self,rng,base,axis,normal,length,width*(1.1 if variant==0 else .92),'cordate' if variant==0 else 'elliptic' if variant==1 else 'lance',2,.12 if key=='leaf_new' else rng.uniform(.45,.92),damage=.24)
            self.counts['climber_leaves']+=1
        def moss(self,p,n,rng):
            self.moss_calls+=1
            if self.moss_calls<=budget:B.moss(self,rng,p,n,.88,projector)
        def finish(self,name):
            self.name='GT6 | '+name;report['element_counts'].update(self.counts);return super().finish()
    climbers.SurfaceMesh=HostBuilder
    aliases=dict(materials);aliases['bark_smooth']=materials['stem']
    try:generated=climbers.decorate_tree(rc['prefix'],wood,aliases,rc['seed'],rc['height'],rc['radius'])
    finally:climbers.SurfaceMesh=original_builder
    collection=bpy.data.collections.new('GT6 | '+original.name)
    for ob in original.objects:
        if 'attached_climbers_and_moss' not in ob.name:collection.objects.link(ob)
    for ob in generated:
        for col in list(ob.users_collection):col.objects.unlink(ob)
        collection.objects.link(ob);ob['gt6_host_mesh']=wood.name;ob['gt6_seated_on_frozen_host']=True
    mesh=B.MeshBuilder('GT6 | '+original.name+' | bark ecology',materials)
    rng=random.Random(rc['seed']+696991);ray_radius=max(3.,rc['radius']*7.);candidates=[]
    for attempt in range(1050 if original.name=='Tree prototype 08' else 440):
        angle=rng.random()*math.tau;z=rng.uniform(.05,3.15);direction=B.hvec(angle)
        p,n,_,_=bvh.ray_cast(direction*ray_radius+B.Z*z,-direction,ray_radius*2.)
        if p is None:continue
        field=.5+.24*math.sin(angle*2.1+z*3.9)+.14*math.sin(z*8.1-angle)
        if field>=.38:candidates.append((p,n,angle,z,field))
    for index,(p,n,angle,z,field) in enumerate(candidates):
        if index%7==0:B.lichen(mesh,rng,p+n*.0008,n,rng.uniform(.014,.047))
        elif index%71==0 and z<1.:B.bracket(mesh,rng,p,n,rng.uniform(.014,.041))
        elif index%3==0:
            axis,side,_=B.frame(B.Z,n);rows,cols=6,4;length=rng.uniform(.009,.032);width=length*rng.uniform(.3,.75)
            start=len(mesh.vertices);tone=rng.uniform(.73,1.19)
            for i in range(rows+1):
                t=i/rows
                for j in range(cols+1):
                    v=2*j/cols-1;half=width*.5*(.56+.36*math.sin(math.pi*t))*(1+.12*math.sin(17*t+angle))
                    target=p+axis*length*t+side*v*half;q,nn,_,_=bvh.find_nearest(target,.065)
                    if q is None:q,nn=target,n
                    mesh.v(q+nn*(.00020+.0024*t*t*(.55+.45*v*v)),(.14*tone,.121*tone,.085*tone),(j/cols,t),field)
            for i in range(rows):
                for j in range(cols):
                    q=start+i*(cols+1)+j;mesh.f((q,q+cols+1,q+cols+2,q+1),'flake')
            mesh.counts['lifted_bark_flakes']+=1
    ob=mesh.finish(collection)
    if ob:generated.append(ob)
    report['element_counts'].update(mesh.counts)
    return collection,generated

def plant(original,materials,report):
    kind,index=re.fullmatch(r'(broadleaf|fern|palm|shrub|Midstory) prototype (\d+)',original.name).groups();index=int(index)
    collection=bpy.data.collections.new('GT6 | '+original.name)
    mesh=B.MeshBuilder('GT6 | '+original.name+' | multigeneration plant',materials)
    seed=SEED+81031+index*499+{'fern':0,'palm':5000,'broadleaf':10000,'shrub':15000,'Midstory':20000}[kind]
    factory=B.shrub if kind=='Midstory' else getattr(B,kind);factory(mesh,seed,index)
    lo,hi=bounds(original);vertices=np.asarray(mesh.vertices,np.float32);newlo=vertices.min(axis=0);newhi=vertices.max(axis=0)
    # Preserve the size envelope, not the old repetitive shoot organization.
    old_xy=max(hi[0]-lo[0],hi[1]-lo[1]);new_xy=max(newhi[0]-newlo[0],newhi[1]-newlo[1])
    vertices[:,:2]*=old_xy/max(new_xy,1e-6)
    vertices[:,2]=(vertices[:,2]-newlo[2])*(hi[2]-lo[2])/max(newhi[2]-newlo[2],1e-6)+lo[2]
    mesh.vertices=[tuple(p) for p in vertices]
    ob=mesh.finish(collection);ob['gt6_architecture_family']=kind;ob['gt6_seed']=seed
    report['element_counts'].update(mesh.counts)
    return collection,[ob]

def ground_details(scene,materials,report):
    ground=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Uneven forest humus'));bvh=bvh_for(ground)
    def height(x,y):
        p,n,_,_=bvh.ray_cast(Vector((x,y,20)),Vector((0,0,-1)),40)
        return (p,n) if p is not None else None
    records=json.loads((ROOT/'evidence/original_instances.json').read_text())
    focuses=[Vector((-4.7,1.5,0)),Vector((0,-3.,0)),Vector((-1.,1.,0))];patches=[]
    for row in records:
        if not row['collection'].startswith('DETAIL | Litter prototype'):continue
        p=Vector((row['matrix'][0][3],row['matrix'][1][3],0))
        if min((p-f).length for f in focuses)<4.4:patches.append(row)
    patches.sort(key=lambda x:x['name'])
    collection=bpy.data.collections.new('GT6 | forest floor decomposition');scene.collection.children.link(collection)
    rng=random.Random(SEED+901912);created=[]
    for group in range(0,len(patches),20):
        mesh=B.MeshBuilder(f'GT6 | decomposing forest floor {group//20:02d}',materials)
        for row in patches[group:group+20]:
            center=Vector((row['matrix'][0][3],row['matrix'][1][3],row['matrix'][2][3]))
            for i in range(18):
                x=center.x+rng.gauss(0,.38);y=center.y+rng.gauss(0,.38);contact=height(x,y)
                if contact is None:continue
                p,n=contact;p=p+n*rng.uniform(.002,.013);wet=B.habitat(p)
                if i%6==0:
                    length=rng.uniform(.08,.17);angle=rng.random()*math.tau;before=len(mesh.vertices)
                    B.blade(mesh,rng,p,B.hvec(angle),n,length,length*rng.uniform(.35,.59),'elliptic',1,rng.uniform(.7,1),True,.75,skeleton=i==0)
                    new=mesh.vertices[before:];lift=0.
                    for vx,vy,vz in new[::max(1,len(new)//24)]:
                        contact=height(vx,vy)
                        if contact:lift=max(lift,contact[0].z+.001-vz)
                    if lift>0:mesh.vertices[before:]=[(vx,vy,vz+lift) for vx,vy,vz in new]
                else:
                    length=rng.uniform(.022,.073);direction=B.hvec(rng.random()*math.tau);side=B.unit(n.cross(direction));start=len(mesh.vertices)
                    color=B.mix((.092,.043,.017),(.043,.029,.016),wet)
                    for j in range(9):
                        t=j/8
                        for k in (-1,0,1):
                            q=p+direction*length*t+side*k*length*.23*math.sin(math.pi*(t*.94+.03))+n*(.003*math.sin(t*4+k)+.002*k*k)
                            mesh.v(q,color,(k*.5+.5,t),wet)
                    for j in range(8):
                        for k in range(2):
                            if rng.random()<.09:continue
                            q=start+j*3+k;mesh.f((q,q+3,q+4,q+1),'dead')
                    mesh.counts['decaying_fragments']+=1
            for j in range(5):
                contact=height(center.x+rng.uniform(-.5,.5),center.y+rng.uniform(-.5,.5))
                if not contact:continue
                p,n=contact;direction=B.hvec(rng.random()*math.tau);length=rng.uniform(.08,.31);path=[]
                for t in B.linspace(0,1,8):
                    q=p+direction*length*t;contact=height(q.x,q.y)
                    if contact:q.z=contact[0].z+.004+.005*math.sin(math.pi*t)
                    path.append(q)
                mesh.tube(path,[.0026*(1-.83*t) for t in B.linspace(0,1,8)],'dry_fibre',4)
                junction=path[4];tip=junction+B.hvec(math.atan2(direction.y,direction.x)+.7)*length*.45
                mesh.tube([junction,junction.lerp(tip,.5)+n*.009,tip],[.0015,.0009,.0003],'dry_fibre',3)
                mesh.counts['branched_fine_twigs']+=1
        ob=mesh.finish(collection)
        if ob:created.append(ob)
        report['element_counts'].update(mesh.counts);del mesh;gc.collect()
    report['ground_patch_count']=len(patches);return created

def main():
    started=time.time()
    if sha(SOURCE)!=EXPECTED:raise ValueError('Original-source digest mismatch')
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GREEN_TERROR_BASELINE_BATCHED.blend'),use_scripts=False)
    scene=bpy.context.scene;cameras=[scene.objects[n] for n in ('01_GREEN_TERROR','02_ROOTS_AND_UNDERSTORY','04_BARK_AND_LITTER')]
    poses={o.name:tuple(x for row in o.matrix_world for x in row) for o in scene.objects if o.instance_type=='COLLECTION'}
    camera_poses={o.name:tuple(x for row in o.matrix_world for x in row) for o in scene.objects if o.type=='CAMERA'}
    packed={im.name for im in bpy.data.images if im.packed_file}
    report={'revision':'integrated_detail_v6','source_sha256':EXPECTED,'original_revision':'surface_detail_v3','static_frame':1,'blender_version':bpy.app.version_string,'new_meshes':[],'element_counts':Counter(),'upgraded_groups':[],'rendered':False}
    materials=B.make_materials();groups={}
    supported=re.compile(r'(Tree|Subcanopy|broadleaf|fern|palm|shrub|Midstory) prototype \d+$')
    for ob in scene.objects:
        if ob.instance_type!='COLLECTION' or ob.instance_collection is None:continue
        name=ob.instance_collection.name
        if not supported.fullmatch(name):continue
        p=ob.matrix_world.translation;distance=min(math.hypot(p.x-c.location.x,p.y-c.location.y) for c in cameras)
        if distance<=(7. if name.startswith(('Tree','Subcanopy')) else 6.):groups.setdefault(name,[]).append(ob)
    log(f'Selected {sum(map(len,groups.values()))} instances / {len(groups)} groups')
    for name,instances in sorted(groups.items()):
        original=bpy.data.collections[name];log('BUILD '+name)
        collection,objects=(host if name.startswith(('Tree','Subcanopy')) else plant)(original,materials,report)
        for ob in instances:ob['gt6_original_prototype']=name;ob.instance_collection=collection
        for ob in objects:report['new_meshes'].append(mesh_record(ob))
        report['upgraded_groups'].append({'original':name,'new':collection.name,'instance_count':len(instances)})
        (ROOT/'evidence/integration_in_progress.json').write_text(json.dumps(report,indent=2));gc.collect()
    for ob in ground_details(scene,materials,report):report['new_meshes'].append(mesh_record(ob))
    if any(tuple(x for row in scene.objects[n].matrix_world for x in row)!=p for n,p in poses.items()):raise RuntimeError('Instance placement changed')
    if any(tuple(x for row in scene.objects[n].matrix_world for x in row)!=p for n,p in camera_poses.items()):raise RuntimeError('Camera changed')
    if packed!={im.name for im in bpy.data.images if im.packed_file}:raise RuntimeError('Original packed assets changed')
    report.update(geometry_integrated=True,original_untouched=sha(SOURCE)==EXPECTED,original_instance_transforms_preserved=True,original_camera_poses_preserved=True,packed_images_preserved=len(packed),unique_added_vertices=sum(m['vertices'] for m in report['new_meshes']),unique_added_triangles=sum(m['triangles'] for m in report['new_meshes']),elapsed_seconds=time.time()-started)
    report['known_limits']=['Static frame-1 look-development copy; new wind binding is not implemented.','No calibrated ecosystem/species model or measured spectral optics.','Foliage interpenetration is not globally collision-relaxed.','Added detail is concentrated near original ground cameras; distant crowns remain unchanged.']
    scene['gt6_revision']=report['revision'];scene['gt6_integration_report']=json.dumps(report)
    for path in sorted(SRC.glob('*.py')):
        text=bpy.data.texts.new('GT6_SOURCE/'+path.name);text.write(path.read_text())
    scene.cycles.debug_use_compact_bvh=True;scene.render.use_persistent_data=False;scene.render.use_motion_blur=False
    output=ROOT/'GREEN_TERROR_V6_INTEGRATED.blend';log('Saving integrated original-scene copy')
    bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
    report.update(output=str(output),output_sha256=sha(output));(ROOT/'evidence/integration.json').write_text(json.dumps(report,indent=2));log('INTEGRATION_COMPLETE')
if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback;traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
