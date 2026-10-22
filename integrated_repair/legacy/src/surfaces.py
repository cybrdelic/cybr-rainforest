"""Continuous bark microhabitats anchored on evaluated wood, no rosette stamps."""
import bpy, numpy as np, math, random
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
import morphology_v9 as M
Z=M.Z;unit=M.unit;hv=M.hv;TAU=math.tau

def habitat(p,n,seed):
    q=p+Vector((seed*.017,1.93,5.2))
    return (.50+.26*noise.noise(q*1.63)+.14*noise.noise(q*5.9)+.055*noise.noise(q*21.7)
            +.10*max(0,n.z)-.027*max(0,p.z-1.2))

def colonize(wood,col,mats,seed,budget=3500):
    me=wood.data;me.calc_loop_triangles();rng=np.random.default_rng(seed);rr=random.Random(seed)
    co=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    tri=np.empty(len(me.loop_triangles)*3,np.int32);me.loop_triangles.foreach_get('vertices',tri);tri=tri.reshape(-1,3)
    normals=np.cross(co[tri[:,1]]-co[tri[:,0]],co[tri[:,2]]-co[tri[:,0]])
    area=np.linalg.norm(normals,axis=1)*.5;z=co[tri,2].mean(axis=1)
    ids=np.flatnonzero((area>1e-10)&(z>.025)&(z<6.0));weights=area[ids];weights/=weights.sum()
    bvh=BVHTree.FromPolygons([Vector(p) for p in co],tri.tolist(),all_triangles=True)
    mesh=M.Mesh('GT11 | '+wood.name+' | attached succession',mats)
    accepted=0;max_gap=0.;candidate_count=budget*4
    points=rng.choice(ids,candidate_count,p=weights)
    def seat(p,distance=.11):
        q,n,i,dist=bvh.find_nearest(p,distance)
        return (q+n*.00035,n) if q is not None else (p,Z)
    cover=np.empty(len(co),np.float32)
    for i,p in enumerate(co):cover[i]=max(0,min(1,(habitat(Vector(p),Vector(me.vertices[i].normal),seed)-.44)*3.6)) if p[2]<7 else 0
    attr=me.attributes.get('gt11_colony_cover') or me.attributes.new('gt11_colony_cover','FLOAT','POINT');attr.data.foreach_set('value',cover)
    for index in points:
        u,v=rr.random(),rr.random()
        if u+v>1:u,v=1-u,1-v
        a,b,c=co[tri[index]];p=Vector(a+(b-a)*u+(c-a)*v);n=unit(Vector(normals[index]))
        h=habitat(p,n,seed)
        if h<.48 or rr.random()>min(1,(h-.44)*5):continue
        accepted+=1;_,x,y=M.frame(n,Z)
        # Creeping connected root system tracks the wood before any shoots rise.
        length=rr.uniform(.018,.072);az=rr.random()*TAU;d=x*math.cos(az)+y*math.sin(az)
        path=[];ns=[]
        for t in np.linspace(0,1,7):
            q,qn=seat(p+d*length*(t-.3)+y*length*.1*math.sin(t*5));path.append(q);ns.append(qn)
        mesh.tube(path,.00048,'moss',4,(.035,.040,.012));mesh.counts['host_conforming_runners']+=1
        for s in range(3):
            k=1+s*2;root=path[k];normal=ns[k];up=unit(normal*.7+Z*.55);height=rr.uniform(.006,.019)
            tip=root+up*height+d*height*.17
            mesh.tube([root,root.lerp(tip,.5),tip],[.00036,.00026,.00008],'moss',3,(.032,.048,.008))
            for j in range(6):
                a1=j*2.399+az;side=x*math.cos(a1)+y*math.sin(a1);base=root.lerp(tip,.17+.12*j)
                L=height*rr.uniform(.44,.66);axis=unit(side*.9+up*.45);wid=L*.26
                mid=base+axis*L*.48+normal*L*.15;end=base+axis*L
                st=len(mesh.vertices);clr=M.mix((.025,.046,.006),(.072,.125,.015),rr.random()*.7)
                for q in (base,mid+y*wid,mid+normal*L*.08,end,mid-y*wid):mesh.v(q,clr)
                for f in ((0,1,2),(1,3,2),(2,3,4),(0,2,4)):mesh.f(tuple(st+i for i in f),'moss')
            mesh.counts['connected_moss_shoots']+=1
        if accepted%7==0:
            # A lobed liverwort thallus follows the host with irregular edges.
            axis=d;L=rr.uniform(.025,.082);W=L*rr.uniform(.18,.32);st=len(mesh.vertices)
            for k in range(13):
                t=k/12
                for j in range(5):
                    v=(j-2)/2;w=W*(.75+.24*math.sin(25*t+az))*math.sin(math.pi*(.12+.85*t))**.5
                    q,qn=seat(p+axis*L*t+y*w*v);lift=.0004+abs(v)**2*.0012*(.5+.5*math.sin(t*19+az))
                    mesh.v(q+qn*lift,(.041,.079,.022),(j/4,t),.5)
                    if k and j:
                        a=st+(k-1)*5+j-1;mesh.f((a,a+5,a+6,a+1),'moss')
            mesh.counts['host_fitted_thalli']+=1
        if accepted%13==0:
            # Crust with a jagged boundary, not an isolated symmetric star.
            st=len(mesh.vertices);L=rr.uniform(.014,.05);mesh.v(p+n*.0007,(.13,.16,.09))
            for j in range(19):
                a=TAU*j/19;r=L*(.72+.20*math.sin(3*a+az)+.14*math.sin(7*a-az))
                q,qn=seat(p+(x*math.cos(a)+y*math.sin(a))*r);mesh.v(q+qn*.0007,(.13,.16,.09))
            for j in range(19):mesh.f((st,st+1+j,st+1+(j+1)%19),'lichen')
            mesh.counts['irregular_crusts']+=1
        if accepted%19==0:
            # Lifted strip: lower edge rooted, curling outer edge casts shadow.
            L=rr.uniform(.035,.105);W=L*rr.uniform(.17,.35);st=len(mesh.vertices)
            for k in range(11):
                t=k/10
                for j in range(5):
                    v=(j-2)/2;ww=W*(.86+.14*math.sin(t*23+az));q,qn=seat(p+Z*L*t+x*ww*v)
                    lift=.0006+L*.14*t**2.3*(.7+.3*abs(v))
                    mesh.v(q+qn*lift,(.084,.068,.036),(j/4,t),.3)
                    if k and j:
                        a=st+(k-1)*5+j-1;mesh.f((a,a+5,a+6,a+1),'flake')
            mesh.counts['raised_bark_scales']+=1
        if accepted>=budget:break
    ob=mesh.finish(col)
    return ob,{'host':wood.name,'accepted':accepted,'candidates':candidate_count,'counts':dict(mesh.counts),'field': 'Shared smooth spatial field drives both attached geometry and substrate color; height and upward normal weighted.'}
