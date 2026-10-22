"""GREEN TERROR V8 native geometry: wet-surface succession and branched vegetation.

All dimensions are metres. No images are used as scene geometry. This extends
rather than replaces the recovered rainforest. Vegetation is authored botanical
morphology, not a species-calibrated growth solver. Geometry randomness is seeded.
"""
from __future__ import annotations
import math, random, sys
from pathlib import Path
from collections import Counter
import bpy
import numpy as np
from mathutils import Vector, Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'upstream'))
import botany as B
import botanical_detail as D
Z=Vector((0,0,1)); TAU=math.tau; unit=B.unit; frame=B.frame; mix=B.mix; hv=B.hvec

class Mesh(B.MeshBuilder):
    """Compact merged geometry; point attributes match inherited native materials."""
    def finish(self, collection=None):
        if not self.faces:return None
        me=bpy.data.meshes.new(self.name+' | geometry')
        co=np.asarray(self.vertices,np.float32)
        if not np.isfinite(co).all():raise ValueError(self.name+': nonfinite coordinates')
        me.from_pydata(self.vertices,[],self.faces)
        for k in self.keys:me.materials.append(self.materials[k])
        me.polygons.foreach_set('material_index',self.indices)
        me.polygons.foreach_set('use_smooth',np.ones(len(me.polygons),np.bool_))
        ca=me.color_attributes.new(name='gt6_color',type='BYTE_COLOR',domain='POINT')
        ca.data.foreach_set('color',np.asarray(self.colors,np.float32).ravel())
        uv=np.zeros((len(co),3),np.float32);uv[:,:2]=self.uv
        me.attributes.new('gt7_anatomical_uv','FLOAT_VECTOR','POINT').data.foreach_set('vector',uv.ravel())
        me.attributes.new('gt8_wetness','FLOAT','POINT').data.foreach_set('value',np.asarray(self.wet,np.float32))
        me.update();me.calc_loop_triangles()
        idx=np.empty(len(me.loop_triangles)*3,np.int32);me.loop_triangles.foreach_get('vertices',idx);idx=idx.reshape(-1,3)
        areas=np.linalg.norm(np.cross(co[idx[:,1]]-co[idx[:,0]],co[idx[:,2]]-co[idx[:,0]]),axis=1)*.5
        if not np.isfinite(areas).all() or (areas<=1e-17).any():raise ValueError(self.name+': invalid triangle')
        ob=bpy.data.objects.new(self.name,me);(collection or bpy.context.scene.collection).objects.link(ob)
        ob['gt8_geometry']=True;ob['gt8_counts']=str(dict(self.counts))
        ob['gt8_min_triangle_area_m2']=float(areas.min());ob['gt8_triangles']=len(idx)
        return ob

class LeafSurface(D.Blade):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.curl*=1.65;self.twist*=1.65
    def pos(self,t,v):
        p=super().pos(t,v)
        # Corrugation follows the secondary vascular paths, not world-space noise.
        s=math.sin((t-.13-.108*abs(v)**1.62)*math.pi/.09125)
        p+=self.normal*(.012*self.width*s*math.sin(math.pi*abs(v))*math.sin(math.pi*t))
        p+=self.side*(self.width*.04*math.sin(t*4+self.phase)*t*t)
        return p

