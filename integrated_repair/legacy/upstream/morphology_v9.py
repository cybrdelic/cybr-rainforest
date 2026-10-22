"""GREEN TERROR V9: connected, scale-aware botanical geometry.

Metres; deterministic seeds; no generated imagery or image-backed geometry.
Leaf holes are closed irregular contours constrained in a Delaunay triangulation,
not deleted grid cells. Branches have explicit parent/child attachment points.
"""
from __future__ import annotations
import math, random, hashlib
from collections import Counter
from functools import lru_cache
import numpy as np
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils import noise
import ecology_v8 as E
import botany as B

Z=Vector((0,0,1)); TAU=math.tau
unit=B.unit; frame=B.frame; mix=B.mix; hv=B.hvec
SECONDARIES=np.linspace(.13,.86,9)


def smoothstep(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)))
    return t*t*(3-2*t)


def spatial_field(p,seed=0):
    p=Vector(p)+Vector((seed*.00137,seed*.000731,seed*.001913))
    return (.54+.24*noise.noise(p*1.83)+.15*noise.noise(p*5.7)+.07*noise.noise(p*19.7))


class Mesh(E.Mesh):
    """Same compact instanced geometry/attributes as V8, with improved woody tubes."""
    def tube(self,points,radii,key='stem',sides=5,color=(.045,.073,.022)):
        points=[Vector(p) for p in points]
        if len(points)<2:return
        radii=[float(radii)]*len(points) if isinstance(radii,(int,float,np.floating)) else list(radii)
        if len(radii)!=len(points):raise ValueError('One radius per ring required')
        woody=key in ('stem','dry_fibre','bark_smooth') and max(radii)>.003
        if not woody:return super().tube(points,radii,key,sides,color)
        sides=max(sides,8 if max(radii)<.03 else 12)
        rings=[];previous=None
        phase=sum(points[0])*7.127+sum(points[-1])*3.017
        for i,(p,r) in enumerate(zip(points,radii)):
            tangent=unit(points[min(i+1,len(points)-1)]-points[max(0,i-1)])
            if previous is None:_,a,b=frame(tangent)
            else:a=unit(previous-tangent*previous.dot(tangent));b=unit(tangent.cross(a))
            previous=a;u=i/(len(points)-1)
            ring=[]
            for j in range(sides):
                th=TAU*j/sides
                lobe=1+.065*math.sin(3*th+phase+u*1.1)+.029*math.sin(7*th-phase+u*2.4)
                elliptic=1+.058*math.cos(2*th+phase)
                swelling=1+.035*math.sin(12*u+phase)+.018*math.sin(29*u)
                q=p+(a*math.cos(th)+b*math.sin(th))*max(r,1e-6)*lobe*elliptic*swelling
                tone=.89+.1*math.sin(th*3+u*19+phase)
                ring.append(self.v(q,tuple(c*tone for c in color),(u,j/sides),.35))
            rings.append(ring)
            if i:
                for j in range(sides):self.f((rings[-2][j],rings[-2][(j+1)%sides],ring[(j+1)%sides],ring[j]),key)
        self.f(tuple(reversed(rings[0])),key);self.f(tuple(rings[-1]),key)
        self.counts['noncircular_woody_segments']+=1

    def finish(self,collection=None):
        # Retain regular quads (half the native topology storage of a forced
        # triangle mesh). Split only projected faces with a collapsed corner.
        if not self.faces:return None
        tris=[];owners=[]
        for index,f in enumerate(self.faces):
            for j in range(1,len(f)-1):tris.append((f[0],f[j],f[j+1]));owners.append(index)
        co=np.asarray(self.vertices,np.float32);ids=np.asarray(tris,np.int32)
        area=np.linalg.norm(np.cross(co[ids[:,1]]-co[ids[:,0]],co[ids[:,2]]-co[ids[:,0]]),axis=1)*.5
        keep=np.isfinite(area)&(area>2e-15)
        badowners=set(owners[i] for i in np.flatnonzero(~keep))
        faces=[];indices=[]
        for i,(f,k) in enumerate(zip(self.faces,self.indices)):
            if i not in badowners:faces.append(f);indices.append(k)
        for i,(f,owner) in enumerate(zip(tris,owners)):
            if owner in badowners and keep[i]:faces.append(f);indices.append(self.indices[owner])
        self.counts['collapsed_projection_triangles_removed']+=int((~keep).sum())
        self.faces=faces;self.indices=indices
        del co,ids,area,tris,owners,keep,badowners
        ob=super().finish(collection)
        if ob:ob['gt9_geometry']=True;ob['gt9_counts']=str(dict(self.counts))
        return ob



