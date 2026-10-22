"""Deterministic revisions of the tested botanical kernels.
The support relaxer is an authored quasi-static approximation, not a validated
cloth simulator. It preserves local edge lengths while allowing supported sag.
"""
from __future__ import annotations
import math,random,json
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector,Matrix
import build_assets as B
TAU=math.tau
OldBlade=B.Blade
OriginalProfile=B.profile

class RepairBlade(OldBlade):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        rr=random.Random(int(args[6] if len(args)>6 else kwargs['seed'])+3991)
        self.edgephase=rr.uniform(0,TAU);self.freq=rr.uniform(22,36)
        if self.dead:
            self.sag=rr.uniform(.004,.024)
            self.twist=rr.uniform(-.025,.025)
            self.curl=rr.uniform(.009,.032)
        if self.fam=='fern':
            self.asym=rr.uniform(-.17,.14)
            self.twist=rr.uniform(-.09,.09)
            self.sag=rr.uniform(.01,.09)
    def pos(self,t,v):
        p=super().pos(t,v)
        if self.fam=='fern':
            # Serration and a modest asymmetrical auricle near the base. Neither
            # the stem nor the geometric midrib changes side between instances.
            basew=self.W*.5*OriginalProfile(t,self.fam)
            tooth=(.5+.5*math.sin(t*self.freq*TAU+self.edgephase+math.copysign(.4,v)))**3
            extent=1-.07*tooth*math.sin(math.pi*t)**.35
            ear=.11*math.exp(-((t-.085)/.065)**2)*(1 if v>0 else -.25)
            p+=self.side*(basew*v*(extent-1+ear))
            p+=self.normal*(self.W*.035*math.sin(t*8+self.phase)*v*t)
        return p
B.Blade=RepairBlade

def material_adjustments():
    """Keep the existing connected venation maps; repair uniform material use."""
    changes=[]
    for m in list(bpy.data.materials):
        if not m.use_nodes or m.get('repair_material_done'):continue
        if 'GATE |' not in m.name:continue
        ns=m.node_tree.nodes;ln=m.node_tree.links
        bs=next((n for n in ns if n.type=='BSDF_PRINCIPLED'),None)
        if not bs:continue
        if '| fern |' in m.name:
            if bs.inputs['Base Color'].is_linked:
                sock=bs.inputs['Base Color'].links[0].from_socket
                tint=ns.new('ShaderNodeMixRGB');tint.name='REPAIR_fern_tissue';tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.70,.81,.67,1)
                ln.new(sock,tint.inputs[1]);ln.new(tint.outputs[0],bs.inputs['Base Color'])
                for n in list(ns):
                    if n.type=='BSDF_TRANSLUCENT':ln.new(tint.outputs[0],n.inputs['Color'])
            bs.inputs['Coat Weight'].default_value=0
        if 'decay state' in m.name or '| dead |' in m.name:
            # Avoid the repeated broad fibrous highlights that read as paper.
            for n in list(ns):
                if n.type=='BUMP':n.inputs['Distance'].default_value*=.30
            bs.inputs['Coat Weight'].default_value=0
            bs.inputs['Specular IOR Level'].default_value=.26
            if bs.inputs['Base Color'].is_linked:
                src=bs.inputs['Base Color'].links[0].from_socket
                tex=ns.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=42;tex.inputs['Detail'].default_value=3
                coord=ns.new('ShaderNodeTexCoord');ln.new(coord.outputs['Object'],tex.inputs['Vector'])
                ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.28;ramp.color_ramp.elements[0].color=(.32,.27,.20,1);ramp.color_ramp.elements[1].position=.73;ramp.color_ramp.elements[1].color=(.95,.85,.68,1)
                ln.new(tex.outputs['Fac'],ramp.inputs[0]);mul=ns.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=.62;ln.new(src,mul.inputs[1]);ln.new(ramp.outputs[0],mul.inputs[2]);ln.new(mul.outputs[0],bs.inputs['Base Color'])
                for n in list(ns):
                    if n.type=='BSDF_TRANSLUCENT':ln.new(mul.outputs[0],n.inputs['Color'])
        m['repair_material_done']=True;changes.append(m.name)
    return changes

def merge_into(dst,src,matrix=None):
    off=len(dst.v)
    if matrix is None:dst.v.extend(src.v)
    else:dst.v.extend(tuple(matrix@Vector(v)) for v in src.v)
    dst.uv.extend(src.uv);dst.f.extend(tuple(i+off for i in f) for f in src.f);dst.mi.extend(dst.mat(src.mats[j]) for j in src.mi);dst.smooth.extend(src.smooth)


