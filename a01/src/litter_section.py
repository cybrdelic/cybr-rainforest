"""Rigidly supported litter study using original deadwood and soil assets.
This is a local model/appearance gate, not a substituted rainforest background.
Leaf meshes are never projected onto the terrain or stretched up the wood.
"""
from pathlib import Path
import sys,time,json,math,random,hashlib,resource
import bpy,numpy as np
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import botanical_assets as A
import studio

def main():
    start=time.time();bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    col=bpy.data.collections.new('A01 | litter support study');s.collection.children.link(col)
    baseline='inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend'
    with bpy.data.libraries.load(baseline,link=False) as (src,dst):
        dst.objects=['CC0 scan | dead_tree_trunk_02'];dst.materials=['Scanned wet forest humus']
    log=dst.objects[0];col.objects.link(log);mat=dst.materials[0]
    # Normalize this inherited piece for a 1m study, not an entire forest.
    co=np.array([v.co[:] for v in log.data.vertices]);center=(co.max(0)+co.min(0))*.5;scale=.78/np.max(np.ptp(co,axis=0));co=(co-center)*scale
    rot=Euler((0,0,.65)).to_matrix();co=np.array([rot@Vector(p) for p in co]);co[:,1]+=.24;co[:,2]-=co[:,2].min();co[:,2]+=.012
    log.data=log.data.copy();log.data.vertices.foreach_set('co',co.astype(np.float32).ravel());log.data.update();log.matrix_world=Matrix.Identity(4)
    coords=[];faces=[];uv=[];nr=85
    def floor_z(x,y):return .008*math.sin(x*9+y*2)+.004*math.sin(x*22-y*9)+.003*math.sin(y*38+x*21)
    for i in range(nr+1):
        for j in range(nr+1):
            x=-.8+1.6*j/nr;y=-.7+1.5*i/nr;coords.append((x,y,floor_z(x,y)));uv.append((x,y))
            if i and j:
                b=(i-1)*(nr+1)+j-1;faces.append((b,b+1,b+nr+2,b+nr+1))
    terrain=A.mesh_from('A01 | test substrate',coords,faces,col,mat,uv);terrain.data.uv_layers[0].name='GroundUV'
    # Exact native support acceleration structure for terrain and original wood.
    verts=[];tris=[]
    for ob in (terrain,log):
        me=ob.data;me.calc_loop_triangles();off=len(verts);verts.extend([ob.matrix_world@v.co for v in me.vertices]);tris.extend([tuple(off+k for k in t.vertices) for t in me.loop_triangles])
    support=BVHTree.FromPolygons(verts,tris,all_triangles=True)
    def height(x,y):
        hit,n,_,_=support.ray_cast(Vector((x,y,2)),Vector((0,0,-1)),4)
        return (float(hit.z),n) if hit is not None else (floor_z(x,y),Vector((0,0,1)))
    rng=random.Random(55419);placed=[];contact=[]
    # Simple spatial support proxy of already placed leaves; evaluated at native
    # XY sample positions. Actual shape is preserved and translated rigidly.
    def previous_support(x,y,z0):
        value=z0
        for xy,z,r in placed:
            if abs(x-xy[0])<r and abs(y-xy[1])<r:
                dist=(x-xy[0])**2+(y-xy[1])**2
                if dist<r*r:value=max(value,z-.012*(dist/(r*r)))
        return value
    for i in range(74):
        x=rng.uniform(-.57,.57);y=rng.uniform(-.48,.52);z,n=height(x,y)
        if n.z<.62:continue
        family='elliptic' if i%3 else 'lance';L=rng.uniform(.065,.155);theta=rng.random()*math.tau
        d=Vector((math.cos(theta),math.sin(theta),rng.uniform(-.10,.10)))
        ob=A.leaf(f'A01 | settled litter leaf {i}',(x,y,z+.04),d,n,L,col,family,i%4,'dry')
        bpy.context.view_layer.update()
        # Sample entire leaf at a deterministic stride; support correction is
        # translation only. No vertex is collapsed onto a support surface.
        me=ob.data;inds=np.arange(0,len(me.vertices)//2,max(1,len(me.vertices)//250))
        points=[ob.matrix_world@me.vertices[int(k)].co for k in inds]
        lifts=[]
        for p in points:
            hz,normal=height(p.x,p.y);hz=previous_support(p.x,p.y,hz)
            lifts.append(hz+.00035-p.z)
        dz=max(lifts);ob.location.z+=dz;bpy.context.view_layer.update()
        # Reject upright / excessive unsupported spans rather than flattening.
        if dz>.075:
            bpy.data.objects.remove(ob,do_unlink=True);continue
        min_gap=min((ob.matrix_world@me.vertices[int(k)].co).z-height((ob.matrix_world@me.vertices[int(k)].co).x,(ob.matrix_world@me.vertices[int(k)].co).y)[0] for k in inds)
        center=ob.matrix_world@Vector((0,.5,0));placed.append(((center.x,center.y),center.z,L*.18))
        contact.append({'name':ob.name,'sampled_vertices':len(inds),'minimum_substrate_gap_m':min_gap,'rigid_translation_z_m':dz,'no_shape_projection':True})
    # Twigs sit on substrate independently of the leaf curvature.
    for i in range(36):
        x=rng.uniform(-.55,.55);y=rng.uniform(-.5,.5);a=rng.random()*math.tau;L=rng.uniform(.04,.18);pts=[]
        for t in np.linspace(0,1,12):
            xx=x+math.cos(a)*L*t;yy=y+math.sin(a)*L*t;zz=height(xx,yy)[0]+.0012+.002*math.sin(math.pi*t);pts.append((xx,yy,zz))
        A.tube(f'A01 | supported twig {i}',pts,[.0014*(1-.8*t) for t in np.linspace(0,1,12)],col,A.plain_material('A01 | fallen twig tissue',(.042,.025,.012),.83),6)
    A.fern(col,origin=(-.48,.38,.02),seed=424,scale=.42)
    # A few living sprouts, not uniformly green coverage.
    for i,(x,y) in enumerate([(.40,.22),(-.36,-.16),(.12,.48)]):
        z=height(x,y)[0];p=Vector((x,y,z));tip=p+Vector((.015,0,.10))
        A.tube('A01 | seedling stem '+str(i),[p,p.lerp(tip,.5),tip],[.0013,.001,.0007],col)
        for sg in (-1,1):A.leaf(f'A01 | seedling blade {i}-{sg}',tip,(sg*.85,-.1,.1),(0,-1,1),.07,col,'elliptic',i%4)
    cam=bpy.data.cameras.new('A01 litter camera');ob=bpy.data.objects.new('A01 litter camera',cam);s.collection.objects.link(ob);s.camera=ob;ob.location=(.85,-1.35,1.15);studio.look(ob,(0,.03,.045));cam.lens=56
    studio.lighting(s,'soft');s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=160;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=True;s.cycles.seed=18371;s.cycles.max_bounces=10
    s.render.resolution_x=1800;s.render.resolution_y=1350;s.render.resolution_percentage=100;s.render.threads_mode='FIXED';s.render.threads=4
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='16';s.render.image_settings.color_mode='RGB';out=ROOT/'renders/LITTER_SUPPORT_STUDY.png';s.render.filepath=str(out)
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'A01_litter.blend'),compress=True)
    bpy.ops.render.render(write_still=True)
    r={'completed':out.is_file(),'scope':'isolated support and appearance study, not a rainforest replacement','leaf_count':len(contact),'contact_test':contact,'samples':160,'resolution':[1800,1350],'image_generation_used':False,'inherited_scanned_deadwood_and_ground':True,'new_leaf_textures':'procedural numerical venation','seconds':time.time()-start,'sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),'global_collision_solver':False}
    (ROOT/'evidence/litter_study.json').write_text(json.dumps(r,indent=2));print('LITTER_STUDY_DONE',flush=True)
if __name__=='__main__':main()