class LeafSurface:
    def __init__(self,base,axis,normal,L,W,shape,rng,dead=False,damage=.15,age=.6):
        self.base=Vector(base);self.axis,self.side,self.normal=frame(axis,normal)
        self.length=float(L);self.width=float(W);self.shape=shape;self.age=age;self.dead=dead
        self.phase=rng.random()*TAU;self.asym=rng.uniform(-.12,.12)
        self.twist=rng.uniform(-.16,.16)*(1.4 if dead else 1)
        self.curl=rng.uniform(.04,.17) if not dead else rng.uniform(.14,.37)
        self.droop=rng.uniform(.035,.21) if not dead else rng.uniform(-.14,.31)
        self.bites=[]
        if rng.random()<damage:
            for _ in range(rng.randrange(1,4)):
                self.bites.append((rng.uniform(.27,.87),rng.choice((-1,1)),rng.uniform(.025,.065),rng.uniform(.1,.38)))
        self.secondary_phase=rng.uniform(-.008,.008)

    def profile(self,t,v):
        t=max(.00035,min(.99965,float(t)))
        if self.shape=='cordate':
            w=math.sin(math.pi*(.105+.895*t))**.67*(1.38-.64*t)
        elif self.shape=='lance':w=math.sin(math.pi*t)**.88*(1.09-.23*t)
        elif self.shape=='pinnule':w=math.sin(math.pi*t)**.68*(1.28-.48*t)
        else:w=math.sin(math.pi*t)**.61*(1.08-.12*t)
        w*=1+self.asym*math.tanh(v*4)*math.sin(math.pi*t)
        w*=1+.010*math.sin(t*47+self.phase)+.007*math.sin(t*83-self.phase)
        for center,sign,rad,depth in self.bites:
            if sign*v>0:w*=1-depth*math.exp(-((t-center)/rad)**2.2 if t>=center else -((center-t)/rad)**2.2)
        return w

    def pos(self,t,v):
        t=float(t);v=float(v)
        width=self.width*.5*self.profile(t,v)
        lon=t
        if self.shape=='cordate':
            lon-=.17*math.sin(math.pi*abs(v))**.72*(1-t)**4
        sag=self.length*(.045*math.sin(math.pi*t)-self.droop*t*t)
        drip=-self.length*.024*smoothstep(.84,1.,t)**2
        cupping=self.width*self.curl*abs(v)**2.5*math.sin(math.pi*t)
        twist=self.width*self.twist*v*(.3*t+.7*t*t)
        # Finite intercostal panels span curved secondary veins. Their sag is
        # zero at the vein paths and grows toward the center of each areole.
        phase=(t-.13-self.secondary_phase-.108*abs(v)**1.62)/.09125
        panel=-self.width*.013*math.sin(math.pi*phase)**2*math.sin(math.pi*abs(v))
        panel*=.65+.35*math.sin(t*9+self.phase)**2
        margin=self.width*.006*math.sin(t*39+self.phase)*abs(v)**5*math.sin(math.pi*t)
        lateral=self.width*.035*math.sin(math.pi*t)*math.sin(self.phase+t*3)
        p=self.base+self.axis*self.length*lon+self.side*(width*v+lateral)+self.normal*(sag+drip+cupping+twist+panel+margin)
        return p

    def n(self,t,v):
        dt=self.pos(min(.99999,t+.0003),v)-self.pos(max(.00001,t-.0003),v)
        dv=self.pos(t,min(.99999,v+.0003))-self.pos(t,max(-.99999,v-.0003))
        n=unit(dt.cross(dv),self.normal)
        return n if n.dot(self.normal)>0 else -n