def fern_meshes(col,stem,vein,seed=881,lod=False,only_frond=None):
    """Several age classes; nonuniform internodes, stagger, local roll and pinna
    width. Each frond is consolidated so stand instances stay inexpensive."""
    r=random.Random(seed);objects=[];roots=[];nfr=8+(seed%3)
    cache={}
    for fr in range(nfr):
        if only_frond is not None and fr!=only_frond:continue
        m=B.Mesh('REPAIR | fern frond %s %s'%(seed,fr));a=fr*2.399+r.uniform(-.4,.4)
        d=Vector((math.cos(a),math.sin(a),0));side=Vector((-d.y,d.x,0))
        age=fr%5;length=r.uniform(.57,.97)*( .68 if age==4 else 1)
        vigor=r.uniform(.68,1.1) if age!=0 else .39;droop=r.uniform(.42,.71);lateral=r.uniform(-.18,.18)
        def rach(t):
            return d*length*(.83*t+.12*t*t)+side*(length*lateral*t*t)+Vector((0,0,length*(vigor*t-droop*t*t+.04*math.sin(math.pi*t))))
        ts=np.linspace(0,1,56);B.tube(m,[rach(float(t)) for t in ts],[.0027*(1-.94*t) for t in ts],stem,7)
        n=r.randint(23,34);weights=np.array([r.uniform(.65,1.35) for _ in range(n)]);locs=.15+.82*np.cumsum(weights)/weights.sum()
        for j,t0 in enumerate(locs):
            for sg in (-1,1):
                if age==0 and j>5 and r.random()<.08:continue
                t=min(.985,float(t0)+sg*r.uniform(.004,.010));p=rach(t)
                lng=length*.20*math.sin(math.pi*(t-.09)/.91)**.78*r.uniform(.78,1.13)
                if t>.89:lng*=max(.15,1-7*(t-.89))
                tangent=B.unit(rach(min(1,t+.001))-rach(max(0,t-.001)))
                normal=B.unit(tangent.cross(side));sweep=r.uniform(.08,.40)+.16*t
                axis=B.unit(side*sg+tangent*sweep+normal*r.uniform(-.11,.09));roll=.16*math.sin(t*8+fr)+r.uniform(-.09,.09)
                normal=B.unit(normal+side*roll*sg)
                mat=B.leafmaterial('fern','young' if age==4 else 'mature')
                variant=(fr*5+j*3+(sg==1))%24;key=(variant,age==4,lod)
                if key not in cache:
                    q=B.Mesh('pinna');B.leaf(q,(0,0,0),(1,0,0),(0,0,1),.1,.019,'fern',seed+variant*83,mat,vein,0,False,False);cache[key]=q
                q=cache[key];y=B.unit(normal.cross(axis));normal=B.unit(axis.cross(y))
                scale=lng/.1;wvar=r.uniform(.76,1.16)
                T=Matrix(((axis.x*scale,y.x*scale*wvar,normal.x*scale,p.x),(axis.y*scale,y.y*scale*wvar,normal.y*scale,p.y),(axis.z*scale,y.z*scale*wvar,normal.z*scale,p.z),(0,0,0,1)))
                merge_into(m,q,T)
                # A fine midrib resolves at grazing angles without painting a
                # repeated row of bright spheres along every pinna.
                B.tube(m,[p,p+axis*lng*.47+normal*lng*.012,p+axis*lng*.94-normal*lng*.025],[.00023*scale,.00014*scale,.00003],vein,4)
        B.leaf(m,rach(.97),B.unit(rach(1)-rach(.94)),(0,0,1),.038,.008,'fern',seed+fr*17,B.leafmaterial('fern','young'),vein,0,False,False)
        o=m.finish(col);objects.append(o)
    bud=B.Mesh('REPAIR | fern root and fiddleheads')
    for j in range(2):
        a=1.1+j*2.3;d=Vector((math.cos(a),math.sin(a),0));side=Vector((-d.y,d.x,0));H=.16+j*.09
        ps=[d*.025*t+Vector((0,0,H*t)) for t in np.linspace(0,1,16)]
        center=ps[-1]+Vector((0,0,.019));coil=[]
        for t in np.linspace(0,1,50):
            rad=.019*(1-t)+.0016;ang=t*TAU*1.45;coil.append(center+d*(rad*math.sin(ang))-Vector((0,0,rad*math.cos(ang))))
        B.tube(bud,ps+coil,np.linspace(.0021,.0003,len(ps+coil)),stem,7)
        vv=[];ff=[];uu=[]
        for k,p in enumerate(coil):
            w=.005*(1-k/len(coil))+.001
            for sign in (-1,0,1):vv.append(p+side*w*sign+d*.001*(1-sign*sign));uu.append((.5+sign*.5,k/len(coil)))
            if k:
                a=(k-1)*3;b=k*3;ff.extend([(a,a+1,b+1,b),(a+1,a+2,b+2,b+1)])
        bud.add(vv,ff,uu,B.leafmaterial('fern','young'))
    objects.append(bud.finish(col))
    root=bpy.data.objects.new('REPAIR | complete varied fern %s'%seed,None);col.objects.link(root)
    for o in objects:o.parent=root
    root['seed']=seed;root['frond_count']=nfr;root['not_species_calibrated']=True
    material_adjustments();return root