def leaf(mesh,rng,base,axis,normal,L,W,shape='elliptic',detail=1,age=.55,dead=False,damage=.12,skeleton=False,veins=True):
    ev=LeafSurface(base,axis,normal,L,W,shape,rng,dead,damage,age)
    nr,nc=(30,12) if detail==2 else (16,6) if detail else (5,2)
    tone=rng.uniform(.76,1.17)
    color=mix((.105,.173,.038),(.017,.058,.011),age)
    if dead:color=mix((.125,.057,.019),(.025,.016,.009),age)
    color=tuple(c*tone for c in color)
    holes=[]
    if detail==2 and not skeleton and rng.random()<damage:
        for _ in range(rng.randint(1,3)):
            holes.append((rng.uniform(.25,.82),rng.choice((-1,1))*rng.uniform(.30,.78),rng.uniform(.024,.055),rng.uniform(.075,.16)))
    start=len(mesh.vertices)
    if not skeleton:
        for i in range(nr+1):
            t=i/nr
            for j in range(nc+1):
                v=j*2/nc-1;scar=0.
                for ht,hv,hr,wr in holes:
                    dist=((t-ht)/hr)**2+((v-hv)/wr)**2
                    scar=max(scar,math.exp(-max(0,dist-1)*2)*.70)
                c=mix(color,(.066,.035,.010),scar)
                mesh.v(ev.pos(t,v),c,(v*.5+.5,t),rng.uniform(.60,.78))
        for i in range(nr):
            for j in range(nc):
                t=(i+.5)/nr;v=(j+.5)*2/nc-1
                if any(((t-ht)/hr)**2+((v-hv)/wr)**2<1 for ht,hv,hr,wr in holes):continue
                a=start+i*(nc+1)+j;mesh.f((a,a+nc+1,a+nc+2,a+1),'dead' if dead else 'leaf')
        mesh.counts['laminae']+=1;mesh.counts['internal_tissue_holes']+=len(holes)
    vascular='dry_fibre' if dead else 'vein'
    vcolor=mix(color,(.10,.12,.035),.22) if not dead else (.085,.050,.023)
    if veins:
        rad=L*(.0016 if detail else .001)
        steps=np.linspace(.002,.997,19 if detail else 7)
        mesh.tube([ev.pos(t,0)+ev.n(t,0)*rad*.45 for t in steps],[rad*(1-.87*t) for t in steps],vascular,4 if detail else 3,vcolor)
        if detail==2 or skeleton:
            for t0 in D.SECONDARIES:
                for side in (-1,1):
                    us=np.linspace(0,1,8)
                    path=[ev.pos(float(t0+.108*u**1.62),side*.97*u)+ev.n(float(t0+.108*u**1.62),side*.97*u)*rad*.18 for u in us]
                    mesh.tube(path,[rad*.33*(1-.91*u) for u in us],vascular,3,vcolor)
                    mesh.counts['secondary_veins']+=1
            if skeleton:
                for k,t0 in enumerate(D.SECONDARIES[:-1]):
                    gap=float(D.SECONDARIES[k+1]-t0)
                    for sg in (-1,1):
                        for u0 in np.linspace(.12,.90,9):
                            pts=[]
                            for q in np.linspace(0,1,5):
                                u=u0+.022*math.sin(q*math.pi)
                                pts.append(ev.pos(float(t0+.108*u**1.62+gap*q),sg*.97*u))
                            mesh.tube(pts,rad*.10,vascular,3,vcolor)
                            mesh.counts['connected_tertiary_crossveins']+=1
        if detail==2 and not skeleton:
            for side in (-1,1):
                ts=np.linspace(.006,.992,32)
                mesh.tube([ev.pos(t,side) for t in ts],max(.000022,L*.0003),vascular,3,color)
    mesh.counts['skeletonized_leaves' if skeleton else 'decaying_leaves' if dead else 'living_leaves']+=1
    return ev

def quad_leaf(mesh,base,axis,normal,length,width,key,color):
    """Small moss phyllid with a bent tip and three-dimensional keel."""
    ax,side,n=frame(axis,normal);start=len(mesh.vertices)
    for t in (0.,.44,.78,1.):
        w=width*(.03+.97*math.sin(math.pi*t)**.8)
        for v in (-1,0,1):
            p=Vector(base)+ax*(length*t)+side*(w*v*.5)+n*(length*.18*t*t+abs(v)*length*.065*math.sin(math.pi*t))
            mesh.v(p,color,(v*.5+.5,t),.8)
    for i in range(3):
        for j in range(2):
            q=start+i*3+j;mesh.f((q,q+3,q+4,q+1),key)

def moss_patch(mesh,seed,variant):
    rng=random.Random(seed)
    # Compact carpet rather than the old centimetre-high broadleaf weeds.
    for shoot in range(115 if variant<3 else 78):
        theta=rng.random()*TAU;r=.049*rng.random()**.85
        base=Vector((math.cos(theta)*r*1.17,math.sin(theta)*r*.73,.0003+.0010*(1-r/.050)))
        H=rng.uniform(.004,.011)*(1 if variant<3 else .75)
        axis=unit(Z*(1 if variant==2 else .46)+hv(theta)*rng.uniform(.3,.85))
        pts=[base+axis*H*t+hv(theta+.4)*H*.13*math.sin(t*math.pi) for t in np.linspace(0,1,5)]
        mesh.tube(pts,[.00020,.00017,.00012,.00007,.00003],'moss',3,(.018,.028,.008))
        for j in range(1,8):
            ph=j*2.39996+theta;u=j/8
            orient=hv(ph)*(.64 if variant%2 else .87)+axis*.50
            c=(rng.uniform(.022,.042),rng.uniform(.055,.09),rng.uniform(.008,.020))
            quad_leaf(mesh,pts[min(4,int(u*4))],orient,Z,H*rng.uniform(.28,.50),H*.13,'moss',c)
        mesh.counts['carpet_moss_shoots']+=1
        if variant==2 and shoot%12==0:
            end=base+axis*H*2.6
            mesh.tube([pts[-1],end],[.00011,.000075],'dry_fibre',3,(.09,.041,.012))
            mesh.tube([end,end+axis*.0015,end+axis*.0028],[.00035,.00060,.00012],'fungus',6,(.08,.055,.022))
            mesh.counts['sporophytes']+=1
    if variant in (1,3,4):
        # Dichotomous flattened thalli grow through the moss, not flat colored blobs.
        for j in range(9):
            ph=j*2.39996;axis=hv(ph);L=rng.uniform(.023,.042)
            for sg in (-1,1):
                d=unit(axis+hv(ph+math.pi/2)*sg*.4)
                quad_leaf(mesh,axis*.009+Z*.0008,d,Z,L,L*.38,'moss',(.025,.065,.018))
                mesh.counts['liverwort_thalli']+=1