def point_inside(point,poly):
    x,y=point;inside=False;j=len(poly)-1
    for i,(xx,yy) in enumerate(poly):
        xj,yj=poly[j]
        if (yy>y)!=(yj>y) and x < (xj-xx)*(y-yy)/(yj-yy)+xx:inside=not inside
        j=i
    return inside


def polygon_distance(p,poly):
    x,y=p;best=100.
    for k,(ax,ay) in enumerate(poly):
        bx,by=poly[(k+1)%len(poly)];dx=bx-ax;dy=by-ay
        u=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/max(dx*dx+dy*dy,1e-15)))
        best=min(best,math.hypot(x-ax-u*dx,y-ay-u*dy))
    return best


@lru_cache(maxsize=16)
def regular_topology(detail):
    nr,nc=((36,14) if detail>=2 else (18,8) if detail else (7,4))
    coords=[(i/nr,-1+2*j/nc) for i in range(nr+1) for j in range(nc+1)]
    faces=[]
    for i in range(nr):
        for j in range(nc):
            a=i*(nc+1)+j;b=a+nc+1
            faces.append((a,b,b+1,a+1))
    boundary=list(range(nc+1))+[i*(nc+1)+nc for i in range(1,nr+1)]+[nr*(nc+1)+j for j in range(nc-1,-1,-1)]+[i*(nc+1) for i in range(nr-1,0,-1)]
    return coords,faces,boundary


def damage_topology(detail,holes):
    """CDT exactly constrains curved injury outlines; no mesh-cell deletion."""
    coords,_,boundary=regular_topology(detail)
    coords=list(coords)
    edges=[(boundary[i],boundary[(i+1)%len(boundary)]) for i in range(len(boundary))]
    hole_ids=[]
    for poly in holes:
        ids=list(range(len(coords),len(coords)+len(poly)));coords.extend(poly)
        edges.extend((ids[i],ids[(i+1)%len(ids)]) for i in range(len(ids)));hole_ids.append(ids)
    # Remove regular interior points inside holes; contour vertices remain.
    result=delaunay_2d_cdt([Vector(c) for c in coords],edges,[],0,1e-7,False)
    out=[tuple(v) for v in result[0]];faces=[]
    for f in result[2]:
        center=tuple(sum(out[k][axis] for k in f)/len(f) for axis in range(2))
        if not (-1e-6<=center[0]<=1.000001 and -1.000001<=center[1]<=1.000001):continue
        if any(point_inside(center,h) for h in holes):continue
        a,b,c=[out[k] for k in f[:3]]
        sign=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        faces.append(tuple(f) if sign>0 else tuple(reversed(f)))
    return out,faces


