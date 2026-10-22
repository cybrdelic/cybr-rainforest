"""Shared native Blender asset library for GREEN TERROR's appearance gate.
All lengths are metres. Geometric and optical maps share the same planar domain.
Photos are used for observation only; surfaces are numerical procedural assets.
"""
from __future__ import annotations
import math, random, json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
CACHE={}

def unit(v, fallback=(0,0,1)):
    v=Vector(v)
    return v.normalized() if v.length>1e-9 else Vector(fallback)

def link_obj(name,mesh,col):
    ob=bpy.data.objects.new(name,mesh);col.objects.link(ob);return ob

def mesh_from(name,verts,faces,col,mat,uv=None):
    me=bpy.data.meshes.new(name+' geometry');me.from_pydata(verts,[],faces);me.update()
    if mat:me.materials.append(mat)
    me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
    if uv is not None:
        idx=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',idx)
        layer=me.uv_layers.new(name='Anatomical UV')
        layer.data.foreach_set('uv',np.asarray(uv,np.float32)[idx].ravel())
    return link_obj(name,me,col)

def image(name,noncolor=False):
    p=str(ROOT/'assets'/name)
    im=bpy.data.images.load(p,check_existing=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    return im

def leaf_material(family,age='mature'):
    key='A01 | '+family+' | '+age
    if bpy.data.materials.get(key):return bpy.data.materials[key]
    m=bpy.data.materials.new(key);m.use_nodes=True;ns=m.node_tree.nodes;ns.clear();ln=m.node_tree.links
    def n(t):return ns.new(t)
    def l(a,b):ln.new(a,b)
    out=n('ShaderNodeOutputMaterial');bs=n('ShaderNodeBsdfPrincipled')
    tex=n('ShaderNodeTexImage');tex.image=image(family+'_albedo.png');tex.interpolation='Cubic';tex.extension='EXTEND'
    data={}
    for kind in ('relief','thickness','roughness'):
        tt=n('ShaderNodeTexImage');tt.image=image(family+'_'+kind+'.png',True);tt.interpolation='Cubic';tt.extension='EXTEND';data[kind]=tt.outputs['Color']
    geo=n('ShaderNodeNewGeometry');back=n('ShaderNodeMixRGB');back.inputs[1].default_value=(1,1,1,1);back.inputs[2].default_value=(1.22,1.16,.85,1);l(geo.outputs['Backfacing'],back.inputs[0])
    mult=n('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;l(tex.outputs['Color'],mult.inputs[1]);l(back.outputs[0],mult.inputs[2])
    oi=n('ShaderNodeObjectInfo');var=n('ShaderNodeMapRange');var.inputs['To Min'].default_value=.86;var.inputs['To Max'].default_value=1.12;l(oi.outputs['Random'],var.inputs['Value'])
    tone=n('ShaderNodeMixRGB');tone.blend_type='MULTIPLY';tone.inputs[0].default_value=1;l(mult.outputs[0],tone.inputs[1]);l(var.outputs[0],tone.inputs[2])
    color=tone.outputs[0]
    if age=='bronze':
        young=n('ShaderNodeMixRGB');young.blend_type='MULTIPLY';young.inputs[0].default_value=1;l(color,young.inputs[1]);young.inputs[2].default_value=(2.2,.53,.60,1);color=young.outputs[0]
    elif age=='dry':
        dry=n('ShaderNodeMixRGB');dry.blend_type='MULTIPLY';dry.inputs[0].default_value=1;l(color,dry.inputs[1]);dry.inputs[2].default_value=(4.0,.52,1.05,1);color=dry.outputs[0]
    l(color,bs.inputs['Base Color']);l(data['roughness'],bs.inputs['Roughness'])
    if age=='dry':
        for edge in list(bs.inputs['Roughness'].links):ln.remove(edge)
        bs.inputs['Roughness'].default_value=.74
    bs.inputs['IOR'].default_value=1.45;bs.inputs['Specular IOR Level'].default_value=.45
    bs.inputs['Coat Weight'].default_value=.025;bs.inputs['Coat Roughness'].default_value=.32
    # Vein relief in physical metres, not exaggerated leaf-wide ridges.
    bump=n('ShaderNodeBump');bump.inputs['Distance'].default_value=.000065;bump.inputs['Strength'].default_value=.38;l(data['relief'],bump.inputs['Height'])
    noise=n('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1600;noise.inputs['Detail'].default_value=2
    tc=n('ShaderNodeTexCoord');l(tc.outputs['Object'],noise.inputs['Vector'])
    crease_noise=n('ShaderNodeTexNoise');crease_noise.inputs['Scale'].default_value=48;crease_noise.inputs['Detail'].default_value=3
    l(tc.outputs['UV'],crease_noise.inputs['Vector'])
    crease=n('ShaderNodeBump');crease.inputs['Distance'].default_value=.00012;crease.inputs['Strength'].default_value=.55;l(crease_noise.outputs['Fac'],crease.inputs['Height']);l(bump.outputs['Normal'],crease.inputs['Normal'])
    fine=n('ShaderNodeBump');fine.inputs['Distance'].default_value=.000008;fine.inputs['Strength'].default_value=.30;l(noise.outputs['Fac'],fine.inputs['Height']);l(crease.outputs['Normal'],fine.inputs['Normal']);l(fine.outputs['Normal'],bs.inputs['Normal'])
    tr=n('ShaderNodeBsdfTranslucent');l(color,tr.inputs['Color']);l(fine.outputs['Normal'],tr.inputs['Normal'])
    trans=n('ShaderNodeMapRange');trans.inputs['From Min'].default_value=.25;trans.inputs['From Max'].default_value=1;trans.inputs['To Min'].default_value=.24;trans.inputs['To Max'].default_value=.055;l(data['thickness'],trans.inputs['Value'])
    mix=n('ShaderNodeMixShader');l(trans.outputs[0],mix.inputs[0]);l(bs.outputs[0],mix.inputs[1]);l(tr.outputs[0],mix.inputs[2]);l(mix.outputs[0],out.inputs['Surface'])
    m['source']='Procedural vein graph: coupled pigment/roughness/thickness/normal, no photographs';return m

def plain_material(name,color,rough=.55):
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
    return mat

def stem_material():
    m=plain_material('A01 | living stem',(.035,.060,.012),.53)
    if m.get('ready'):return m
    ns=m.node_tree.nodes;ln=m.node_tree.links;bs=ns.get('Principled BSDF')
    tc=ns.new('ShaderNodeTexCoord');v=ns.new('ShaderNodeVectorMath');v.operation='MULTIPLY';v.inputs[1].default_value=(70,70,7);ln.new(tc.outputs['Object'],v.inputs[0])
    tex=ns.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=1;tex.inputs['Detail'].default_value=3;ln.new(v.outputs[0],tex.inputs['Vector'])
    ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.026,.037,.009,1);ramp.color_ramp.elements[1].color=(.075,.105,.026,1);ln.new(tex.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
    b=ns.new('ShaderNodeBump');b.inputs['Distance'].default_value=.00007;b.inputs['Strength'].default_value=.26;ln.new(tex.outputs['Fac'],b.inputs['Height']);ln.new(b.outputs[0],bs.inputs['Normal']);m['ready']=True
    return m

def tube(name,path,radii,col,mat=None,sides=10):
    path=[Vector(p) for p in path];verts=[];faces=[];prev=None
    if isinstance(radii,(float,int)):radii=[radii]*len(path)
    for k,(p,r) in enumerate(zip(path,radii)):
        d=unit(path[min(k+1,len(path)-1)]-path[max(k-1,0)])
        side=unit(d.cross(Vector((0,0,1)) if abs(d.z)<.95 else Vector((0,1,0)))) if prev is None else unit(prev-d*prev.dot(d))
        normal=unit(d.cross(side));prev=side
        for j in range(sides):
            th=j*math.tau/sides;rad=r*(1+.022*math.sin(3*th+k*.11))
            verts.append(tuple(p+(side*math.cos(th)+normal*math.sin(th))*rad))
            if k: a=(k-1)*sides+j;b=k*sides+j;faces.append((a,(k-1)*sides+(j+1)%sides,k*sides+(j+1)%sides,b))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple(range((len(path)-1)*sides,len(path)*sides))])
    return mesh_from(name,verts,faces,col,mat or stem_material())

def leaf_surface(fam,variant):
    data=np.load(ROOT/'assets'/f'{fam}.npz');xy=data['xy'];x=xy[:,0];t=xy[:,1]
    phase=.65+variant*1.127
    # Rest shape: one coherent longitudinal arc, smooth transverse camber,
    # asymmetric torsion and narrow vein-supported intercostal relief.
    sag=(.040+.025*math.sin(phase))*np.sin(np.pi*t)-(.10+.09*math.sin(phase*.83))*t*t
    camber=-(.24+.10*math.cos(phase))*x*x
    camber+=.018*np.sin(x*6+t*3+phase)*np.sin(np.pi*np.clip(t,0,1))
    twist=(.10*math.sin(phase)+.18*t*math.cos(phase*.8))*x
    margin=.008*np.sin(7*t+phase)*(np.abs(x)/.45)**3
    panel=.018*np.minimum(data['panel_distance']/.012,1)**1.4*np.sin(np.pi*np.clip(t,0,1))
    # Reduced panel amplitude: millimetre scale on a 25cm blade.
    z=sag+camber+twist+margin+panel*.055+data['relief']*.00025
    co=np.c_[x,t,z].astype(np.float32)
    co[:,0]*=1+.13*math.sin(phase)+.06*t*math.cos(phase)
    co[:,0]+= .022*np.sin(t*math.pi)*math.sin(phase)
    co[:,1]+= .055*x*math.sin(phase*.7)*(1-t)**2
    co[:,1]+= .060*np.maximum(-t,0)*math.sin(phase*.6)
    return data,co

def leaf_template(fam,variant=0,age='mature'):
    key=(fam,variant,age)
    if key in CACHE and CACHE[key].name in bpy.data.meshes:return CACHE[key]
    data,co=leaf_surface(fam,variant)
    if age=='dry':
        x,t=co[:,0].copy(),co[:,1].copy();phase=variant*1.23
        co[:,2]+=(.16+.10*math.sin(phase))*x*x + (.06+.04*math.cos(phase))*np.sin(t*math.pi*1.4+phase)*t + .09*np.abs(x)**1.4*np.sin(t*7+phase)
    me=bpy.data.meshes.new(f'A01 blade {fam} {variant} {age}')
    # A curved two-sided thin-sheet optical model. Do not apply a thin-leaf
    # transmission BSDF twice by duplicating offset upper/lower shells.
    # Backfacing selects the underside material response on the same lamina.
    faces=data['faces'];me.from_pydata(co.tolist(),[],faces.tolist());me.update()
    me.materials.append(leaf_material(fam,age))
    me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
    ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
    uv=me.uv_layers.new(name='Anatomical UV');uv.data.foreach_set('uv',data['uv'][ids].ravel())
    me['optical_model']='curved two-sided thin sheet; not a finite-volume BSSRDF'
    me['family']=fam;me['variant']=variant;me['asset_gate']='A01';CACHE[key]=me
    return me

def leaf(name,base,direction,normal,L,col,fam='cordate',variant=0,age='mature',width_ratio=None):
    d=unit(direction);n=unit(Vector(normal)-d*Vector(normal).dot(d));side=unit(d.cross(n))
    ob=link_obj(name,leaf_template(fam,variant,age),col)
    ob.matrix_world=Matrix(((side.x,d.x,n.x,base[0]),(side.y,d.y,n.y,base[1]),(side.z,d.z,n.z,base[2]),(0,0,0,1)))
    widthscale=1 if width_ratio is None else width_ratio/({'cordate':.87,'elliptic':.60,'lance':.38}[fam])
    ob.scale=(L*widthscale,L,L)
    ob['plant_component']='leaf';ob['attachment']=list(base);return ob

def heartleaf_branch(col,origin=(0,0,0),seed=101):
    rng=random.Random(seed);origin=Vector(origin);path=[]
    for k in range(110):
        t=k/109;path.append(origin+Vector((.090*math.sin(t*3.6)-.035*t,.035*math.sin(t*4.3),t*.84)))
    tube('A01 | climbing stem',path,[.0055*(1-.65*k/109) for k in range(110)],col)
    times=[.11,.255,.40,.545,.71,.86]
    angles=[3.65,5.65,3.24,5.96,4.03,5.44]
    lengths=[.28,.25,.225,.242,.185,.15]
    for i,(t,theta,L) in enumerate(zip(times,angles,lengths)):
        p=path[round(t*109)];vec=Vector((math.cos(theta),math.sin(theta),0))
        pet=vec*(.105+.025*rng.random())+Vector((0,0,.035+rng.random()*.035));tip=p+pet
        pts=[p.lerp(tip,j/22)+Vector((0,0,.020*math.sin(math.pi*j/22))) for j in range(23)]
        tube(f'A01 | petiole {i}',pts,[.0028*(1-.47*j/22) for j in range(23)],col,sides=10)
        down=[-.52,-.73,-.27,-.64,-.42,-.18][i]
        dr=unit(vec*.75+Vector((0,-.18,down)))
        norm=unit(Vector((0,-1,.30))+vec*.25)
        leaf(f'A01 | cordate blade {i}',tip,dr,norm,L,col,'cordate',i%4)
        sheathmat=plain_material('A01 | oxidized sheath',(.12,.040,.016),.74)
        spts=[p+Vector((.004,0,k*.002)) for k in range(14)]
        tube(f'A01 | dry stipule {i}',spts,[.0025*(1-k/14) for k in range(14)],col,sheathmat,7)
        if i%2==0:
            end=p+vec*.025+Vector((0,.025,-.07))
            tube(f'A01 | aerial root {i}',[p,p.lerp(end,.4)+Vector((0,.01,0)),end],[.0014,.0009,.00020],col,plain_material('A01 | aerial root tissue',(.080,.049,.020),.8),7)
    tip=path[-1];leaf('A01 | bronze unfolding tip',tip,(-.24,-.15,1),(0,-1,0),.11,col,'lance',1,'bronze')
    return path

def woody_branch(col,origin=(0,0,0),seed=207):
    rng=random.Random(seed);o=Vector(origin);path=[o+Vector((.10*math.sin(t*3),.04*t*t,.66*t)) for t in np.linspace(0,1,55)]
    tube('A01 | juvenile woody leader',path,[.0065*(1-.88*t) for t in np.linspace(0,1,55)],col)
    for i,t in enumerate([.20,.37,.59,.73,.90]):
        p=path[int(t*54)];sg=1 if i%2 else -1;end=p+Vector((sg*rng.uniform(.20,.32),-.03,.09))
        twig=[p.lerp(end,u)+Vector((0,-.012*math.sin(math.pi*u),.03*math.sin(math.pi*u))) for u in np.linspace(0,1,20)]
        tube(f'A01 | lateral shoot {i}',twig,[.0030*(1-.9*u) for u in np.linspace(0,1,20)],col)
        for j,u in enumerate([.24,.48,.73,.97]):
            q=twig[int(u*19)];sg2=1 if j%2 else -1
            ax=unit((sg*.48,sg2*.34,-.20 if j%3 else .20));L=rng.uniform(.13,.19)*(1-.20*u)
            pet=q+ax*.024
            tube(f'A01 | woody petiole {i}-{j}',[q,q.lerp(pet,.5),pet],[.0013,.0011,.00065],col, sides=7)
            leaf(f'A01 | elliptic blade {i}-{j}',pet,ax,(0,-1,.75),L,col,'elliptic',(i+j)%4)

class GeometryBatch:
    def __init__(self):self.v=[];self.f=[];self.uv=[]
    def add(self,verts,faces,uv=None):
        st=len(self.v);self.v.extend(verts);self.f.extend([tuple(st+k for k in f) for f in faces]);self.uv.extend(uv if uv is not None else [(0,0)]*len(verts))

def fern_material():
    mat=plain_material('A01 | fern pinna tissue',(.046,.119,.013),.51)
    if mat.get('ready'):return mat
    ns=mat.node_tree.nodes;ln=mat.node_tree.links;bs=ns.get('Principled BSDF');out=ns.get('Material Output')
    uv=ns.new('ShaderNodeTexCoord');noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=17;noise.inputs['Detail'].default_value=3;ln.new(uv.outputs['UV'],noise.inputs['Vector'])
    ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.029,.074,.008,1);ramp.color_ramp.elements[1].color=(.072,.154,.020,1);ln.new(noise.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
    sep=ns.new('ShaderNodeSeparateXYZ');ln.new(uv.outputs['UV'],sep.inputs[0]);sub=ns.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=.5;ln.new(sep.outputs['X'],sub.inputs[0]);ab=ns.new('ShaderNodeMath');ab.operation='ABSOLUTE';ln.new(sub.outputs[0],ab.inputs[0]);less=ns.new('ShaderNodeMath');less.operation='LESS_THAN';less.inputs[1].default_value=.018;ln.new(ab.outputs[0],less.inputs[0])
    bump=ns.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00008;bump.inputs['Strength'].default_value=.5;ln.new(less.outputs[0],bump.inputs['Height']);ln.new(bump.outputs[0],bs.inputs['Normal'])
    tr=ns.new('ShaderNodeBsdfTranslucent');ln.new(ramp.outputs[0],tr.inputs['Color']);mx=ns.new('ShaderNodeMixShader');mx.inputs[0].default_value=.18;ln.new(bs.outputs[0],mx.inputs[1]);ln.new(tr.outputs[0],mx.inputs[2]);ln.new(mx.outputs[0],out.inputs['Surface']);mat['ready']=True;return mat

def fern(col,origin=(0,0,0),seed=311,scale=1):
    rng=random.Random(seed);o=Vector(origin);batch=GeometryBatch()
    for fr in range(11):
        a=fr*2.39996+rng.uniform(-.24,.24);rad=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
        length=rng.uniform(.48,.76)*scale;rise=rng.uniform(.29,.54)*scale
        def pos(t):return o+rad*(length*(.70*t+.30*t*t))+Vector((0,0,rise*math.sin(math.pi*t*.83)+.025*scale))
        pts=[pos(t) for t in np.linspace(0,1,60)]
        tube(f'A01 | fern rachis {seed}-{fr}',pts,[scale*.0022*(1-.95*t) for t in np.linspace(0,1,60)],col,stem_material(),8)
        pairs=38
        for k in range(pairs):
            t=.11+.86*k/pairs
            plen=length*.19*math.sin(math.pi*(.10+.88*t))**.83*(1-.32*t)
            for sg in (-1,1):
                q=pos(t+(0.006 if sg==1 else 0));d=unit(rad*.27+side*sg+Vector((0,0,.03*math.sin(k))))
                across=unit(Vector((0,0,1)).cross(d));verts=[];faces=[];uv=[]
                nr,nc=22,6
                for r in range(nr+1):
                    u=r/nr;profile=math.sin(math.pi*(.025+.975*u))**.54
                    for c in range(nc+1):
                        v=c*2/nc-1
                        # Auriculate base and fine serrulation of actual silhouette.
                        aur=1+(.24 if v*sg>0 else -.07)*math.exp(-((u-.12)/.16)**2)
                        serr=1+.055*math.sin(2*math.pi*10*u+.25*sg)*abs(v)**5
                        w=plen*.15*profile*aur*serr
                        point=q+d*(u*plen)+across*(v*w)+Vector((0,0,plen*(.05*math.sin(u*math.pi)-.13*u*u+.02*v*v)))
                        verts.append(tuple(point));uv.append((c/nc,u))
                        if r and c:
                            b=(r-1)*(nc+1)+c-1;faces.append((b,b+1,b+nc+2,b+nc+1))
                batch.add(verts,faces,uv)
    ob=mesh_from(f'A01 | reference-guided fern {seed}',batch.v,batch.f,col,fern_material(),batch.uv)
    ob['reference']='Nephrolepis exaltata: pinnate fronds, asymmetric auriculate pinnae; approximation, not species-calibrated'
    # Distinct uncurling shoots, tapered rather than perfect repeated spirals.
    for j in range(2):
        a=j*2.1;h=(.20+j*.06)*scale;rad=Vector((math.cos(a),math.sin(a),0))
        pts=[o+rad*.018+Vector((0,0,h*t)) for t in np.linspace(0,1,20)]
        center=pts[-1]-rad*.018*scale
        for t in np.linspace(0,1,30):
            ang=-math.pi*.5+t*math.tau*1.30;r=.018*scale*(1-.80*t)
            pts.append(center+rad*(r*math.cos(ang))+Vector((0,0,r*math.sin(ang)+.018*scale)))
        tube(f'A01 | unfurling fern {j}',pts,[.0018*scale*(1-.85*k/(len(pts)-1)) for k in range(len(pts))],col)
    return ob