def crust_lichen(mesh,seed):
    rng=random.Random(seed)
    for k in range(22):
        a=rng.random()*TAU;center=hv(a)*rng.uniform(0,.047)+Z*.0006
        rr=rng.uniform(.003,.015);n=12;start=len(mesh.vertices)
        mesh.v(center+Z*.001,(.105,.136,.066))
        for j in range(n):
            ph=j*TAU/n;r=rr*rng.uniform(.75,1.2)
            mesh.v(center+hv(ph)*r+Z*rng.uniform(.0003,.0020),(.086,.109,.054))
        for j in range(n):mesh.f((start,start+1+j,start+1+(j+1)%n),'lichen')
        mesh.counts['lichen_lobes']+=1

def epiphyte(mesh,seed,variant):
    rng=random.Random(seed)
    for j in range(9):
        ph=j*2.39996;L=rng.uniform(.095,.23);out=hv(ph)
        base=out*.014+Z*.008;tip=base+out*.065+Z*rng.uniform(.035,.075)
        mesh.tube([base,tip],[.0015,.0006],'stem',4,(.031,.042,.010))
        leaf(mesh,rng,tip,unit(out+Z*.27),Z,L,L*(.17 if variant%2 else .32),'lance',1,rng.uniform(.35,.78),damage=.04)
    mesh.counts['epiphyte_crowns']+=1

def droplet(mesh,p,n,r):
    """One closed spherical-cap lens with a seated footprint; true refractive mesh."""
    ax,side,up=frame(n);start=len(mesh.vertices);N=10;R=5
    for i in range(R+1):
        t=(i+.045)/(R+.10)*math.pi*.70
        rr=r*math.sin(t);height=r*(math.cos(t)+.59)
        for j in range(N):
            ph=j*TAU/N;mesh.v(Vector(p)+side*rr*math.cos(ph)+up*rr*math.sin(ph)+ax*height,(1,1,1))
        if i:
            for j in range(N):
                a=start+(i-1)*N+j;b=start+(i-1)*N+(j+1)%N;mesh.f((a,b,b+N,a+N),'water')
    mesh.f(tuple(start+j for j in reversed(range(N))),'water')
    mesh.f(tuple(start+R*N+j for j in range(N)),'water')
    mesh.counts['seated_dew_lenses']+=1

def shade_shrub(mesh,seed,H,variant):
    rng=random.Random(seed);H=float(H);phase=rng.random()*TAU
    # Ordered structural forks create four genuinely distinct silhouettes.
    stems=2 if variant==1 else 3 if variant==2 else 1
    for stem in range(stems):
        ph=phase+stem*2.39996;d=hv(ph);height=H*rng.uniform(.73,1.0)
        root=d*.025
        def trunk(t):return root+d*(H*.09*t*t)+Z*(height*t)
        ts=np.linspace(0,1,15);mesh.tube([trunk(t) for t in ts],[max(.001,height*.009*(1-.94*t)) for t in ts],'stem',7,(.046,.038,.022))
        for level in range(7):
            f=.25+level*.095;base=trunk(f);a=ph+level*(2.40 if variant%2 else 2.96)+rng.uniform(-.34,.34)
            lateral=hv(a);reach=H*rng.uniform(.23,.39)*(1-.37*f)
            tip=base+lateral*reach+Z*H*rng.uniform(.05,.16)
            pts=[base.lerp(tip,t)+Z*(H*.025*math.sin(t*math.pi)) for t in np.linspace(0,1,9)]
            mesh.tube(pts,[.0050*(1-.90*t) for t in np.linspace(0,1,9)],'stem',5,(.039,.036,.017))
            mesh.counts['structural_secondary_branches']+=1
            for node in range(1,6):
                f2=node/6;junction=pts[min(8,int(f2*8))]
                side=hv(a+math.pi/2)*(1 if node%2 else -1)
                ax=unit(lateral*.35+side*.87+Z*rng.uniform(-.1,.3))
                budpos=junction+ax*rng.uniform(.022,.040)
                mesh.tube([junction,budpos],[.0012,.00045],'stem',4,(.024,.045,.013))
                L=rng.uniform(.075,.155)*(1 if variant!=2 else .75)
                ev=leaf(mesh,rng,budpos,ax,Z,L,L*(.48 if variant%2 else .58),'elliptic',1,rng.uniform(.35,.85),damage=.12)
                if node in (2,4):
                    spur=budpos+ax*.045+Z*.023
                    mesh.tube([budpos,spur],[.00085,.00018],'stem',4)
                    for sg in (-1,1):leaf(mesh,rng,spur,unit(ax*.4+hv(a+math.pi/2)*sg),Z,L*.61,L*.30,'elliptic',1,.19,damage=.04)
                    mesh.counts['tertiary_shoots']+=1
            # Terminal rolled flush and persistent stipules.
            leaf(mesh,rng,tip,unit(lateral*.25+Z),lateral,.026,.008,'lance',1,.08,veins=False)
        mesh.counts['forked_shrub_stems']+=1