def leaf(mesh,rng,base,axis,normal,L,W,shape='elliptic',detail=1,age=.55,dead=False,damage=.12,skeleton=False,veins=True):
    if L<=0 or W<=0:raise ValueError('Leaf dimensions must be positive')
    ev=LeafSurface(base,axis,normal,L,W,shape,rng,dead,damage,age)
    tone=rng.uniform(.82,1.15)
    green=mix((.105,.15,.038),(.027,.073,.018),max(0,min(1,age)))
    if age<.16 and rng.random()<.28:green=mix(green,(.125,.048,.018),.55)
    if dead:green=mix((.17,.083,.035),(.025,.019,.013),age)
    green=tuple(c*tone for c in green)
    wet=rng.uniform(.18,.70) if not dead else rng.uniform(.22,.75)
    holes=[]
    if detail>=1 and not skeleton and rng.random()<damage:
        n=rng.randint(1,3) if detail>=2 else 1
        for k in range(n):
            t0=rng.uniform(.25,.78);v0=rng.choice((-1,1))*rng.uniform(.40,.66)
            rt=rng.uniform(.016,.047);rv=rng.uniform(.065,.15);phase=rng.random()*TAU
            poly=[]
            for j in range(32):
                a=TAU*j/32;rr=1+.13*math.sin(3*a+phase)+.075*math.sin(7*a-phase)
                poly.append((t0+rt*math.cos(a)*rr,v0+rv*math.sin(a)*rr))
            if not any(abs(t0-sum(p[0] for p in h)/len(h))<.13 for h in holes):holes.append(poly)
    start=len(mesh.vertices)
    if not skeleton:
        coords,faces=damage_topology(detail,holes) if holes else regular_topology(detail)[:2]
        for t,v in coords:
            pigment=1+.028*math.sin(t*14+v*3+ev.phase)+.012*math.sin(t*47-v*17+ev.phase)
            edge=smoothstep(.86,1,abs(v))*max(0,age-.60)*.4
            scar=0.
            if holes:
                # This field uses the same contours as the removed tissue.
                scar=max(math.exp(-polygon_distance((t,v),h)/.009) for h in holes)*.85
            c=mix(tuple(k*pigment for k in green),(.066,.036,.016),max(edge,scar))
            mesh.v(ev.pos(t,v),c,(v*.5+.5,t),wet)
        for f in faces:
            pts=[Vector(mesh.vertices[start+i]) for i in f[:3]]
            if (pts[1]-pts[0]).cross(pts[2]-pts[0]).length_squared>1e-27:mesh.f(tuple(start+i for i in f),'dead' if dead else 'leaf')
        if detail>=2:
            # A thin physical rim catches grazing light at the cuticle and each
            # injury. It is not an opaque alpha-mask or a drawn contour.
            outline=[(i/48,-1.) for i in range(49)]+[(i/48,1.) for i in range(48,-1,-1)]
            for poly in [outline]+holes:
                ids=[];thick=max(.000055,min(.00019,L*.00048))
                for t,v in poly:
                    n=ev.n(t,v);p=ev.pos(t,v)
                    ids.append((mesh.v(p,green,(v*.5+.5,t),wet),mesh.v(p-n*thick,tuple(c*.73 for c in green),(v*.5+.5,t),wet)))
                for k in range(len(ids)):
                    a,b=ids[k];c,d=ids[(k+1)%len(ids)];mesh.f((a,b,d,c),'dead' if dead else 'leaf')
            mesh.counts['cuticle_rims']+=1
        mesh.counts['curved_laminae']+=1;mesh.counts['curved_contour_holes']+=len(holes)
    vascular='dry_fibre' if dead else 'vein';vc=mix(green,(.10,.12,.041),.17)
    rad=max(.000022,L*(.0015 if detail else .0009))
    def allowed(t,v):return not any(point_inside((t,v),h) for h in holes)
    if veins:
        ts=np.linspace(.004,.993,25 if detail else 8)
        mesh.tube([ev.pos(t,0)+ev.n(t,0)*rad*.2 for t in ts],[rad*(1-.90*t) for t in ts],vascular,4 if detail else 3,vc)
        if detail>=2 or skeleton:
            for k,t0 in enumerate(SECONDARIES):
                for sign in (-1,1):
                    us=np.linspace(.025,.96,13);path=[];rads=[]
                    for u in us:
                        t=float(t0+.108*u**1.62);v=sign*.97*u
                        if not allowed(t,v):
                            if len(path)>1:mesh.tube(path,rads,vascular,3,vc)
                            path=[];rads=[];continue
                        path.append(ev.pos(t,v)+ev.n(t,v)*rad*.10);rads.append(rad*.29*(1-.92*u))
                    if len(path)>1:mesh.tube(path,rads,vascular,3,vc)
                    mesh.counts['secondary_veins']+=1
                    if k<8 and (skeleton or detail>=2):
                        for u0 in ((.2,.36,.52,.68,.84) if skeleton else (.35,.65)):
                            path=[]
                            for q in np.linspace(0,1,7):
                                u=u0+.025*math.sin(math.pi*q);t=float(t0+.108*u**1.62+.09125*q);v=sign*.97*u
                                if allowed(t,v):path.append(ev.pos(t,v)+ev.n(t,v)*rad*.06)
                            if len(path)>2:mesh.tube(path,rad*(.10 if skeleton else .09),vascular,3,vc)
                            mesh.counts['connected_tertiary_veins']+=1
    mesh.counts['skeletonized_leaves' if skeleton else 'decaying_leaves' if dead else 'living_leaves']+=1
    return ev