class SupportGrid:
    def __init__(self,xmin,xmax,ymin,ymax,n=480,bvhs=None,base_func=B.soil_z):
        self.xmin=xmin;self.xmax=xmax;self.ymin=ymin;self.ymax=ymax;self.n=n
        self.xs=np.linspace(xmin,xmax,n);self.ys=np.linspace(ymin,ymax,n);xx,yy=np.meshgrid(self.xs,self.ys)
        try:self.h=base_func(xx,yy)
        except TypeError:self.h=np.array([[base_func(float(x),float(y)) for x in self.xs] for y in self.ys])
        self.h=np.asarray(self.h,np.float64)
        if bvhs:
            for y in range(n):
                for x in range(n):
                    for tree in bvhs:
                        hit,normal,_,_=tree.ray_cast(Vector((float(self.xs[x]),float(self.ys[y]),30)),Vector((0,0,-1)),50)
                        if hit is not None:self.h[y,x]=max(self.h[y,x],hit.z)
        self.initial=self.h.copy()
    def sample(self,co):
        u=np.clip((co[:,0]-self.xmin)/(self.xmax-self.xmin)*(self.n-1),0,self.n-1.0001);v=np.clip((co[:,1]-self.ymin)/(self.ymax-self.ymin)*(self.n-1),0,self.n-1.0001)
        i=u.astype(int);j=v.astype(int);fu=u-i;fv=v-j
        return (self.h[j,i]*(1-fu)+self.h[j,i+1]*fu)*(1-fv)+(self.h[j+1,i]*(1-fu)+self.h[j+1,i+1]*fu)*fv
    def update(self,co,faces):
        from mathutils.bvhtree import BVHTree
        tree=BVHTree.FromPolygons(co.tolist(),faces,all_triangles=False)
        lo=co.min(axis=0);hi=co.max(axis=0)
        i0=max(0,int((lo[0]-self.xmin)/(self.xmax-self.xmin)*(self.n-1))-1);i1=min(self.n-1,int((hi[0]-self.xmin)/(self.xmax-self.xmin)*(self.n-1))+1)
        j0=max(0,int((lo[1]-self.ymin)/(self.ymax-self.ymin)*(self.n-1))-1);j1=min(self.n-1,int((hi[1]-self.ymin)/(self.ymax-self.ymin)*(self.n-1))+1)
        for j in range(j0,j1+1):
            for i in range(i0,i1+1):
                hit,_,_,_=tree.ray_cast(Vector((float(self.xs[i]),float(self.ys[j]),float(hi[2]+.002))),Vector((0,0,-1)),float(hi[2]-lo[2]+.004))
                if hit is not None:self.h[j,i]=max(self.h[j,i],hit.z)


# Earlier rejected relax_leaf experiment is retained in provenance,
# not as a shadowed definition in the executable module.