def broadleaf(mesh,seed,H,variant):
    rng=random.Random(seed)
    for i in range(12):
        a=i*2.39996+rng.uniform(-.15,.15);d=hv(a);age=.18+.78*i/12
        base=d*.018;end=d*H*rng.uniform(.22,.43)+Z*H*rng.uniform(.43,.84)*(1-.22*age)
        pts=[base.lerp(end,t)+Z*H*.05*math.sin(math.pi*t) for t in np.linspace(0,1,9)]
        mesh.tube(pts,[H*.0045*(1-.60*t) for t in np.linspace(0,1,9)],'stem',6,(.020,.043,.009))
        L=min(.55,H*rng.uniform(.32,.48));shape=('cordate','lance','elliptic','cordate')[variant%4]
        ev=leaf(mesh,rng,end,unit(d+Z*rng.uniform(-.28,.26)),Z,L,L*(.76 if shape=='cordate' else .44),shape,2,age,damage=.29)
        if i in (1,4,7):
            for j in range(5):
                t=rng.uniform(.24,.80);v=rng.uniform(-.7,.7);r=rng.uniform(.0006,.0015)
                droplet(mesh,ev.pos(t,v)+ev.n(t,v)*.00015,ev.n(t,v),r)
        if i%3==0:
            leaf(mesh,rng,base,unit(Z+d*.25),d,H*.11,H*.018,'lance',1,.95,True,damage=.6)
    for j in range(2):
        a=rng.random()*TAU;end=hv(a)*H*.12+Z*H*.98
        mesh.tube([Vector(),end],[H*.002,H*.001],'stem',5)
        ev=leaf(mesh,rng,end,unit(Z+hv(a)*.15),hv(a),H*.12,H*.025,'lance',2,.08,damage=0)
    mesh.counts['multigeneration_broadleaf_crowns']+=1

def debris(mesh,seed,variant):
    rng=random.Random(seed)
    for j in range(7):
        a=rng.random()*TAU;p=hv(a)*rng.uniform(0,.11)+Z*rng.uniform(.001,.015)
        L=rng.uniform(.025,.085);leaf(mesh,rng,p,hv(a+.5),Z,L,L*rng.uniform(.36,.63),'elliptic',2 if j==0 else 1,rng.uniform(.58,.98),True,.7,skeleton=(j==0 and variant%3==0))
    for j in range(9):
        a=rng.random()*TAU;p=hv(a)*rng.uniform(0,.11)+Z*.006;L=rng.uniform(.025,.13)
        pts=[p+hv(a+1)*L*t+Z*(.006*math.sin(t*math.pi)) for t in np.linspace(0,1,8)]
        mesh.tube(pts,[.0014*(1-.90*t) for t in np.linspace(0,1,8)],'dry_fibre',4,(.033,.021,.012))
        if j%2==0:mesh.tube([pts[4],pts[4]+hv(a+2)*L*.38],[.0007,.00007],'dry_fibre',3,(.051,.028,.009))
        mesh.counts['decomposition_twigs']+=1
    if variant in (1,5,8):
        for j in range(3):D.fungus(mesh,rng,hv(j*2.4)*.035+Z*.009,Z,rng.uniform(.010,.028))
    if variant%4==0:
        # Roots remain continuous through forks, rather than disconnected strands.
        for j in range(6):
            a=rng.random()*TAU;p=hv(a)*.06+Z*.005;path=[p+hv(a+.4)*t*.09+hv(a+1.8)*.006*math.sin(t*9) for t in np.linspace(0,1,13)]
            mesh.tube(path,[.00034*(1-.8*t) for t in np.linspace(0,1,13)],'dry_fibre',3,(.12,.097,.057))
            mesh.counts['decomposer_root_fibres']+=1