def bezier(a,b,c,d,t):
    return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3


def collar(mesh,p,axis,radius,rng,key='stem'):
    axis=unit(axis)
    mesh.tube([Vector(p)-axis*radius*.45,Vector(p),Vector(p)+axis*radius*.8],[radius*.91,radius*1.19,radius*.82],key,9,(.038,.031,.019))
    mesh.counts['branch_collars']+=1


def twig(mesh,rng,root,direction,length,variant=0,leaf_detail=0,leaf_scale=1.):
    direction=unit(direction);_,side,n=frame(direction)
    bend=side*rng.uniform(-.22,.22)*length+Z*rng.uniform(-.12,.10)*length
    end=Vector(root)+direction*length+bend
    controls=[Vector(root),Vector(root)+direction*length*.28,Vector(root)+direction*length*.68+bend*.4,end]
    ts=np.linspace(0,1,9);path=[bezier(*controls,t) for t in ts]
    mesh.tube(path,[max(.00025,length*.009*(1-.95*t)) for t in ts],'stem',5,(.042,.033,.020))
    count=rng.randint(5,9);offset=rng.random()*TAU
    for j in range(count):
        u=.16+.76*(j+.25*rng.random())/count
        p=bezier(*controls,u);sg=-1 if j%2 else 1
        lateral=unit(side*sg*.82+direction*.43+n*rng.uniform(-.12,.18))
        rot=math.sin(offset+j*1.3)*.15
        normal=unit(Z*.83+n*.17+side*rot)
        a=p+lateral*rng.uniform(.012,.028)
        mesh.tube([p,a],[.0011,.00045],'stem',4,(.036,.055,.019))
        L=rng.uniform(.09,.205)*leaf_scale*(1-.20*u)
        leaf(mesh,rng,a,lateral,normal,L,L*(.42 if variant%3==1 else .55),('elliptic','lance','elliptic')[variant%3],leaf_detail,rng.uniform(.38,.9),damage=.15 if leaf_detail else 0,veins=leaf_detail>0)
        mesh.counts['attached_petiole_junctions']+=1
    if rng.random()<.8:
        leaf(mesh,rng,end,unit(direction+Z*.7),side,.03*leaf_scale,.009*leaf_scale,'lance',0,.10,damage=0,veins=False)
        mesh.counts['terminal_flush_buds']+=1
    return end


