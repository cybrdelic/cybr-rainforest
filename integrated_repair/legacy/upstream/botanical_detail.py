"""V7: surface-consistent foliage, branching architectures, and instanced microflora.

Metres throughout. Morphotypes are authored approximations, not species claims.
The same anatomical coordinates drive shape, pigment, surface relief, and veins.
"""
from __future__ import annotations
import math, random, sys
from pathlib import Path
from collections import Counter
import bpy
import numpy as np
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'upstream_v6'))
import botany as B
Z=B.Z;TAU=math.tau;unit=B.unit;frame=B.frame;mix=B.mix;clamp=B.clamp;hvec=B.hvec;linspace=B.linspace
SECONDARIES=np.linspace(.13,.86,9)

class MeshBuilder(B.MeshBuilder):
    def finish(self,collection=None):
        if not self.vertices or not self.faces:return None
        p=np.asarray(self.vertices,np.float32)
        if not np.isfinite(p).all():raise ValueError('Nonfinite botanical geometry')
        me=bpy.data.meshes.new(self.name+' | mesh');me.from_pydata(self.vertices,[],self.faces)
        for key in self.keys:me.materials.append(self.materials[key])
        me.polygons.foreach_set('material_index',self.indices)
        me.polygons.foreach_set('use_smooth',np.ones(len(me.polygons),np.bool_))
        me.color_attributes.new(name='gt6_color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.asarray(self.colors,np.float32).ravel())
        me.attributes.new('gt6_wetness','FLOAT','POINT').data.foreach_set('value',np.asarray(self.wet,np.float32))
        indices=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',indices)
        uv=me.uv_layers.new(name='AnatomicalUV')
        uv.data.foreach_set('uv',np.asarray(self.uv,np.float32)[indices].ravel())
        me.update();ob=bpy.data.objects.new(self.name,me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        ob['gt7_geometry']=True;ob['gt7_counts']=str(dict(self.counts))
        return ob

class Blade:
    def __init__(self,base,axis,normal,L,W,shape,rng,dead=False,damage=.15,age=.6):
        self.base=Vector(base);self.axis,self.side,self.normal=frame(axis,normal)
        self.length=L;self.width=W;self.shape=shape
        self.phase=rng.uniform(0,TAU);self.droop=rng.uniform(.04,.20) if not dead else rng.uniform(-.25,.42)
        self.curl=rng.uniform(-.025,.07) if not dead else rng.uniform(.10,.34)
        self.twist=rng.uniform(-.07,.07);self.asym=rng.uniform(-.075,.075)
        self.bites=[]
        if rng.random()<damage:
            for k in range(rng.randint(1,3)):
                self.bites.append((rng.uniform(.30,.88),rng.choice((-1,1)),rng.uniform(.017,.07),rng.uniform(.10,.28)))
        self.lobed=(shape=='cordate' and age>.65 and rng.random()<.27)
    def profile(self,t,v=0):
        q=clamp(t,.0008,.9992)
        if self.shape=='cordate':w=math.sin(math.pi*(.14+.86*q))**.67*(1.27-.53*q)
        elif self.shape=='pinnule':w=math.sin(math.pi*q)**.69*(1.21-.50*q)
        elif self.shape=='lance':w=math.sin(math.pi*q)**.98*(1.06-.19*q)
        else:w=math.sin(math.pi*q)**.78*(1.06-.10*q)
        w*=1+self.asym*(1 if v>0 else -1)*math.sin(math.pi*q)
        if self.lobed and .12<t<.86:
            w*=1-.27*(max(0,math.sin((t-.08)*math.pi*6.8)))**5
        if self.shape=='pinnule':w*=1+.065*math.sin(56*t+self.phase)
        for center,sgn,radius,depth in self.bites:
            if v*sgn>0:w*=1-depth*math.exp(-((t-center)/radius)**4)
        return w
    def pos(self,t,v):
        t=float(t);v=float(v);w=self.width*.5*self.profile(t,v)
        lon=t
        if self.shape=='cordate':lon-=.20*math.sin(math.pi*abs(v))**.8*(1-t)**4
        driptip=.035*max(0,(t-.86)/.14)**2
        # Tissue lies between supporting veins; folds are not isotropic noise.
        supporting=.006*self.width*math.sin((t-.13-.108*abs(v)**1.62)*math.pi/.09125)*math.sin(math.pi*abs(v))
        curl=self.width*self.curl*abs(v)**3*math.sin(math.pi*t)
        lift=self.length*(.065*math.sin(math.pi*t)-self.droop*t*t-driptip)+curl+self.twist*self.width*v*t+supporting
        return self.base+self.axis*self.length*lon+self.side*(v*w)+self.normal*lift
    def n(self,t,v):
        dt=self.pos(clamp(t+.0007),v)-self.pos(clamp(t-.0007),v)
        dv=self.pos(t,clamp(v+.0007,-1,1))-self.pos(t,clamp(v-.0007,-1,1))
        n=unit(dt.cross(dv),self.normal)
        return n if n.dot(self.normal)>0 else -n

def blade(mesh,rng,base,axis,normal,length,width,shape='elliptic',detail=1,age=.55,dead=False,damage=.15,skeleton=False,veins=True):
    ev=Blade(base,axis,normal,length,width,shape,rng,dead,damage,age)
    rows,cols=((30,12) if detail==2 else (14,6) if detail==1 else (6,2))
    green=mix((.084,.139,.022),(.022,.078,.013),clamp(age))
    if dead:green=mix((.13,.063,.023),(.036,.021,.010),age)
    wet=clamp(.58+rng.uniform(-.14,.15));start=len(mesh.vertices)
    if not skeleton:
        for i in range(rows+1):
            t=i/rows
            for j in range(cols+1):
                v=2*j/cols-1
                edge=max(0,(abs(v)-.89)/.11)*max(0,age-.68)*.45
                scar=0.
                for center,sgn,radius,depth in ev.bites:
                    if v*sgn>0:scar=max(scar,math.exp(-((t-center)/(radius*1.7))**4)*max(0,(abs(v)-.76)/.24)*.82)
                tone=.97+.017*math.sin(t*17+v*3+ev.phase)
                color=mix(tuple(k*tone for k in green),(.104,.055,.013),max(edge,scar))
                mesh.v(ev.pos(t,v),color,(v*.5+.5,t),wet)
        for i in range(rows):
            for j in range(cols):
                q=start+i*(cols+1)+j;mesh.f((q,q+cols+1,q+cols+2,q+1),'dead' if dead else 'leaf')
        mesh.counts['laminae']+=1
        mesh.counts['contour_bites']+=len(ev.bites)
        if ev.lobed:mesh.counts['mature_lobed_leaves']+=1
    vascular='dry_fibre' if dead else 'vein'
    veincolor=mix(green,(.092,.125,.040),.18) if not dead else (.064,.037,.018)
    if veins:
        r=length*(.0015 if detail else .0010)
        steps=linspace(.002,.997,23 if detail else 7)
        mesh.tube([ev.pos(t,0)+ev.n(t,0)*r*.40 for t in steps],[r*(1-.83*t) for t in steps],vascular,4 if detail else 3,veincolor)
        if detail==2 or skeleton:
            for t0 in SECONDARIES:
                for sign in (-1,1):
                    us=linspace(0,1,9)
                    path=[ev.pos(float(t0+.108*u**1.62),sign*.97*u)+ev.n(float(t0+.108*u**1.62),sign*.97*u)*r*.19 for u in us]
                    mesh.tube(path,[r*.32*(1-.89*u) for u in us],vascular,3,veincolor)
                    mesh.counts['geometric_secondary_veins']+=1
            if skeleton:
                for k,t0 in enumerate(SECONDARIES[:-1]):
                    gap=float(SECONDARIES[k+1]-t0)
                    for sign in (-1,1):
                        for u0 in (.22,.42,.62,.82):
                            path=[]
                            for q in linspace(0,1,5):
                                u=u0+.04*math.sin(math.pi*q);t=float(t0+.108*u**1.62+gap*q)
                                path.append(ev.pos(t,sign*.97*u))
                            mesh.tube(path,r*.105,vascular,3,veincolor)
                            mesh.counts['connected_skeleton_crossveins']+=1
        if detail==2 and not skeleton:
            # A curved rolled margin has a real silhouette at grazing angles.
            for side in (-1,1):
                ts=linspace(.002,.998,35)
                mesh.tube([ev.pos(t,side) for t in ts],max(.00003,length*.00030),vascular,3,green)
            mesh.counts['rolled_leaf_margins']+=2
    mesh.counts['skeletonized_leaves' if skeleton else 'dead_leaves' if dead else 'live_leaves']+=1
    return ev

def make_materials(assets:Path):
    materials=B.make_materials()
    pigment=bpy.data.images.load(str(assets/'leaf_pigment_multiplier.png'),check_existing=True)
    height=bpy.data.images.load(str(assets/'leaf_vein_height16.png'),check_existing=True)
    state=bpy.data.images.load(str(assets/'leaf_tissue_state.png'),check_existing=True)
    for im in (pigment,height,state):im.colorspace_settings.name='Non-Color';im.pack()
    for key,m in materials.items():
        m.name='GT7 | '+key
        if key not in ('leaf','dead'):continue
        ns=m.node_tree.nodes;ln=m.node_tree.links;ns.clear()
        out=ns.new('ShaderNodeOutputMaterial');bs=ns.new('ShaderNodeBsdfPrincipled')
        attr=ns.new('ShaderNodeAttribute');attr.attribute_name='gt6_color'
        uv=ns.new('ShaderNodeUVMap');uv.uv_map='AnatomicalUV'
        tex=[]
        for im in (pigment,height,state):
            n=ns.new('ShaderNodeTexImage');n.image=im;n.interpolation='Linear';n.extension='EXTEND';ln.new(uv.outputs['UV'],n.inputs['Vector']);tex.append(n)
        col=ns.new('ShaderNodeMixRGB');col.blend_type='MULTIPLY';col.inputs[0].default_value=1
        ln.new(attr.outputs['Color'],col.inputs[1]);ln.new(tex[0].outputs['Color'],col.inputs[2])
        geom=ns.new('ShaderNodeNewGeometry')
        back=ns.new('ShaderNodeMixRGB');back.blend_type='MULTIPLY';back.inputs[0].default_value=.45;back.inputs[2].default_value=(1.17,1.09,.89,1)
        ln.new(col.outputs[0],back.inputs[1])
        sides=ns.new('ShaderNodeMixRGB');ln.new(geom.outputs['Backfacing'],sides.inputs[0]);ln.new(col.outputs[0],sides.inputs[1]);ln.new(back.outputs[0],sides.inputs[2]);ln.new(sides.outputs[0],bs.inputs['Base Color'])
        sep=ns.new('ShaderNodeSeparateColor');ln.new(tex[2].outputs[0],sep.inputs[0])
        rough=ns.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1
        rough.inputs['To Min'].default_value=.20 if key=='leaf' else .71;rough.inputs['To Max'].default_value=.56 if key=='leaf' else .91
        ln.new(sep.outputs['Red'],rough.inputs['Value']);ln.new(rough.outputs[0],bs.inputs['Roughness'])
        bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.38;bump.inputs['Distance'].default_value=.00070 if key=='leaf' else .00095
        ln.new(tex[1].outputs[0],bump.inputs['Height']);ln.new(bump.outputs['Normal'],bs.inputs['Normal'])
        bs.inputs['IOR'].default_value=1.43;bs.inputs['Specular IOR Level'].default_value=.30 if key=='leaf' else .22
        if key=='leaf':
            bs.inputs['Coat Weight'].default_value=.10;bs.inputs['Coat Roughness'].default_value=.24
            tr=ns.new('ShaderNodeBsdfTranslucent');ln.new(sides.outputs[0],tr.inputs['Color']);ln.new(bump.outputs['Normal'],tr.inputs['Normal'])
            thin=ns.new('ShaderNodeMapRange');thin.inputs['To Min'].default_value=.25;thin.inputs['To Max'].default_value=.13;ln.new(sep.outputs['Green'],thin.inputs['Value'])
            mixn=ns.new('ShaderNodeMixShader');ln.new(thin.outputs[0],mixn.inputs[0]);ln.new(bs.outputs[0],mixn.inputs[1]);ln.new(tr.outputs[0],mixn.inputs[2]);ln.new(mixn.outputs[0],out.inputs['Surface'])
        else:ln.new(bs.outputs[0],out.inputs['Surface'])
    return materials

def broadleaf(mesh,seed,variant):
    rng=random.Random(seed);groups=2 if variant%2==0 else 3
    for generation in range(groups):
        a=rng.random()*TAU;offset=hvec(a)*rng.uniform(.025,.10);size=1 if generation==0 else rng.uniform(.38,.64)
        rhizome=[offset-Z*.005,offset+Z*.045*size,offset+Z*.08*size]
        mesh.tube(rhizome,[.018*size,.014*size,.011*size],'stem',7)
        count=10 if generation==0 else 6
        for i in range(count):
            a=i*2.39996+generation*1.7+rng.uniform(-.25,.25);d=hvec(a);age=.22+.73*i/(count-1)
            L=rng.uniform(.27,.46)*size;shape='cordate' if variant%3!=1 else 'lance'
            tip=offset+d*rng.uniform(.14,.34)*size+Z*rng.uniform(.30,.80)*size*(1-.33*age)
            root=rhizome[1]+hvec(a)*.008*size
            B.petiole(mesh,rng,root,tip,.0045*size)
            # Smooth pulvinus and a persistent basal sheath connect blade and stem.
            mesh.tube([tip-d*.012*size,tip,tip+d*.014*size],[.004*size,.0048*size,.0026*size],'stem',6)
            blade(mesh,rng,tip,unit(d+Z*rng.uniform(-.36,.12)),Z,L,L*(.74 if shape=='cordate' else .32),shape,2 if generation==0 else 1,age,damage=.27)
            if i%3==0:blade(mesh,rng,root,Z+d*.15,d,.095*size,.021*size,'lance',1,.9,True,.38)
        top=offset+Z*.68*size;B.petiole(mesh,rng,rhizome[0],top,.003*size)
        B.bud(mesh,top,Z+hvec(a)*.12,.11*size,rng)
        mesh.counts['offset_basal_generations']+=1

def shrub(mesh,seed,variant):
    rng=random.Random(seed);H=rng.uniform(1.5,1.95);phase=rng.random()*TAU
    stems=2+(variant%2)
    for k in range(stems):
        d=hvec(phase+k*2.28);h=H*(1-.21*k)
        spine=[d*(.16*t+.11*t*t)+Z*h*t for t in linspace(0,1,18)]
        mesh.tube(spine,[.010*(1-.87*t) for t in linspace(0,1,18)],'stem',6,(.042,.047,.020))
        for j in range(3,16,2):
            root=spine[j];a=phase+j*2.39996+k;out=hvec(a);lateral=hvec(a+math.pi/2)
            reach=rng.uniform(.24,.46)*(1-.22*j/17);tip=root+out*reach+Z*rng.uniform(.09,.27)
            axis=unit(tip-root)
            path=[root.lerp(tip,t)+Z*.035*math.sin(math.pi*t) for t in linspace(0,1,9)]
            mesh.tube(path,[.0035*(1-.88*t) for t in linspace(0,1,9)],'stem',5)
            for n in range(2,8):
                center=path[n];sign=(-1)**n
                stem_axis=unit(axis*.42+lateral*sign*.75+Z*.08)
                p=center+stem_axis*rng.uniform(.025,.046)
                B.petiole(mesh,rng,center,p,.0014)
                L=rng.uniform(.10,.19)*(1-.22*n/8)
                blade(mesh,rng,p,stem_axis,Z,L,L*(.40 if variant%2 else .55),'lance' if variant%2 else 'elliptic',1,rng.uniform(.3,.9),damage=.22)
                if n%3==0:
                    short=p+out*rng.uniform(.065,.12)+Z*.022
                    mesh.tube([center,p,short],[.0016,.0010,.0002],'stem',4)
                    for sg in (-1,1):
                        sax=unit(out*.5+lateral*sg)
                        blade(mesh,rng,short,sax,Z,L*.62,L*.30,'elliptic',1,.3,damage=.08)
                    B.bud(mesh,short,out,.014,rng)
                    mesh.counts['tertiary_shoots']+=1
            B.bud(mesh,tip,axis,.027,rng);mesh.counts['secondary_shoots']+=1
        B.bud(mesh,spine[-1],Z,.035,rng)
    mesh.counts['woody_stems']+=stems

def microflora(mesh,seed,variant):
    """One reusable 5–9 cm colony, rooted at z=0 and growing toward +Z."""
    rng=random.Random(seed)
    if variant<3:
        for i in range(37+variant*8):
            a=rng.random()*TAU;r=.045*math.sqrt(rng.random());root=hvec(a)*r
            h=rng.uniform(.012,.035);axis=unit(Z+hvec(a)*rng.uniform(.05,.38))
            pts=[root+axis*h*t+hvec(a+.8)*h*.13*math.sin(math.pi*t) for t in linspace(0,1,6)]
            mesh.tube(pts,[.00042*(1-.81*t) for t in linspace(0,1,6)],'moss',3,(.026,.052,.012))
            side=frame(axis)[1]
            for j in range(2,10):
                t=j/11;phi=j*2.39996+a;d=frame(axis)[1]*math.cos(phi)+frame(axis)[2]*math.sin(phi)
                before=len(mesh.faces);L=h*rng.uniform(.20,.34)
                blade(mesh,rng,root+axis*h*t,unit(d*.61+axis*.68),Z,L,L*.29,'lance',0,.72,veins=False,damage=0)
                for q in range(before,len(mesh.faces)):mesh.indices[q]=mesh.lookup['moss']
            mesh.counts['microflora_shoots']+=1
            if i%19==0:
                end=root+axis*h*1.9
                mesh.tube([pts[-1],end],[.00030,.00018],'dry_fibre',3,(.12,.05,.017));B.bud(mesh,end,axis,.0032,rng,False)
                mesh.counts['sporophyte_capsules']+=1
    elif variant==3:
        for branch in range(14):
            phi=branch*2.39996;d=hvec(phi);L=rng.uniform(.022,.056);side=hvec(phi+math.pi/2);start=len(mesh.vertices)
            for i in range(11):
                t=i/10
                for j in range(5):
                    v=(j-2)/2;w=L*.14*math.sin(math.pi*(.1+.8*t))*(1+.14*math.sin(t*27+phi))
                    pos=d*L*t+side*w*v+Z*(.0015+.003*abs(v)**2+.004*math.sin(t*math.pi))
                    mesh.v(pos,(.033,.067,.022),(j/4,t),.7)
            for i in range(10):
                for j in range(4):
                    q=start+i*5+j;mesh.f((q,q+5,q+6,q+1),'moss')
            mesh.counts['liverwort_ribbons']+=1
    else:
        for k in range(7):
            a=k*TAU/7;d=hvec(a);side=hvec(a+math.pi/2);L=rng.uniform(.035,.082)
            def p(u):return d*L*u+Z*(.006+L*(.42*math.sin(u*math.pi*.86)-.04*u))
            mesh.tube([p(t) for t in linspace(0,1,14)],[.00065*(1-.88*t) for t in linspace(0,1,14)],'stem',3)
            for j in range(2,12):
                u=j/13
                for sg in (-1,1):
                    l=L*.17*math.sin(math.pi*u)**.7
                    blade(mesh,rng,p(u),unit(side*sg+d*.26+Z*.16),Z,l,l*.39,'pinnule',0,.69,damage=0,veins=False)
            mesh.counts['micro_fern_fronds']+=1

def fungus(mesh,rng,p,n,size):
    """Small gilled mushroom, with a continuous stem, cap rim and radial gills."""
    p=Vector(p);n=unit(n);axis=unit(Z*.76+n*.24);ax,s,u=frame(axis)
    H=size*rng.uniform(1.5,2.1);tip=p+axis*H
    mesh.tube([p,p+axis*H*.5+s*size*.08,tip],[size*.10,size*.08,size*.095],'fungus',6,(.12,.088,.052))
    start=len(mesh.vertices);N=32;R=10;tone=rng.uniform(.7,1.2)
    for i in range(R+1):
        t=.001+.999*i/R;r=size*t
        for j in range(N):
            a=j*TAU/N;pos=tip+(s*math.cos(a)+u*math.sin(a))*r+axis*size*(.45*math.sqrt(max(0,1-t*t))-.10*t*t)
            color=mix((.048,.025,.014),(.15*tone,.095*tone,.054*tone),t**.8)
            mesh.v(pos,color,(j/N,t),.4)
        if i:
            for j in range(N):
                q=start+(i-1)*N+j;qq=start+(i-1)*N+(j+1)%N;mesh.f((q,qq,qq+N,q+N),'fungus')
    for j in range(32):
        a=j*TAU/32;d=s*math.cos(a)+u*math.sin(a)
        path=[tip+d*size*t-axis*size*(.11+.06*math.sin(math.pi*t)) for t in linspace(.13,.98,8)]
        mesh.tube(path,size*.009,'fungus',3,(.17,.129,.076))
    mesh.counts['gilled_mushrooms']+=1

def install():
    """Upgrade shared geometry entry points, leaving placement and source assets intact."""
    B.blade=blade;B.broadleaf=broadleaf;B.shrub=shrub;B.MeshBuilder=MeshBuilder