def litter_patch(col,stem,vein,grid,count=370,seed=3811):
    r=random.Random(seed);mesh=B.Mesh('REPAIR | locally relaxed litter');records=[];attempts=0
    for k in range(count*2):
        attempts+=1
        x=r.uniform(grid.xmin+.1,grid.xmax-.15);y=r.uniform(grid.ymin+.1,grid.ymax-.15)
        a=r.random()*TAU;L=r.uniform(.04,.135) if k%5 else r.uniform(.13,.19);W=L*r.uniform(.37,.61)
        d=Vector((math.cos(a),math.sin(a),r.uniform(-.045,.045)));fam='piper' if k%5 else 'cordate'
        q=B.Mesh('temp');B.leaf(q,(x,y,0),d,(0,0,1),L,W,fam,seed+31*k,B.litter_material(fam,k%6),vein,0,True,False)
        co=np.asarray(q.v,float)
        # Do not put a wide rigid leaf astride a nearly vertical root face.
        span=float(np.ptp(grid.sample(co)))
        if span>L*.34:continue
        fixed,rec=relax_leaf(co,q.f,grid,q.last_lamina_count)
        if rec['edge_strain_p95']>.05 or rec['max_edge_length_error_m']>.0012 or rec['min_centroid_clearance_m']<-.0002 or rec['median_clearance_after_m']>.018:continue
        q.v=[tuple(p) for p in fixed];merge_into(mesh,q);grid.update(fixed,q.f);rec['leaf']=k;records.append(rec)
        if len(records)>=count:break
    ob=mesh.finish(col)
    # Smaller fragments and leaf stalks make the intact leaves part of a layer,
    # instead of a repeated collection of full-sized brown props.
    det=B.Mesh('REPAIR | leaf fragments and petioles');mats=[B.litter_material('piper',i) for i in range(6)]
    for k in range(count*3):
        x=r.uniform(grid.xmin+.02,grid.xmax-.02);y=r.uniform(grid.ymin+.02,grid.ymax-.02);ang=r.uniform(0,TAU);size=r.uniform(.006,.024)
        poly=[];uv=[];n=r.randint(4,7)
        for j in range(n):
            a=ang+j*TAU/n;rad=size*r.uniform(.6,1);poly.append((x+rad*math.cos(a),y+rad*math.sin(a),0));uv.append((.4+.2*math.cos(a),.45+.2*math.sin(a)))
        co=np.array(poly);su=grid.sample(co)
        if np.ptp(su)>size*.5:continue
        co[:,2]=su+.00045+r.uniform(.0001,.0007);det.add(co,[tuple(range(n))],uv,mats[k%6],False)
    twigmat=B.plain('REPAIR | decomposing stem fragments',(.028,.018,.009),.8)
    for k in range(count//7):
        x=r.uniform(grid.xmin+.08,grid.xmax-.08);y=r.uniform(grid.ymin+.08,grid.ymax-.08);a=r.uniform(0,TAU);L=r.uniform(.025,.18)
        co=np.array([(x+math.cos(a)*L*t,y+math.sin(a)*L*t,.001*math.sin(t*math.pi)) for t in np.linspace(0,1,9)]);su=grid.sample(co)
        if np.ptp(su)>.03:continue
        co[:,2]+=float(np.max(su-co[:,2])+.001);B.tube(det,co,np.linspace(.0008,.00015,len(co)),twigmat,5)
    det.finish(col);material_adjustments()
    return ob,{'accepted':len(records),'attempts':attempts,'per_leaf':records,'fragment_target':count*3,'method':'3D metric-constrained settling with weak rest-shape penalty; steep-support rejection; sampled contacts'}


# Earlier rejected rooted_plant experiment is retained in provenance,
# not as a shadowed definition in the executable module.

# Revised solver: allow in-plane motion while resolving vertical support. The
# previous restricted-height experiment is retained above for provenance only.
def relax_leaf(co,faces,grid,lamina_faces,iterations=65):
    tf=np.asarray(faces[:lamina_faces:2],int);n=int(tf.max())+1
    rest=co[:n].copy();p=rest.copy();su=grid.sample(p);p[:,2]+=float(np.max(su-p[:,2])+.0008);start=p.copy()
    edges=np.unique(np.sort(np.concatenate([tf[:,[0,1]],tf[:,[1,2]],tf[:,[2,3]],tf[:,[3,0]],tf[:,[0,2]],tf[:,[1,3]]]),axis=1),axis=0)
    i,j=edges.T;length=np.linalg.norm(rest[j]-rest[i],axis=1);degree=np.maximum(1,np.bincount(np.r_[i,j],minlength=n))
    def project():
        diff=p[j]-p[i];dist=np.linalg.norm(diff,axis=1);c=diff*((dist-length)/np.maximum(dist,1e-9))[:,None]*.48
        acc=np.zeros_like(p);np.add.at(acc,i,c);np.add.at(acc,j,-c);p[:]+=acc/degree[:,None]*1.75
        p[:,2]=np.maximum(p[:,2],grid.sample(p)+.00065)
    for it in range(iterations):
        p[:,2]-=.00018
        for _ in range(5):project()
        # A weak long-range/rest-shape term prevents total collapse of dried
        # curls. This is intentionally not claimed to be measured leaf physics.
        delta=p-start;center=delta.mean(axis=0);p-=.003*(delta-center)
        p[:,2]=np.maximum(p[:,2],grid.sample(p)+.00065)
    for _ in range(130):project()
    # Resolve triangle interiors, then restore lengths without renewed gravity.
    for _ in range(10):
        centers=p[tf].mean(axis=1);req=grid.sample(centers)+.00038-centers[:,2];bad=req>0
        if not np.any(bad):break
        dz=np.zeros(n)
        for k in range(4):np.maximum.at(dz,tf[bad,k],req[bad])
        p[:,2]+=dz
        for __ in range(10):project()
    out=co.copy();out[:n]=p
    # Keep lower shell and attached vein displacements paired to the top mesh.
    if len(out)>=2*n:out[n:2*n]+=p-rest
    if len(out)>2*n:
        for k in range(2*n,len(out)):
            near=int(np.argmin(np.sum((rest-out[k])**2,axis=1)));out[k]+=p[near]-rest[near]
    final=np.linalg.norm(p[j]-p[i],axis=1);err=np.abs(final-length);strain=err/np.maximum(length,.00015)
    clear=p[:,2]-grid.sample(p);centers=p[tf].mean(axis=1);cc=centers[:,2]-grid.sample(centers)
    rec={'max_edge_strain':float(strain.max()),'edge_strain_p95':float(np.quantile(strain,.95)),'max_edge_length_error_m':float(err.max()),'median_clearance_before_m':float(np.median(start[:,2]-su)),'median_clearance_after_m':float(np.median(clear)),'min_vertex_clearance_m':float(clear.min()),'min_centroid_clearance_m':float(cc.min()),'rms_settling_m':float(np.sqrt(np.mean(np.sum((p-start)**2,axis=1)))),'collision_scope':'height-field vertices and face centroids; no global/self collision guarantee'}
    return out,rec

def basal_plant(col,stem,vein,seed=901,H=.8,fam='cordate',lod=False):
    r=random.Random(seed);m=B.Mesh('REPAIR | broadleaf basal plant %s'%seed);ph=r.random()*TAU
    for k in range(8+seed%4):
        a=ph+k*2.4+r.uniform(-.3,.3);d=Vector((math.cos(a),math.sin(a),0));age=k/(8+seed%4)
        root=d*.016;end=d*H*r.uniform(.22,.44)+Vector((0,0,H*r.uniform(.46,.9)*(1-.27*age)))
        pts=[root.lerp(end,float(t))+Vector((0,0,H*.05*math.sin(float(t)*math.pi))) for t in np.linspace(0,1,18)]
        B.tube(m,pts,np.linspace(.004*H,.0014*H,18),stem,8)
        L=min(.46,H*r.uniform(.30,.51));f=fam;axis=B.unit(d+Vector((0,0,r.uniform(-.25,.20))));norm=B.unit((r.uniform(-.12,.12),r.uniform(-.12,.12),1))
        B.leaf(m,end,axis,norm,L,L*(.66 if f=='cordate' else .43),f,seed+k*37,B.leafmaterial(f,'young' if k==0 else 'mature'),vein,0 if lod else 1,False,not lod)
    return m.finish(col)

# Replaces the older fixed-four-leaf lateral template. Shared original branch
# inspection assets remain untouched; this grammar is for rooted forest plants.
def rooted_plant(col,stem,vein,seed=901,H=1.5,fam='piper',lod=False):
    r=random.Random(seed);m=B.Mesh('REPAIR | rooted %s plant %s'%(fam,seed));ph=r.uniform(0,TAU);graph=[]
    lean=Vector((math.cos(ph),math.sin(ph),0))*H*r.uniform(.10,.22)
    def trunk(t):return Vector((0,0,H*t))+lean*t*t+Vector((math.sin(t*4.5+ph),math.cos(t*3.2+ph),0))*H*.017*t
    ts=np.linspace(0,1,32);B.tube(m,[trunk(float(t)) for t in ts],[H*.009*(1-.965*t)**.9*(1+.045*math.sin(t*18+ph)) for t in ts],stem,10)
    graph.append({'id':0,'parent':None,'start':[0,0,0],'end':list(trunk(1))})
    def shoot(start,direction,L,parent,sd,age):
        rr=random.Random(sd);d=B.unit(direction);side=B.unit(d.cross(Vector((0,0,1))),(1,0,0));end=start+d*L+Vector((0,0,L*rr.uniform(-.12,.12)))
        def path(t):return start.lerp(end,t)+side*(L*.10*math.sin(t*math.pi))+Vector((0,0,L*.08*math.sin(t*math.pi)))
        pts=[path(float(t)) for t in np.linspace(0,1,13)];B.tube(m,pts,np.linspace(.0018*max(.7,H*.6),.0003,len(pts)),stem,6)
        gid=len(graph);graph.append({'id':gid,'parent':parent,'start':list(start),'end':list(end)})
        n=rr.randint(4,7);steps=np.array([rr.uniform(.7,1.3)*(1-.38*k/max(1,n-1)) for k in range(n)]);levels=.12+.80*np.cumsum(steps)/steps.sum()
        for k,u in enumerate(levels):
            root=path(float(u));sg=1 if k%2 else -1
            axis=B.unit(d*.28+side*sg+Vector((0,0,rr.uniform(-.28,.24))));normal=B.unit(Vector((0,0,1))+side*sg*rr.uniform(-.42,.42))
            lng=min(.255,H*rr.uniform(.11,.18))*(1-.15*u)
            if k==n-1:lng*=.62
            if k==0 and rr.random()<.18:continue
            tip=root+axis*(.018+.012*(fam=='cordate'));B.tube(m,[root,root.lerp(tip,.5)+Vector((0,0,.005)),tip],[.00125,.0008,.0004],stem,6)
            B.leaf(m,tip,axis,normal,lng,lng*(.62 if fam=='cordate' else rr.uniform(.37,.46)),fam,sd+k*31,B.leafmaterial(fam,'young' if k==n-1 and age<.7 else 'mature'),vein,0 if lod else 1,False,not lod)
        B.tube(m,[end,end+d*.007+Vector((0,0,.003)),end+d*.012+Vector((0,0,.004))],[.0005,.0010,.0001],stem,6)
    levels=sorted(r.uniform(.17,.94) for _ in range(8+seed%4))
    for j,t in enumerate(levels):
        root=trunk(t);a=ph+j*2.399+r.uniform(-.65,.65);d=Vector((math.cos(a),math.sin(a),r.uniform(-.15,.24)))
        reach=H*r.uniform(.23,.43)*(1-.38*t);end=root+d*reach+Vector((0,0,H*r.uniform(.012,.075)))
        path=[root.lerp(end,float(u))+Vector((0,0,H*.06*math.sin(float(u)*math.pi))) for u in np.linspace(0,1,16)]
        rad=H*.004*(1-.52*t);B.tube(m,path,np.linspace(rad,.0009,len(path)),stem,8)
        gid=len(graph);graph.append({'id':gid,'parent':0,'start':list(root),'end':list(end)})
        shoot(path[10],B.unit(d+Vector((0,0,-.13))),min(.50,H*.23),gid,seed+j*157,.8-t*.5)
        for k,u in enumerate([r.uniform(.30,.49),r.uniform(.60,.79)]):
            if k==1 and j%3==0:continue
            side=Vector((-d.y,d.x,0))*(1 if k%2 else -1)
            shoot(path[int(u*15)],B.unit(d*.23+side+Vector((0,0,r.uniform(-.1,.2)))),min(.40,H*r.uniform(.14,.22)),gid,seed+j*157+77+k,.6)
    # A connected subordinate leader, rather than another floating plant.
    if seed%3!=1:
        p=trunk(.31);dd=Vector((math.cos(ph+2),math.sin(ph+2),0));tip=p+Vector((0,0,H*.48))+dd*H*.20
        ps=[p.lerp(tip,float(t))+dd*H*.05*math.sin(float(t)*math.pi) for t in np.linspace(0,1,20)]
        B.tube(m,ps,np.linspace(H*.0048,.0005,20),stem,8);gid=len(graph);graph.append({'id':gid,'parent':0,'start':list(p),'end':list(tip)})
        for k in range(3):
            u=.35+k*.25;shoot(ps[int(u*19)],B.unit(Vector((math.cos(ph+k*2),math.sin(ph+k*2),.18))),min(.42,H*.20),gid,seed+3000+k*47,.3)
    ob=m.finish(col);ob['repair_branch_graph']=json.dumps(graph,separators=(',',':'));ob['repair_branch_graph_nodes']=len(graph);return ob