def branching_tree(mesh,seed,H,R,variant=0):
    """Irregular growth cohorts and subordinate leaders, not a level/arm grid."""
    rng=random.Random(seed);H=float(H);R=float(R);phase=rng.random()*TAU
    lean=hv(phase)*rng.uniform(.025,.11)*H
    kink=hv(phase+1.4)*H*rng.uniform(.012,.042)
    def trunk(t):
        return Z*(H*t)+lean*t*t+kink*math.sin(math.pi*t)*t
    levels=np.linspace(0,1,38);radius=H*rng.uniform(.0068,.0105)
    mesh.tube([trunk(t) for t in levels],[max(.002,radius*(1-.985*t)**.85) for t in levels],'stem',11,(.055,.049,.033))
    mesh.counts['irregular_tree_leaders']+=1
    # Add a healed missing branch rather than forcing all plants to be complete.
    for _ in range(2):
        t=rng.uniform(.22,.63);p=trunk(t);axis=hv(rng.random()*TAU)+Z*.25
        end=p+axis*H*rng.uniform(.012,.035)
        mesh.tube([p,p.lerp(end,.7),end],[radius*.26,radius*.16,radius*.08],'dry_fibre',7,(.046,.031,.020))
        mesh.counts['suppressed_branch_stubs']+=1
    # The sample set is deliberately nonuniform and may contain gaps. Each
    # bough carries branchlets, rather than one leaf on a smooth wire.
    nbranches=rng.randint(10,15)
    levels=sorted(rng.uniform(.30 if variant%4==2 else .43,.965) for _ in range(nbranches))
    preferred=phase+rng.uniform(-1,1)
    for k,t in enumerate(levels):
        if variant%4==1 and .59<t<.67:continue
        p=trunk(t);a=preferred+k*2.39996+rng.gauss(0,.49)
        d=hv(a);length=R*rng.uniform(.48,1.05)*(1-.46*t)
        if variant%4==0:rise=H*rng.uniform(-.035,.05)
        elif variant%4==1:rise=H*rng.uniform(.07,.15)
        elif variant%4==2:rise=H*rng.uniform(-.065,.018)
        else:rise=H*rng.uniform(.025,.095)
        end=p+d*length+Z*rise;droop=Z*(-length*rng.uniform(.07,.23))
        ctrl=[p,p+d*length*.22+Z*abs(rise)*.26,p+d*length*.72+Z*rise*.88+droop,end]
        r=radius*rng.uniform(.27,.44)*(1-t*.3)
        us=np.linspace(0,1,18);mesh.tube([bezier(*ctrl,u) for u in us],[max(.001,r*(1-.95*u)**.85) for u in us],'stem',8,(.049,.040,.025));collar(mesh,p,d+Z*.3,r,rng)
        n=rng.randint(4,7)
        for j in range(n):
            u=.27+.66*(j+rng.random()*.65)/n
            q=bezier(*ctrl,u);sg=(-1 if j%2 else 1)
            side=hv(a+sg*rng.uniform(.62,1.40));ax=unit(d*.40+side*.64+Z*rng.uniform(-.25,.32))
            TL=rng.uniform(.31,.66)*(1-.25*t)
            endpoint=twig(mesh,rng,q,ax,TL,variant,0)
            if j%3==1:
                q2=q.lerp(endpoint,.48)
                twig(mesh,rng,q2,unit(ax*.2+hv(a-sg*1.1)+Z*.1),TL*.61,variant+1,0,.8)
                mesh.counts['tertiary_branch_forks']+=1
        twig(mesh,rng,bezier(*ctrl,.90),unit(end-bezier(*ctrl,.7)),rng.uniform(.22,.44),variant,0,.82)
        mesh.counts['irregular_secondary_boughs']+=1
    if variant%3!=0:
        t=.48 if variant%3==1 else .63;p=trunk(t);d=hv(phase+1.3)
        end=p+Z*H*(1-t)*.76+d*R*.62
        ctrl=[p,p+Z*H*.1+d*R*.13,end-Z*H*.15,end]
        us=np.linspace(0,1,22);mesh.tube([bezier(*ctrl,u) for u in us],[radius*.45*(1-.96*u)**.8 for u in us],'stem',9,(.055,.046,.031));collar(mesh,p,end-p,radius*.44,rng)
        for k in range(7):
            u=.34+k*.089;q=bezier(*ctrl,u);ax=unit(hv(phase+k*2.4)+Z*.24)
            twig(mesh,rng,q,ax,rng.uniform(.40,.74),variant+1,0)
        mesh.counts['subordinate_crown_leaders']+=1


