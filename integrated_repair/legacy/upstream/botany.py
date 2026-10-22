"""GREEN TERROR v6: connected botanical architecture and microhabitats.

All additions are procedural mesh geometry. The host forest retains its original
assets. World units are metres; morphological families are not calibrated species.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import math, random, hashlib
import bpy
import numpy as np
from mathutils import Vector
Z=Vector((0,0,1));TAU=math.tau

def linspace(a,b,n):return [float(v) for v in np.linspace(a,b,n)]
def unit(v,fallback=(0,0,1)):
    v=Vector(v)
    return v.normalized() if v.length_squared>1e-16 else Vector(fallback)
def frame(axis,up=Z):
    a=unit(axis);n=Vector(up)-a*Vector(up).dot(a)
    if n.length_squared<1e-8:
        v=Vector((1,0,0)) if abs(a.x)<.8 else Vector((0,1,0));n=v-a*v.dot(a)
    n.normalize();return a,unit(n.cross(a)),n
def clamp(v,lo=0.,hi=1.):return min(hi,max(lo,v))
def mix(a,b,t):return tuple(x*(1-t)+y*t for x,y in zip(a,b))
def hvec(a):return Vector((math.cos(a),math.sin(a),0))
def habitat(p):
    x,y,z=p
    return clamp(.51+.18*math.sin(x*.81+y*.33)+.14*math.cos(y*1.27-x*.23)-.035*z)

class MeshBuilder:
    """Merged mesh with meaningful pigment and wetness state. No per-leaf objects."""
    def __init__(self,name,materials):
        self.name=name;self.materials=materials;self.keys=list(materials)
        self.lookup={k:i for i,k in enumerate(self.keys)}
        self.vertices=[];self.faces=[];self.indices=[];self.colors=[];self.uv=[];self.wet=[]
        self.counts=Counter()
    def v(self,p,color=(.05,.10,.02),uv=(0,0),wet=.3):
        index=len(self.vertices);self.vertices.append(tuple(p));self.colors.append((*color,1.))
        self.uv.append(tuple(uv));self.wet.append(float(wet));return index
    def f(self,indices,key):
        if len(set(indices))<3:return
        self.faces.append(tuple(indices));self.indices.append(self.lookup[key])
    def tube(self,points,radii,key='stem',sides=5,color=(.045,.073,.022)):
        points=[Vector(p) for p in points]
        if len(points)<2:return
        radii=[radii]*len(points) if isinstance(radii,(int,float)) else radii
        previous=None;rings=[]
        for i,(p,r) in enumerate(zip(points,radii)):
            t=unit(points[min(len(points)-1,i+1)]-points[max(0,i-1)])
            if previous is None:_,side,n=frame(t)
            else:side=unit(previous-t*previous.dot(t),frame(t)[1]);n=unit(t.cross(side))
            previous=side
            ring=[self.v(p+(side*math.cos(j*TAU/sides)+n*math.sin(j*TAU/sides))*max(float(r),1e-6),color,(i/max(1,len(points)-1),j/sides)) for j in range(sides)]
            rings.append(ring)
            if i:
                for j in range(sides):self.f((rings[-2][j],rings[-2][(j+1)%sides],ring[(j+1)%sides],ring[j]),key)
        self.f(tuple(reversed(rings[0])),key);self.f(tuple(rings[-1]),key)
    def finish(self,collection=None):
        if not self.vertices:return None
        vertices=np.asarray(self.vertices,np.float32)
        if not np.isfinite(vertices).all():raise ValueError('Nonfinite generated vertices')
        me=bpy.data.meshes.new(self.name+' | mesh');me.from_pydata(self.vertices,[],self.faces)
        for k in self.keys:me.materials.append(self.materials[k])
        me.polygons.foreach_set('material_index',self.indices)
        me.polygons.foreach_set('use_smooth',np.ones(len(me.polygons),dtype=np.bool_))
        me.color_attributes.new(name='gt6_color',type='FLOAT_COLOR',domain='POINT').data.foreach_set('color',np.asarray(self.colors,np.float32).ravel())
        me.attributes.new('gt6_wetness','FLOAT','POINT').data.foreach_set('value',np.asarray(self.wet,np.float32))
        # Shaders use actual pigment attributes and object coordinates. Unused
        # per-corner UV buffers are intentionally not allocated in this snapshot.
        me.update();ob=bpy.data.objects.new(self.name,me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        ob['gt6_geometry']=True;ob['gt6_counts']=str(dict(self.counts));return ob

@dataclass
class Blade:
    base:Vector
    axis:Vector
    normal:Vector
    length:float
    width:float
    shape:str='elliptic'
    curl:float=.07
    droop:float=.10
    twist:float=.07
    phase:float=0.
    def __post_init__(self):
        self.base=Vector(self.base);self.axis,self.side,self.normal=frame(self.axis,self.normal)
    def profile(self,t):
        t=clamp(t,.001,.999)
        if self.shape=='cordate':return math.sin(math.pi*(.16+.84*t))**.62*(1.25-.45*t)
        if self.shape=='lance':return math.sin(math.pi*t)**.91*(1.08-.18*t)
        if self.shape=='pinnule':return math.sin(math.pi*t)**.66*(1.35-.66*t)
        return math.sin(math.pi*t)**.70*(1.12-.21*t)
    def pos(self,t,v):
        t=float(t);v=float(v);w=self.width*.5*self.profile(t)
        asymmetry=1+.044*math.sin(t*9+self.phase)*(1 if v>0 else -1)
        if self.shape=='pinnule':asymmetry*=1+.15*math.sin(t*43+self.phase)*abs(v)**3
        longitudinal=t
        if self.shape=='cordate':longitudinal-=.18*max(0.,math.sin(math.pi*abs(v)))**.7*(1-t)**4
        p=self.base+self.axis*self.length*longitudinal+self.side*(w*v*asymmetry)
        residual=.00040*math.sin(t*61+v*5)*math.sin(math.pi*t)*math.sin(math.pi*abs(v))
        p+=self.normal*(self.length*(.105*math.sin(math.pi*t)-self.droop*t*t)+self.curl*self.width*v*v*self.profile(t)+self.twist*self.width*v*t+residual)
        return p
    def n(self,t,v):
        dt=self.pos(clamp(t+.0005),v)-self.pos(clamp(t-.0005),v)
        dv=self.pos(t,clamp(v+.001,-1,1))-self.pos(t,clamp(v-.001,-1,1))
        n=unit(dt.cross(dv),self.normal)
        return n if n.dot(self.normal)>0 else -n

def blade(mesh,rng,base,axis,normal,length,width,shape='elliptic',detail=1,age=.55,dead=False,damage=.15,skeleton=False,veins=True):
    """Lamina, damage and vascular structure share one curved surface evaluator."""
    ev=Blade(Vector(base),Vector(axis),Vector(normal),length,width,shape,rng.uniform(-.035,.14),rng.uniform(.04,.23) if not dead else rng.uniform(-.28,.40),rng.uniform(-.15,.15),rng.random()*TAU)
    rows,cols=(22,10) if detail==2 else (14,6) if detail==1 else (5,2)
    injuries=[]
    if detail>0 and rng.random()<damage:
        for _ in range(rng.randint(1,3)):injuries.append((rng.uniform(.21,.83),rng.uniform(-.87,.87),rng.uniform(.025,.065),rng.uniform(.07,.20)))
    green=mix((.12,.17,.036),(.029,.091,.016),clamp(age))
    if dead:green=mix((.17,.077,.026),(.045,.028,.016),age)
    wet=habitat(base)*rng.uniform(.6,1);start=len(mesh.vertices)
    if not skeleton:
        for i in range(rows+1):
            t=i/rows
            for j in range(cols+1):
                v=2*j/cols-1;scar=0
                for ht,hv,rx,ry in injuries:
                    distance=((t-ht)/rx)**2+((v-hv)/ry)**2
                    scar=max(scar,math.exp(-max(0,distance-1)*1.8))
                edge=clamp((abs(v)-.84)*6)*max(0,age-.65)
                patch=.91+.05*math.sin(t*37+v*13+ev.phase)+.055*math.sin(t*87-v*31)
                color=mix(tuple(k*patch for k in green),(.115,.071,.019),max(scar*.77,edge))
                mesh.v(ev.pos(t,v),color,(j/cols,t),wet)
        for i in range(rows):
            for j in range(cols):
                t=(i+.5)/rows;v=2*(j+.5)/cols-1
                if any(((t-ht)/rx)**2+((v-hv)/ry)**2<1 for ht,hv,rx,ry in injuries):
                    mesh.counts['missing_lamina_cells']+=1;continue
                q=start+i*(cols+1)+j;mesh.f((q,q+cols+1,q+cols+2,q+1),'dead' if dead else 'leaf')
        mesh.counts['laminae']+=1
    color=mix(green,(.16,.18,.065),.16) if not dead else (.075,.042,.014)
    vascular='dry_fibre' if dead else 'vein'
    if veins:
        radius=length*(.0019 if detail else .001)
        ts=linspace(.012,.995,17 if detail else 5)
        mesh.tube([ev.pos(t,0)+ev.n(t,0)*radius*.5 for t in ts],[radius*(1-.77*t) for t in ts],vascular,4 if detail else 3,color)
        if detail:
            for t0 in linspace(.14,.85,9 if detail==2 else 7):
                for sign in (-1,1):
                    steps=linspace(0,1,9)
                    path=[ev.pos(t0+.12*u**1.7,sign*.91*u)+ev.n(t0+.12*u**1.7,sign*.91*u)*radius*.21 for u in steps]
                    mesh.tube(path,[radius*.34*(1-.84*u) for u in steps],vascular,3,color)
                    mesh.counts['secondary_veins']+=1
                    if detail==2 or skeleton:
                        for u0 in (.35,.61,.78):
                            path=[]
                            for q in range(4):
                                v=q/3;t=t0+.12*u0**1.7+.058*v;cross=sign*(.91*u0+.06*math.sin(math.pi*v))
                                path.append(ev.pos(t,cross)+ev.n(t,cross)*radius*.13)
                            mesh.tube(path,[radius*.13,radius*.11,radius*.08,radius*.035],vascular,3,color)
                            mesh.counts['tertiary_veins']+=1
    mesh.counts['skeletonized_leaves' if skeleton else 'dead_leaves' if dead else 'live_leaves']+=1
    return ev

def bud(mesh,base,axis,size,rng,young=True):
    ax,side,n=frame(axis)
    for k in range(3):
        a=k*TAU/3;v=side*math.cos(a)+n*math.sin(a)
        blade(mesh,rng,base,ax+v*.13,v,size,size*.29,detail=0,age=.08 if young else .95,veins=False,dead=not young)
    mesh.counts['buds']+=1

def petiole(mesh,rng,root,end,radius=.003):
    root,end=Vector(root),Vector(end)
    path=[root.lerp(end,t)+Z*(math.sin(math.pi*t)*.05*(end-root).length) for t in linspace(0,1,8)]
    mesh.tube(path,[radius*(1-.5*i/7) for i in range(8)],'stem',5)
    mesh.counts['petiole_junctions']+=1

def broadleaf(mesh,seed,variant):
    rng=random.Random(seed);shape=('cordate','lance','elliptic','cordate')[variant%4];count=10+variant%3
    for i in range(count):
        phase=i*2.399963+rng.uniform(-.34,.34);direction=hvec(phase);age=.19+.78*i/max(1,count-1)
        length=rng.uniform(.29,.53)*(1-.27*age);reach=rng.uniform(.15,.42);height=rng.uniform(.32,.78)*(1-.38*age)
        root=hvec(phase)*rng.uniform(.006,.025);tip=root+direction*reach+Z*height
        petiole(mesh,rng,root,tip,.005*(1-.36*age))
        blade(mesh,rng,tip,unit(direction+Z*rng.uniform(-.38,.30)),Z,length,length*(.73 if shape=='cordate' else .38 if shape=='lance' else .53),shape,2,age,damage=.38)
        if i%3==0:blade(mesh,rng,root,unit(direction*.15+Z),direction,.11,.028,'lance',1,.92,True,.55)
    for k in range(2):
        a=rng.random()*TAU;tip=hvec(a)*.04+Z*rng.uniform(.60,.77)
        petiole(mesh,rng,(0,0,0),tip,.003);bud(mesh,tip,unit(Z+hvec(a)*.3),.115,rng)
    mesh.counts['basal_crowns']+=1

def shrub(mesh,seed,variant,midstory=False):
    rng=random.Random(seed);trunks=2+variant%3
    for k in range(trunks):
        angle=rng.random()*TAU;direction=hvec(angle);height=rng.uniform(1.35,2.05)
        trunk=[direction*(.18*t+.12*t*t)+Z*(height*t) for t in linspace(0,1,15)];radius=rng.uniform(.008,.017)
        mesh.tube(trunk,[radius*(1-.89*i/14) for i in range(15)],'stem',6)
        for j in range(3,13,2):
            root=trunk[j];a=angle+j*2.39996+rng.uniform(-.30,.30);side=hvec(a)
            reach=rng.uniform(.25,.58)*(1-.22*j/14);tip=root+side*reach+Z*rng.uniform(.11,.38)
            branch=[root.lerp(tip,t)+Z*(.06*math.sin(math.pi*t)) for t in linspace(0,1,7)]
            mesh.tube(branch,[.003*(1-.88*i/6) for i in range(7)],'stem',5);mesh.counts['secondary_shoots']+=1
            for m in range(3 if variant%2 else 2):
                u=.3+m*.23;p=branch[min(6,int(u*6))]
                for sign in (-1,1):
                    lateral=unit(hvec(a+sign*1.05)+Z*rng.uniform(-.1,.4));end=p+lateral*rng.uniform(.04,.075)
                    petiole(mesh,rng,p,end,.0018);length=rng.uniform(.105,.22)
                    blade(mesh,rng,end,lateral,Z,length,length*(.40 if variant%2 else .55),'lance' if variant%2 else 'elliptic',1,rng.uniform(.35,.9),damage=.27)
            bud(mesh,tip,unit(tip-root),.027,rng)
            if rng.random()<.24:mesh.tube([root,root-side*.08+Z*.035],[.0023,.0005],'dry_fibre',4,(.083,.041,.019))
        bud(mesh,trunk[-1],Z,.033,rng)
    mesh.counts['woody_stems']+=trunks

def fern(mesh,seed,variant):
    rng=random.Random(seed);fronds=10+variant%3
    for i in range(fronds):
        a=i*TAU/fronds+rng.uniform(-.15,.15);direction=hvec(a);side=hvec(a+math.pi/2);length=rng.uniform(.65,1.16)
        def point(u):return direction*(length*u)+Z*(.10+length*(.48*math.sin(u*math.pi*.79)-.18*u*u))
        mesh.tube([point(u) for u in linspace(0,1,23)],[.0042*(1-.89*u) for u in linspace(0,1,23)],'stem',5)
        for j in range(3,20):
            u=j/22;plen=length*.23*math.sin(math.pi*u)**.8
            for sign in (-1,1):
                p=point(u);pax=unit(side*sign+direction*.24+Z*.055)
                mesh.tube([p,p+pax*plen*.48,p+pax*plen],[.0012,.0007,.00018],'vein',3)
                for k in range(1,7):
                    v=k/7;center=p+pax*plen*v
                    for side2 in (-1,1):
                        axis=unit(pax*.37+direction*side2*.8+Z*.15);ln=plen*.32*math.sin(math.pi*v)**.55
                        blade(mesh,rng,center,axis,Z,ln,ln*.45,'pinnule',0,rng.uniform(.4,.85),damage=0,veins=k%2==0)
        mesh.counts['compound_fronds']+=1
    for k in range(2):
        direction=hvec(rng.random()*TAU);center=direction*.08+Z*.18
        path=[center+direction*(.055*math.sin(t))+Z*(.055*math.cos(t)+t*.004) for t in linspace(0,TAU*1.7,36)]
        mesh.tube([Vector((0,0,0)),center-Z*.08]+path,[.004,.003]+linspace(.003,.001,36),'stem',4)
        mesh.counts['fiddleheads']+=1

def palm(mesh,seed,variant):
    rng=random.Random(seed);trunk=[Z*(.15*t)+Vector((.012*math.sin(t*3),0,0)) for t in linspace(0,1,8)]
    mesh.tube(trunk,[.025*(1-.3*i/7) for i in range(8)],'stem',8)
    for j in range(9):
        a=j*2.39996+rng.uniform(-.15,.15);d=hvec(a);side=hvec(a+math.pi/2);length=rng.uniform(.7,1.15)
        def point(t):return trunk[-1]+d*length*t+Z*(length*(.63*t-.42*t*t))
        mesh.tube([point(t) for t in linspace(0,1,19)],[.006*(1-.87*t) for t in linspace(0,1,19)],'stem',5)
        for k in range(3,21):
            t=k/22;p=point(t)
            for sign in (-1,1):
                ln=.26*length*math.sin(math.pi*t)**.7;axis=unit(side*sign*.70+d*.65-Z*.13)
                blade(mesh,rng,p,axis,Z,ln,ln*.16,'lance',1,rng.uniform(.3,.9),damage=.08,veins=False)
        mesh.counts['palm_fronds']+=1
    bud(mesh,trunk[-1],Z,.52,rng)

def moss(mesh,rng,p,n,scale=1.,projector=None):
    p=Vector(p);n=unit(n);_,side,up=frame(n)
    for k in range(rng.randint(5,9)):
        a=rng.random()*TAU;root=p+(side*math.cos(a)+up*math.sin(a))*rng.uniform(0,.024)*scale
        if projector:
            seated=projector(root,n)
            if seated is None:continue
            root,localnormal=seated
        else:localnormal=n
        height=rng.uniform(.010,.026)*scale;shoot=unit(localnormal*.82+Z*.25)
        path=[root+shoot*height*t+side*(.13*height*math.sin(math.pi*t)) for t in linspace(0,1,5)]
        mesh.tube(path,[.00044*scale*(1-.81*t) for t in linspace(0,1,5)],'moss',3,(.040,.082,.015))
        for j in range(6):
            t=.20+j*.112;center=root+shoot*height*t;_,s,u=frame(shoot);a+=2.39996;d=s*math.cos(a)+u*math.sin(a)
            before=len(mesh.faces)
            blade(mesh,rng,center,unit(d*.63+shoot*.61),localnormal,height*.40,height*.13,'lance',0,.7,veins=False)
            for f in range(before,len(mesh.faces)):mesh.indices[f]=mesh.lookup['moss']
        mesh.counts['connected_moss_shoots']+=1
        if rng.random()<.075:
            tip=root+shoot*height*1.6;mesh.tube([path[-2],tip],[.00035*scale,.00020*scale],'dry_fibre',3)
            bud(mesh,tip,shoot,.003*scale,rng,False);mesh.counts['sporophytes']+=1

def lichen(mesh,rng,p,n,radius=.035):
    p=Vector(p);n=unit(n);_,s,u=frame(n)
    for j in range(rng.randint(7,12)):
        angle=rng.random()*TAU;d=s*math.cos(angle)+u*math.sin(angle);length=radius*rng.uniform(.50,1.10)
        ev=Blade(p+n*.001,d,n,length,length*.48,'elliptic',rng.uniform(.09,.25),-.02,.05,rng.random()*TAU)
        start=len(mesh.vertices);rows,cols=7,4;tone=rng.uniform(.77,1.18);color=(.128*tone,.155*tone,.098*tone)
        for i in range(rows+1):
            t=i/rows
            for k in range(cols+1):
                v=2*k/cols-1;pos=ev.pos(t,v)+n*(.002*math.sin(11*t+v*3)**2)
                mesh.v(pos,color,(k/cols,t),.3)
        for i in range(rows):
            for k in range(cols):
                q=start+i*(cols+1)+k;mesh.f((q,q+cols+1,q+cols+2,q+1),'lichen')
    mesh.counts['foliose_lichen_colonies']+=1

def bracket(mesh,rng,p,n,radius):
    p=Vector(p);n=unit(n);side=unit(Z.cross(n),(1,0,0));normal=unit(side.cross(n),Z)
    if normal.z<0:normal=-normal
    start=len(mesh.vertices);rings=8;segments=26;phase=rng.random()*TAU
    for lower in (False,True):
        for i in range(rings+1):
            u=.014+.986*i/rings
            for j in range(segments+1):
                a=(j/segments-.5)*math.pi*1.16;edge=1+.067*math.sin(7*a+phase)+.031*math.sin(17*a+phase*.73)
                pos=p+(n*math.cos(a)+side*math.sin(a))*radius*u*edge
                pos+=normal*radius*(.20*math.sin(math.pi*u*.8)-(.075*(1-u*.6) if lower else 0))
                band=.76+.20*math.sin(u*35+phase)+.055*math.sin(u*83+a*4)
                color=(.18*band,.125*band,.070*band) if not lower else (.29,.25,.16)
                mesh.v(pos,color,(j/segments,u),.15)
        block=start+(rings+1)*(segments+1)*int(lower)
        for i in range(rings):
            for j in range(segments):
                q=block+i*(segments+1)+j;face=(q,q+segments+1,q+segments+2,q+1)
                mesh.f(tuple(reversed(face)) if lower else face,'fungus')
    offset=(rings+1)*(segments+1)
    for j in range(segments):
        q=start+rings*(segments+1)+j;mesh.f((q,q+1,q+1+offset,q+offset),'fungus')
    mesh.counts['pored_brackets']+=1

def make_materials():
    result={}
    for key,rough,base in (('leaf',.39,(.027,.09,.013)),('vein',.55,(.065,.12,.022)),('stem',.63,(.048,.069,.019)),('dead',.82,(.09,.047,.019)),('dry_fibre',.88,(.092,.048,.024)),('moss',.87,(.043,.085,.017)),('lichen',.95,(.14,.17,.12)),('fungus',.69,(.20,.145,.084)),('flake',.92,(.09,.059,.032))):
        material=bpy.data.materials.new('GT6 | '+key);material.use_nodes=True;ns=material.node_tree.nodes;links=material.node_tree.links;ns.clear()
        output=ns.new('ShaderNodeOutputMaterial');bs=ns.new('ShaderNodeBsdfPrincipled')
        pigment=ns.new('ShaderNodeAttribute');pigment.attribute_name='gt6_color'
        wet=ns.new('ShaderNodeAttribute');wet.attribute_name='gt6_wetness'
        tex=ns.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=135 if key=='leaf' else 75;tex.inputs['Detail'].default_value=3
        tc=ns.new('ShaderNodeTexCoord');links.new(tc.outputs['Generated'],tex.inputs['Vector'])
        color=ns.new('ShaderNodeMixRGB');color.blend_type='MULTIPLY';color.inputs[0].default_value=.10
        links.new(pigment.outputs['Color'],color.inputs[1]);links.new(tex.outputs['Color'],color.inputs[2]);links.new(color.outputs[0],bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value=rough;bs.inputs['IOR'].default_value=1.43;bs.inputs['Specular IOR Level'].default_value=.32 if key=='leaf' else .24
        bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.21;bump.inputs['Distance'].default_value=.000055 if key in ('leaf','vein') else .00028
        links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
        if key=='leaf':
            mapping=ns.new('ShaderNodeMapRange');mapping.inputs['From Min'].default_value=0;mapping.inputs['From Max'].default_value=1
            mapping.inputs['To Min'].default_value=.52;mapping.inputs['To Max'].default_value=.30
            links.new(wet.outputs['Fac'],mapping.inputs['Value']);links.new(mapping.outputs[0],bs.inputs['Roughness'])
            bs.inputs['Coat Weight'].default_value=.12;bs.inputs['Coat Roughness'].default_value=.27
            trans=ns.new('ShaderNodeBsdfTranslucent');links.new(color.outputs[0],trans.inputs[0]);links.new(bump.outputs['Normal'],trans.inputs['Normal'])
            combine=ns.new('ShaderNodeMixShader');combine.inputs[0].default_value=.19
            links.new(bs.outputs[0],combine.inputs[1]);links.new(trans.outputs[0],combine.inputs[2]);links.new(combine.outputs[0],output.inputs['Surface'])
        else:links.new(bs.outputs[0],output.inputs['Surface'])
        material.diffuse_color=(*base,1);result[key]=material
    return result


def midstory(mesh,seed,variant,height,crown_radius):
    """Tree-scale branching with leaf dimensions kept in metres, not scaled shrubs."""
    rng=random.Random(seed);phase=rng.random()*TAU
    H=float(height);R=float(crown_radius)
    def stem(t):return hvec(phase)*(.015*H*t+.012*H*t*t)+Z*(H*t)
    trunk=[stem(t) for t in linspace(0,1,22)]
    mesh.tube(trunk,[max(.005,H*.010*(1-.91*t)**.85) for t in linspace(0,1,22)],'stem',8,(.045,.038,.024))
    mesh.counts['tree_scale_stems']+=1
    for level,f in enumerate(linspace(.43,.88,7)):
        for arm in range(2):
            angle=phase+level*2.39996+arm*2.76+rng.uniform(-.18,.18)
            direction=hvec(angle);side=hvec(angle+math.pi*.5)
            base=stem(f);length=R*rng.uniform(.62,1.02)*(1-.30*(f-.43))
            rise=H*rng.uniform(.055,.105)
            def primary(t):return base+direction*(length*t)+Z*(rise*(.30*t+.70*t*t))
            path=[primary(t) for t in linspace(0,1,11)]
            mesh.tube(path,[max(.0018,H*.0028*(1-.88*t)) for t in linspace(0,1,11)],'stem',6,(.050,.043,.027))
            mesh.counts['primary_tree_branches']+=1
            for t in (.36,.62,.86):
                for sign in (-1,1):
                    p=primary(t)
                    axis=unit(direction*.55+side*sign*.85+Z*.20)
                    shoot_length=rng.uniform(.35,.72)
                    tip=p+axis*shoot_length
                    mesh.tube([p,p.lerp(tip,.35)+Z*.015,p.lerp(tip,.70),tip],[.0048,.0031,.0018,.0005],'stem',5)
                    mesh.counts['secondary_shoots']+=1
                    for node in range(5):
                        u=.23+node*.16;junction=p.lerp(tip,u)
                        for leafside in (-1,1):
                            leaf_axis=unit(axis*.32+side*leafside*.77+Z*rng.uniform(-.1,.2))
                            attach=junction+leaf_axis*rng.uniform(.015,.035)
                            mesh.tube([junction,attach],[.0014,.0007],'stem',3)
                            L=rng.uniform(.12,.25)*(1-.14*node/4)
                            blade(mesh,rng,attach,leaf_axis,Z,L,L*(.42 if variant%2 else .54),'lance' if variant%2 else 'elliptic',0,rng.uniform(.3,.92),veins=True)
                            mesh.counts['petiole_junctions']+=1
                    bud(mesh,tip,axis,.018,rng)
            bud(mesh,path[-1],unit(path[-1]-path[-2]),.023,rng)
    bud(mesh,trunk[-1],Z,.024,rng)