def shade_shrub(mesh,seed,H,variant=0):
    rng=random.Random(seed);phase=rng.random()*TAU
    nstems=1+(variant%3)
    for stem in range(nstems):
        a=phase+stem*2.31;d=hv(a);h=H*rng.uniform(.68,1.02)
        root=d*.03;end=root+Z*h+d*h*rng.uniform(.10,.25)
        ctrl=[root,root+Z*h*.38,root+Z*h*.77+d*h*.13,end]
        ts=np.linspace(0,1,23)
        mesh.tube([bezier(*ctrl,t) for t in ts],[h*.009*(1-.97*t) for t in ts],'stem',8,(.045,.039,.025))
        for k,t in enumerate(sorted(rng.uniform(.20,.96) for _ in range(rng.randint(6,10)))):
            p=bezier(*ctrl,t);ang=a+k*2.399+rng.uniform(-.45,.45)
            ax=unit(hv(ang)+Z*rng.uniform(-.12,.40))
            end2=twig(mesh,rng,p,ax,H*rng.uniform(.18,.37),variant,1,.85)
            if k%3==1:twig(mesh,rng,p.lerp(end2,.52),unit(hv(ang+1.3)+Z*.14),H*.15,variant+1,1,.64)
        mesh.counts['asymmetric_shrub_leaders']+=1


def broadleaf(mesh,seed,H,variant):
    rng=random.Random(seed);phase=rng.random()*TAU;n=rng.randint(9,14)
    for i in range(n):
        a=phase+i*2.39996+rng.gauss(0,.20);d=hv(a);age=.17+.79*i/n
        root=d*.025;end=d*H*rng.uniform(.19,.44)+Z*H*rng.uniform(.42,.91)*(1-.31*age)
        c1=root+Z*H*.22;c2=end*.71+Z*H*.17
        ts=np.linspace(0,1,17);mesh.tube([bezier(root,c1,c2,end,t) for t in ts],[H*.0044*(1-.61*t) for t in ts],'stem',7,(.033,.060,.018))
        L=min(.46,H*rng.uniform(.30,.46));shape=('cordate','elliptic','lance','elliptic')[variant%4]
        norm=unit(Z+hv(a+.7)*rng.uniform(-.15,.18));axis=unit(d+Z*rng.uniform(-.24,.18))
        ev=leaf(mesh,rng,end,axis,norm,L,L*(.72 if shape=='cordate' else .39 if shape=='lance' else .52),shape,2,age,damage=.27)
        if i in (1,5):
            for j in range(3):
                t=rng.uniform(.30,.78);v=rng.uniform(-.7,.7)
                E.droplet(mesh,ev.pos(t,v)+ev.n(t,v)*.00010,ev.n(t,v),rng.uniform(.00045,.0010))
        if i%4==0:leaf(mesh,rng,root,unit(Z+d*.4),d,H*.10,H*.018,'lance',1,.90,True,damage=.45)
    mesh.counts['multigeneration_basal_crowns']+=1


def fern(mesh,seed,variant):
    rng=random.Random(seed);phase=rng.random()*TAU
    n=rng.randint(7,11)
    for f in range(n):
        a=phase+f*2.399+rng.gauss(0,.19);d=hv(a);side=hv(a+math.pi/2)
        L=rng.uniform(.68,1.14);rise=rng.uniform(.37,.71);lean=rng.uniform(.06,.17)
        def center(t):return d*L*t+side*L*.035*math.sin(t*4+f)+Z*(.08+L*(rise*math.sin(t*math.pi*.76)-lean*t*t))
        ts=np.linspace(0,1,30);mesh.tube([center(t) for t in ts],[.0037*(1-.94*t) for t in ts],'stem',5,(.035,.048,.014))
        count=rng.randint(16,22)
        for j in range(count):
            t=.12+.80*j/count
            for sign in (-1,1):
                tt=min(.94,t+(sign+1)*.004+rng.uniform(-.006,.006));root=center(tt)
                axis=unit(side*sign+d*rng.uniform(.21,.37)+Z*rng.uniform(-.09,.09))
                PL=L*.23*math.sin(math.pi*tt)**.85*rng.uniform(.86,1.11)
                pend= root+axis*PL-Z*PL*.19
                mesh.tube([root,root.lerp(pend,.5)+Z*PL*.08,pend],[.00090,.00050,.00013],'vein',4,(.04,.067,.019))
                if variant%3==2:
                    leaf(mesh,rng,root,axis,Z,PL,PL*.21,'pinnule',1,rng.uniform(.35,.88),damage=.03,veins=False)
                else:
                    for k in range(1,7):
                        u=k/7;q=root.lerp(pend,u)+Z*PL*.03*math.sin(math.pi*u)
                        for s in (-1,1):
                            pax=unit(axis*.44+d*s*.88+Z*.15);ln=PL*.30*math.sin(math.pi*u)**.62
                            leaf(mesh,rng,q,pax,Z,ln,ln*.35,'pinnule',0,rng.uniform(.48,.80),damage=0,veins=False)
        mesh.counts['arched_compound_fronds']+=1
    for k in range(2):
        d=hv(phase+k*2.4);top=Z*.21+d*.045
        pts=[Z*.008,top-Z*.06]+[top+d*.035*math.sin(t)+Z*.035*math.cos(t) for t in np.linspace(0,TAU*1.45,28)]
        mesh.tube(pts,[.0033,.0028]+list(np.linspace(.0027,.00065,28)),'stem',5,(.074,.072,.024))
        mesh.counts['unfurling_fiddleheads']+=1


def debris(mesh,seed,variant,extent=.16,count=13):
    rng=random.Random(seed);occupied=[]
    for k in range(count):
        a=rng.random()*TAU;r=extent*math.sqrt(rng.random());p=hv(a)*r
        axis=hv(rng.random()*TAU);L=rng.uniform(.028,.14) if count<25 else rng.uniform(.055,.22)
        W=L*rng.uniform(.31,.60);age=rng.uniform(.60,.98)
        # A local occupancy support envelope keeps each blade above earlier
        # leaves. The build stage subsequently fits the whole patch to terrain.
        z=.001
        for x,y,rr,h in occupied:
            if (p.x-x)**2+(p.y-y)**2 < (rr+L*.33)**2:z=max(z,h+rng.uniform(.001,.005))
        p.z=z+L*.13
        start=len(mesh.vertices)
        ev=leaf(mesh,rng,p,axis,unit(Z+hv(a)*.16),L,W,'elliptic' if variant%2 else 'lance',1 if L<.10 else 2,age,True,damage=.67,skeleton=k%11==0)
        ids=range(start,len(mesh.vertices))
        if mesh.vertices[start:]:
            minz=min(mesh.vertices[i][2] for i in ids);dz=max(0,z-minz)
            for i in ids:
                q=mesh.vertices[i];mesh.vertices[i]=(q[0],q[1],q[2]+dz)
            occupied.append((p.x+axis.x*L*.48,p.y+axis.y*L*.48,L*.37,z+L*.07))
        if k%3==0:
            q=p+axis*L*.3+Z*.002;path=[q-axis*L*.7,q,q+axis*L*.75+Z*.004]
            mesh.tube(path,[.0015,.0013,.00045],'dry_fibre',5,(.065,.039,.021))
            mesh.tube([q,q+hv(a+1.0)*L*.37],[.0009,.00025],'dry_fibre',4,(.065,.039,.021))
            mesh.counts['branching_litter_twigs']+=1
        mesh.counts['support_seated_litter_blades']+=1
    for j in range(35 if count<25 else 90):
        a=rng.random()*TAU;p=hv(a)*extent*rng.random()+Z*rng.uniform(.001,.009)
        L=rng.uniform(.004,.020);ax=hv(rng.random()*TAU);_,side,n=frame(ax)
        st=len(mesh.vertices)
        poly=[p,p+ax*L*.25+side*L*.3,p+ax*L,p+ax*L*.63-side*L*.22]
        for v in poly:mesh.v(v,tuple(c*rng.uniform(.72,1.3) for c in (.053,.033,.019)))
        mesh.f((st,st+1,st+2,st+3),'dead');mesh.counts['humified_fragments']+=1
