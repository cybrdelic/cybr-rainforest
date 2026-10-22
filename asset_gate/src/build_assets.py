"""GREEN TERROR: bounded botanical asset gate, native Blender/Cycles.
Reproducible authored approximations informed by botanical references.
No AI-generated images, alpha cards, or photographic leaf textures.
"""
from __future__ import annotations
import bpy, numpy as np, math, random, json, os, sys, time, hashlib, argparse
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]; AS=ROOT/'assets'; OUT=ROOT/'renders';EV=ROOT/'evidence'
for p in (AS,OUT,EV):p.mkdir(exist_ok=True)
SEED=317291; TAU=2*math.pi
SUPPORT_BVHS=[]
PANELS={}
rng=random.Random(SEED)

# Global meshes carry UVs and material indices explicitly. Tubes share the
# same continuous frame at their ends; laminae have top/bottom/rim faces.
class Mesh:
    def __init__(self,name): self.name=name;self.v=[];self.f=[];self.uv=[];self.mi=[];self.smooth=[];self.mats=[]
    def mat(self,m):
        if m not in self.mats:self.mats.append(m)
        return self.mats.index(m)
    def add(self,verts,faces,uvs,material,smooth=True):
        off=len(self.v);self.v.extend(tuple(v) for v in verts);self.uv.extend(tuple(uv) for uv in uvs)
        self.f.extend(tuple(i+off for i in face) for face in faces);self.mi.extend([self.mat(material)]*len(faces));self.smooth.extend([smooth]*len(faces))
    def finish(self,col):
        if not self.f:return None
        data=bpy.data.meshes.new(self.name);data.from_pydata(self.v,[],self.f);data.update()
        for m in self.mats:data.materials.append(m)
        data.polygons.foreach_set('material_index',self.mi);data.polygons.foreach_set('use_smooth',self.smooth)
        uv=data.uv_layers.new(name='Anatomy');loop_idx=np.empty(len(data.loops),dtype=np.int32);data.loops.foreach_get('vertex_index',loop_idx)
        uv.data.foreach_set('uv',np.asarray(self.uv,dtype=np.float32)[loop_idx].ravel())
        ob=bpy.data.objects.new(self.name,data);col.objects.link(ob);return ob

def unit(x,fallback=(0,0,1)):
    a=Vector(x);return a.normalized() if a.length>1e-12 else Vector(fallback)
def tube(mesh,points,radii,material,sides=8):
    pts=[Vector(p) for p in points];n=len(pts)
    if n<2:return
    rs=[float(radii)]*n if np.isscalar(radii) else [float(x) for x in radii]
    vs=[];uvs=[];fs=[];axis=unit(pts[1]-pts[0]);side=unit(axis.cross(Vector((0,0,1))),(1,0,0))
    for i,p in enumerate(pts):
        tangent=unit(pts[min(n-1,i+1)]-pts[max(0,i-1)])
        side=unit(side-tangent*side.dot(tangent),(1,0,0));other=unit(tangent.cross(side))
        for j in range(sides):
            a=j*TAU/sides;vs.append(p+max(rs[i],1e-6)*(side*math.cos(a)+other*math.sin(a)));uvs.append((j/sides,i/(n-1)))
        if i:
            for j in range(sides):
                q=(i-1)*sides+j;r=(i-1)*sides+(j+1)%sides
                fs.append((q,r,r+sides,q+sides))
    fs.append(tuple(reversed(range(sides))));fs.append(tuple((n-1)*sides+j for j in range(sides)))
    mesh.add(vs,fs,uvs,material)

def plain(name,color,roughness=.55):
    m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
    return m

def imtex(nodes,path,noncolor=False):
    im=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    n=nodes.new('ShaderNodeTexImage');n.image=im;n.interpolation='Linear';n.extension='EXTEND';return n

def leafmaterial(family,age='mature'):
    name=f'GATE | {family} | {age} | thin lamina'
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name);mat.use_nodes=True;ns=mat.node_tree.nodes;ns.clear();ln=mat.node_tree.links
    def N(t):return ns.new(t)
    def L(a,b):ln.new(a,b)
    out=N('ShaderNodeOutputMaterial');bs=N('ShaderNodeBsdfPrincipled');geo=N('ShaderNodeNewGeometry')
    tex=imtex(ns,AS/f'{family}_{age}.png');under=imtex(ns,AS/f'{family}_{"dead" if age=="dead" else "underside"}.png')
    mix=N('ShaderNodeMixRGB');L(geo.outputs['Backfacing'],mix.inputs[0]);L(tex.outputs['Color'],mix.inputs[1]);L(under.outputs['Color'],mix.inputs[2]);L(mix.outputs[0],bs.inputs['Base Color'])
    rou=imtex(ns,AS/f'{family}_roughness.png',True);L(rou.outputs['Color'],bs.inputs['Roughness'])
    if family=='fern':
        rr=N('ShaderNodeMapRange');rr.inputs['From Min'].default_value=.30;rr.inputs['From Max'].default_value=.61;rr.inputs['To Min'].default_value=.52;rr.inputs['To Max'].default_value=.72;L(rou.outputs['Color'],rr.inputs['Value']);L(rr.outputs[0],bs.inputs['Roughness'])
    if age=='dead':
        rr=N('ShaderNodeMapRange');rr.inputs['From Min'].default_value=.30;rr.inputs['From Max'].default_value=.61;rr.inputs['To Min'].default_value=.70;rr.inputs['To Max'].default_value=.89;L(rou.outputs['Color'],rr.inputs['Value']);L(rr.outputs[0],bs.inputs['Roughness'])
    bs.inputs['IOR'].default_value=1.45;bs.inputs['Specular IOR Level'].default_value=.5;bs.inputs['Coat Weight'].default_value=.018 if age not in ['dead','underside'] else 0
    bs.inputs['Coat Roughness'].default_value=.34
    h=imtex(ns,AS/f'{family}_height.png',True);bump=N('ShaderNodeBump');bump.inputs['Distance'].default_value=.00040 if family!='fern' else .00008;bump.inputs['Strength'].default_value=.55;L(h.outputs['Color'],bump.inputs['Height'])
    coord=N('ShaderNodeTexCoord');noise=N('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1100;noise.inputs['Detail'].default_value=2;L(coord.outputs['Object'],noise.inputs['Vector'])
    micro=N('ShaderNodeBump');micro.inputs['Distance'].default_value=.000038;micro.inputs['Strength'].default_value=.35;L(noise.outputs['Fac'],micro.inputs['Height']);L(bump.outputs['Normal'],micro.inputs['Normal']);L(micro.outputs['Normal'],bs.inputs['Normal'])
    trans=N('ShaderNodeBsdfTranslucent');L(mix.outputs[0],trans.inputs['Color']);L(micro.outputs['Normal'],trans.inputs['Normal'])
    thick=imtex(ns,AS/f'{family}_thickness.png',True);factor=N('ShaderNodeMapRange');factor.inputs['From Min'].default_value=.25;factor.inputs['From Max'].default_value=1;factor.inputs['To Min'].default_value=.27 if age!='dead' else .13;factor.inputs['To Max'].default_value=.045
    L(thick.outputs['Color'],factor.inputs['Value']);mixbs=N('ShaderNodeMixShader');L(factor.outputs[0],mixbs.inputs[0]);L(bs.outputs[0],mixbs.inputs[1]);L(trans.outputs[0],mixbs.inputs[2]);clear=N('ShaderNodeBsdfTransparent');shell=N('ShaderNodeMixShader');L(geo.outputs['Backfacing'],shell.inputs[0]);L(mixbs.outputs[0],shell.inputs[1]);L(clear.outputs[0],shell.inputs[2]);L(shell.outputs[0],out.inputs['Surface'])
    mat['model']='Thin diffuse transmission + cuticle reflection; not measured spectral optics.'
    return mat

def litter_material(family,variant):
    name=f'GATE | {family} | decay state {variant}'
    if bpy.data.materials.get(name):return bpy.data.materials[name]
    m=leafmaterial(family,'dead').copy();m.name=name;ns=m.node_tree.nodes;ln=m.node_tree.links
    tints=[(.65,.58,.47),(1.15,.97,.65),(.87,.95,.83),(1.28,1.02,.80),(.70,.66,.63),(.94,.74,.51)]
    tint=tints[variant%6];bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');source=bs.inputs['Base Color'].links[0].from_socket
    mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*tint,1);ln.new(source,mix.inputs[1]);ln.new(mix.outputs[0],bs.inputs['Base Color'])
    for n in ns:
        if n.type=='BSDF_TRANSLUCENT':ln.new(mix.outputs[0],n.inputs['Color'])
    rough=bs.inputs['Roughness'].links[0].from_socket;mp=ns.new('ShaderNodeMapRange');mp.inputs['From Min'].default_value=.30;mp.inputs['From Max'].default_value=.61;mp.inputs['To Min'].default_value=.66+.035*(variant%3);mp.inputs['To Max'].default_value=.83+.02*(variant%3);ln.new(rough,mp.inputs['Value']);ln.new(mp.outputs[0],bs.inputs['Roughness'])
    bs.inputs['Specular IOR Level'].default_value=.28;return m

def stemmaterial():
    m=plain('GATE | stipules and bark-bearing stems',(.041,.053,.018),.66);ns=m.node_tree.nodes;ln=m.node_tree.links;bs=ns.get('Principled BSDF')
    coord=ns.new('ShaderNodeTexCoord');noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220;noise.inputs['Detail'].default_value=3
    ln.new(coord.outputs['Object'],noise.inputs['Vector']);ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.019,.026,.010,1);ramp.color_ramp.elements[1].color=(.082,.073,.031,1);ln.new(noise.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
    bump=ns.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.0001;bump.inputs['Strength'].default_value=.38;ln.new(noise.outputs['Fac'],bump.inputs['Height']);ln.new(bump.outputs['Normal'],bs.inputs['Normal']);return m

def profile(t,fam):
    t=max(.0003,min(.9997,t))
    if fam=='cordate':return math.sin(math.pi*(.09+.91*t))**.65*(1.34-.65*t)
    if fam=='fern':return math.sin(math.pi*(.035+.965*t))**.33*(1.12-.38*t)
    tip=max(0,min(1,(t-.72)/.28));tip=tip*tip*(3-2*tip)
    return math.sin(math.pi*t)**.70*(1.26-.42*t)*(1-.62*tip)

class Blade:
    def __init__(self,base,axis,normal,L,W,family,seed,dead=False):
        self.base=Vector(base);self.axis=unit(axis);self.side=unit(self.axis.cross(unit(normal)),(1,0,0));self.normal=unit(self.side.cross(self.axis));self.L=L;self.W=W;self.fam=family
        r=random.Random(seed);self.phase=r.uniform(0,TAU);self.asym=r.uniform(-.075,.075);self.twist=r.uniform(-.06,.06);self.sag=r.uniform(.018,.055) if family=='fern' else r.uniform(.06,.14);self.dead=dead;self.decay_class=seed%5
        if family not in PANELS:PANELS[family]=np.load(AS/f'{family}_panel.npy')
        self.curl=r.uniform(.012,.065) if dead else r.uniform(.015,.045)
        self.bites=[]
        if r.random()<.2 or dead:
            for _ in range(r.randrange(2,5) if dead else r.randrange(1,3)):
                self.bites.append((r.uniform(.18,.85),r.choice((-1,1)),r.uniform(.02,.07),r.uniform(.12,.42)))
    def pos(self,t,v):
        t=float(t);v=float(v)
        p=profile(t,self.fam);w=self.W*.5*p
        asym=1+self.asym*math.tanh(v*4)*math.sin(math.pi*t)
        for tt,sg,rr,dd in self.bites:
            if sg*v>0:asym*=1-dd*math.exp(-((t-tt)/rr)**2)
        if self.fam=='fern':asym*=1+.022*math.sin(t*170+self.phase)+.007*math.sin(t*340)
        lateral=w*v*asym
        lon=t
        if self.fam=='cordate':lon-=.17*math.sin(math.pi*abs(v))**.75*(1-t)**4
        if self.fam=='piper':lon+=self.asym*math.tanh(v*6)*(1-t)**4
        drop=self.L*((.018 if self.fam=='fern' else .09)*math.sin(math.pi*t)-self.sag*t*t-(.004 if self.fam=='fern' else .055)*max(0,(t-.82)/.18)**2)
        cup=self.W*self.curl*abs(v)**2.5*math.sin(math.pi*t)
        twist=self.W*self.twist*v*t**1.3
        ripple=self.W*(.008 if not self.dead else [.007,.011,.018,.026,.042][self.decay_class])*math.sin(t*(24 if not self.dead else 15)+self.phase)*abs(v)**4*math.sin(math.pi*t)
        if self.dead:
            drop+=self.L*.026*math.sin(math.pi*t)*math.sin(t*6+self.phase)
            cup+=self.W*[.006,.008,.018,.026,.033][self.decay_class]*math.sin(t*7+v*2)*v*v
        panel=PANELS[self.fam];uu=np.clip(.5+.5*v*p,0,1)*(panel.shape[1]-1);vv=(1-t)*(panel.shape[0]-1);ix=int(uu);iy=int(vv);fx=uu-ix;fy=vv-iy
        ix1=min(ix+1,panel.shape[1]-1);iy1=min(iy+1,panel.shape[0]-1)
        bulge=float((panel[iy,ix]*(1-fx)+panel[iy,ix1]*fx)*(1-fy)+(panel[iy1,ix]*(1-fx)+panel[iy1,ix1]*fx)*fy)
        cell_relief=(.00042 if self.fam!='fern' else .00008)*min(1.5,self.L/.18)*bulge
        return self.base+self.axis*(self.L*lon)+self.side*lateral+self.normal*(drop+cup+twist+ripple+cell_relief)
    def normal_at(self,t,v):
        dt=self.pos(min(.9998,t+.0004),v)-self.pos(max(.0002,t-.0004),v)
        dv=self.pos(t,min(1,v+.0004))-self.pos(t,max(-1,v-.0004))
        return unit(dv.cross(dt))

NETWORK={}
def leaf(mesh,base,axis,normal,L,W,family,seed,material,veinmat,detail=1,dead=False,major_veins=True):
    b=Blade(base,axis,normal,L,W,family,seed,dead);nt,nv=(84,22) if detail>=2 else (48,12) if detail==1 else (64,6) if family=='fern' else (32,8) if dead else (20,6)
    ts=np.linspace(.001,.999,nt+1);vs=np.linspace(-1,1,nv+1);verts=[];uvs=[];faces=[];coords=[]
    for t in ts:
        for v in vs:
            coords.append((float(t),float(v)));p=b.pos(t,v);verts.append(tuple(p));uvs.append((.5+.5*v*profile(t,family),float(t)))
    count=len(verts);thickness=.00016 if family!='fern' else .000085
    # A real double surface and closed rim, not an alpha rectangle.
    for (t,v),p in zip(coords,verts[:count]):verts.append(tuple(Vector(p)-b.normal_at(t,v)*thickness));uvs.append((.5+.5*v*profile(t,family),t))
    for i in range(nt):
        for j in range(nv):
            q=i*(nv+1)+j;r=q+nv+1
            faces.append((q,q+1,r+1,r));faces.append((q+count,r+count,r+1+count,q+1+count))
    edge=list(range(nv+1))+[i*(nv+1)+nv for i in range(1,nt+1)]+[nt*(nv+1)+j for j in range(nv-1,-1,-1)]+[i*(nv+1) for i in range(nt-1,0,-1)]
    for i,a in enumerate(edge):c=edge[(i+1)%len(edge)];faces.append((a,c,c+count,a+count))
    mesh.add(verts,faces,uvs,material)
    mesh.last_lamina_count=nt*nv*2
    under=mesh.mat(leafmaterial(family,'dead' if dead else 'underside'))
    start=len(mesh.mi)-len(faces)
    for fi in range(1,nt*nv*2,2):mesh.mi[start+fi]=under
    if major_veins:
        # Physical underside supports follow the exact atlas paths.
        net=NETWORK.get(family)
        if net is None:net=json.loads((AS/f'{family}_network.json').read_text());NETWORK[family]=net
        for path in net['major']:
            lev=path['level']
            if lev and detail<1:continue
            ps=[];radii=[]
            for u,t in path['uv'][::2]:
                t=max(.002,min(.998,t));v=max(-.98,min(.98,(u-.5)*2/max(.02,profile(t,family))))
                ps.append(b.pos(t,v)-b.normal_at(t,v)*(thickness+.00002));rad=(.00033 if lev==0 else .00012)*(L/.20)*(1-.75*t)
                radii.append(max(.000012,rad))
            tube(mesh,ps,radii,veinmat,5)
    return b

def add_collection(name,scene=None):
    c=bpy.data.collections.new(name);(scene or bpy.context.scene).collection.children.link(c);return c

def create_branch(col,stem,vein,fam='piper',seed=773):
    r=random.Random(seed);m=Mesh('GATE | branching '+fam)
    def axispath(t):return Vector((-.27+.51*t,.022*math.sin(t*3.7),.25+.18*t+.014*math.sin(t*5)))
    ts=np.linspace(0,1,42);tube(m,[axispath(t) for t in ts],[.0038*(1-.86*t) for t in ts],stem,10)
    count=0
    def put_leaf(root,direction,length,seed2,young=False):
        nonlocal count
        d=unit(direction);petlen=.018 if fam=='piper' else .037
        end=root+d*petlen+Vector((0,-.002,.004))
        tube(m,[root,root.lerp(end,.5)+Vector((0,-.003,.004)),end],[.0014,.001,.0006],stem,7)
        normal=unit((r.uniform(-.14,.14),-1,r.uniform(.12,.32)))
        leaf(m,end,d,normal,length,length*(.40 if fam=='piper' else .67),fam,seed2,leafmaterial(fam,'young' if young else 'mature'),vein,2)
        count+=1
        # Persistent curled stipule and nodal swelling at the exact junction.
        tube(m,[root-Vector((.004,0,0)),root,root+Vector((.004,0,.002))],[.0016,.0022,.0016],stem,10)
        if count%3==0:leaf(m,root,unit((.1,.1,1)),(0,-1,0),.012,.004,'piper',seed2+11,leafmaterial('piper','dead'),vein,0,True,False)
    levels=[.09,.21,.34,.47,.58,.70,.81,.91]
    for i,t in enumerate(levels):
        root=axispath(t);sg=1 if i%2 else -1
        d=unit((sg*r.uniform(.45,.86),r.uniform(-.35,.12),r.uniform(-.95,-.45)))
        put_leaf(root,d,r.uniform(.15,.215)*(1-.26*t),seed+i*31,i>5)
    for j,t in enumerate([.30,.66]):
        root=axispath(t);end=root+Vector((.10,-.035,.09 if j else -.055))
        pts=[root.lerp(end,u)+Vector((0,.012*math.sin(u*math.pi),.015*math.sin(u*math.pi))) for u in np.linspace(0,1,16)]
        tube(m,pts,np.linspace(.0024,.0005,16),stem,8)
        for k,u in enumerate([.55,.95]):
            p=pts[int(u*15)];put_leaf(p,unit(((-1 if k else 1)*.5,-.15,-.8)),.16-.035*k,seed+600+j*31+k,j==1)
        # Connected leaf bud at terminal point, not a protruding stick.
        tube(m,[end,end+Vector((.003,-.003,.008)),end+Vector((.004,-.004,.014))],[.0007,.0014,.00015],stem,8)
    ob=m.finish(col);ob['gate_leaf_count']=count;ob['family_reference']=fam;return ob

def create_fern(col,stem,vein,seed=881):
    r=random.Random(seed);m=Mesh('GATE | sword fern with attached pinnae');pinnae=[];prototype={};sori=plain('GATE | fern indusia',(.13,.077,.021),.91)
    for fr in range(7):
        a=fr*2.399+r.uniform(-.32,.32);d=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0));length=r.uniform(.67,.96)
        vigor=[.68,.90,1.02,.76,1.20,.83,.98][fr];droop=[.56,.42,.38,.63,.49,.66,.28][fr];twist=r.uniform(-.18,.18)
        def rach(t):
            t=float(t)
            return d*length*(.85*t+.09*t*t)+side*(length*twist*t*t)+Vector((0,0,length*(vigor*t-droop*t*t+.06*math.sin(math.pi*t))))
        ts=np.linspace(0,1,72);tube(m,[rach(t) for t in ts],[.0025*(1-.92*t) for t in ts],stem,9)
        n=r.randint(31,39)
        for j in range(n):
            for sg in [-1,1]:
                if fr in [0,3] and j>5 and r.random()<.025:continue
                t=.19+.78*(j+(.38 if sg==1 else 0)+r.uniform(-.09,.09))/n;root=rach(t)
                lng=length*.19*math.sin(math.pi*(t-.095)/.905)**.60*r.uniform(.93,1.07)
                sweep=.13+.13*math.sin(t*3.3+fr*.6)
                tangent=unit(rach(min(1,t+.001))-rach(max(0,t-.001)))
                frond_normal=unit(tangent.cross(side))
                # Each pinna belongs to the local curved frond surface, not a
                # globally horizontal plane on an ascending rachis.
                ax=unit(tangent*sweep+side*sg+frond_normal*r.uniform(-.055,.045))
                nn=unit(frond_normal+side*sg*(.12*math.sin(t*6+fr)))
                variant=(j+fr*7+(sg==1))%12;age='young' if fr==6 else 'mature';key=(variant,age);ps=1109+variant*71
                if key not in prototype:
                    pm=Mesh(f'GATE | shared fern pinna {variant} {age}');leaf(pm,(0,0,0),(1,0,0),(0,0,1),.10,.018,'fern',ps,leafmaterial('fern',age),vein,0,False,True)
                    po=pm.finish(col);prototype[key]=po.data;bpy.data.objects.remove(po,do_unlink=True)
                sidev=unit(ax.cross(nn));nn=unit(sidev.cross(ax));o=bpy.data.objects.new(f'Pinna {fr:02d} {j:02d} {sg:+d}',prototype[key]);col.objects.link(o)
                rot=Matrix(((ax.x,-sidev.x,nn.x),(ax.y,-sidev.y,nn.y),(ax.z,-sidev.z,nn.z))).to_4x4();rot.translation=root
                o.matrix_world=rot@Matrix.Scale(lng/.10,4);pinnae.append(o)
                b=Blade(root,ax,nn,lng,lng*.18,'fern',ps,False)
                if fr in [0,2] and 6<j<27:
                    for tt in [.20,.32,.44,.56,.68,.80]:
                        for vv in [-.71,.71]:
                            p=b.pos(tt,vv)-b.normal_at(tt,vv)*.00022;norm=-b.normal_at(tt,vv)
                            tube(m,[p,p+norm*.00035],[.00060,.00038],sori,6)
        leaf(m,rach(.97),unit(rach(1)-rach(.94)),(0,0,1),.046,.009,'fern',seed+fr*17,leafmaterial('fern','young'),vein,0,False,False)
    # Compact circinate buds with developing pinnae, not bare wire loops.
    for fr in range(2):
        a=1.3+fr*2.1;d=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
        height=.22+fr*.09;p0=Vector((0,0,0));p1=d*.06+Vector((0,0,height));ps=[p0.lerp(p1,t)+d*.02*math.sin(t*math.pi) for t in np.linspace(0,1,20)]
        center=p1+Vector((0,0,.024));coil=[]
        for t in np.linspace(0,1,65):
            theta=float(t)*TAU*1.6;rad=.024*(1-float(t))+.002
            coil.append(center+d*rad*math.sin(theta)-Vector((0,0,rad*math.cos(theta))))
        ps+=coil;tube(m,ps,np.linspace(.0026,.00055,len(ps)),stem,8)
        # Developing rolled lamina around the spiral rather than a bare tube.
        rv=[];ru=[];rf=[]
        for k,p0 in enumerate(coil):
            u=k/(len(coil)-1);width=.0065*(1-u)**.65+.0013
            for sg in [-1,0,1]:
                rv.append(p0+side*width*sg+d*.0015*(1-sg*sg));ru.append((sg*.5+.5,u))
            if k:
                a=(k-1)*3;b=k*3;rf.extend([(a,a+1,b+1,b),(a+1,a+2,b+2,b+1)])
        m.add(rv,rf,ru,leafmaterial('fern','young'))
        for k in range(5,60,4):
            p=coil[k]
            for sg in [-1,1]:
                leaf(m,p,unit(side*sg+Vector((0,0,.2))),d,.006+.003*k/60,.0025,'fern',seed+900+fr*101+k,leafmaterial('fern','young'),vein,0,False,False)
    ob=m.finish(col);root=bpy.data.objects.new('GATE | complete fern crown',None);col.objects.link(root)
    for part in pinnae+[ob]:part.parent=root
    root['reference']='Nephrolepis biserrata-informed authored juvenile; not species-calibrated';root['shared_pinna_variants']=len(prototype);root['pinna_instances']=len(pinnae);return root

def soil_z(x,y):return .008*math.sin(x*12+y*3)+.006*math.sin(y*15-x*4)+.002*math.cos(x*39-y*17)

def soilmat():
    m=plain('GATE | inherited forest mud substrate',(.024,.016,.009),.86);ns=m.node_tree.nodes;ln=m.node_tree.links;bs=ns.get('Principled BSDF')
    tc=ns.new('ShaderNodeTexCoord');mapping=ns.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=1/2.35;ln.new(tc.outputs['Object'],mapping.inputs[0])
    diff=imtex(ns,AS/'inherited_mud_Diffuse.jpg');diff.extension='REPEAT';ln.new(mapping.outputs[0],diff.inputs[0]);ln.new(diff.outputs['Color'],bs.inputs['Base Color'])
    rough=imtex(ns,AS/'inherited_mud_Rough.jpg',True);rough.extension='REPEAT';ln.new(mapping.outputs[0],rough.inputs[0]);ln.new(rough.outputs['Color'],bs.inputs['Roughness'])
    normal=imtex(ns,AS/'inherited_mud_nor_gl.png',True);normal.extension='REPEAT';ln.new(mapping.outputs[0],normal.inputs[0]);n=ns.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.65;ln.new(normal.outputs['Color'],n.inputs['Color']);ln.new(n.outputs[0],bs.inputs['Normal'])
    bs.inputs['Specular IOR Level'].default_value=.32
    return m

def append_existing_substrate(col):
    """Reuse original deadwood unmodified; its translated geometry is a support."""
    from mathutils.bvhtree import BVHTree
    source=AS/'original_substrate.blend'
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):
        dst.objects=['CC0 scan | dead_tree_trunk_02']
    for ob in dst.objects:
        col.objects.link(ob);ob.location=(.05,.47,-.045);ob.scale=(.31,.31,.31);ob.rotation_euler[2]=.13
        bpy.context.view_layer.update()
        co=[ob.matrix_world@v.co for v in ob.data.vertices]
        faces=[tuple(p.vertices) for p in ob.data.polygons]
        SUPPORT_BVHS.append(BVHTree.FromPolygons(co,faces,all_triangles=False))
        ob['gate_provenance']='Existing CC0 deadwood from original GREEN_TERROR scene; not newly scanned.'
        ob['gate_source']='original_substrate.blend'
    return dst.objects

def skeleton_leaf(mesh,b,material):
    net=NETWORK.get(b.fam)
    if net is None:net=json.loads((AS/f'{b.fam}_network.json').read_text());NETWORK[b.fam]=net
    pts=[]
    for u,t in net['nodes']:
        t=max(.002,min(.998,t));v=np.clip((u-.5)*2/max(.02,profile(t,b.fam)),-.97,.97)
        pts.append(b.pos(t,float(v)))
    for k,parent in enumerate(net['parent']):
        if parent<0:continue
        level=net['order'][k];rad=(.00038 if level==0 else .00016 if level==1 else .000055)*(b.L/.18)
        tube(mesh,[pts[parent],pts[k]],[rad,rad*.84],material,4)

def create_ground(col,stem,vein,seed=3771):
    r=random.Random(seed);soil=soilmat();m=Mesh('GATE | soil support');verts=[];uv=[];faces=[];nx,ny=161,141
    for iy,y in enumerate(np.linspace(-.72,.72,ny)):
        for ix,x in enumerate(np.linspace(-.85,.85,nx)):
            verts.append((x,y,soil_z(x,y)));uv.append((ix/(nx-1),iy/(ny-1)))
            if iy and ix:
                a=(iy-1)*nx+ix-1;faces.append((a,a+1,a+1+nx,a+nx))
    m.add(verts,faces,uv,soil);base=m.finish(col)
    # A dense support raster seats each object rigidly; no vertex-wise terrain projection.
    G=750;xs=np.linspace(-.85,.85,G);ys=np.linspace(-.72,.72,G);xx,yy=np.meshgrid(xs,ys);height=.008*np.sin(xx*12+yy*3)+.006*np.sin(yy*15-xx*4)+.002*np.cos(xx*39-yy*17)
    if SUPPORT_BVHS:
        for iy in range(G):
            for ix in range(G):
                origin=Vector((float(xs[ix]),float(ys[iy]),1.5))
                for tree in SUPPORT_BVHS:
                    hit,_,_,_=tree.ray_cast(origin,Vector((0,0,-1)),2.0)
                    if hit is not None:height[iy,ix]=max(height[iy,ix],hit.z)
    def sample_support(co):
        ix=np.clip(np.rint((co[:,0]+.85)/1.70*(G-1)).astype(int),0,G-1);iy=np.clip(np.rint((co[:,1]+.72)/1.44*(G-1)).astype(int),0,G-1)
        return height[iy,ix],ix,iy
    lm=Mesh('GATE | rigidly settled curled litter');contacts=[]
    for k in range(610):
        x=r.uniform(-.83,.83);y=r.uniform(-.7,.7);angle=r.random()*TAU;d=Vector((math.cos(angle),math.sin(angle),r.uniform(-.18,.18)))
        L=r.uniform(.075,.165);W=L*r.uniform(.41,.63);family='piper' if k%4 else 'cordate'
        # Build object at zero elevation, then preserve its shape with one translation.
        q=Mesh('temp');b=leaf(q,(x,y,0),d,(r.uniform(-.17,.17),r.uniform(-.17,.17),1),L,W,family,seed+k*31,litter_material(family,k%6),vein,0,True,k%7==0)
        co=np.asarray(q.v);support,ix,iy=sample_support(co)
        lamina=np.array(q.f[:q.last_lamina_count:2],dtype=np.int32);centroids=co[lamina].mean(axis=1);cs,_,_=sample_support(centroids)
        lift=float(max(np.max(support-co[:,2]),np.max(cs-centroids[:,2]))+.0006);co[:,2]+=lift
        # Reject precarious high-standing leaves rather than stretching them down.
        clearance=co[:,2]-support
        if np.median(clearance)>.045:continue
        off=len(lm.v);lm.v.extend(map(tuple,co));lm.uv.extend(q.uv);lm.f.extend(tuple(i+off for i in f) for f in q.f)
        lm.mi.extend([lm.mat(q.mats[j]) for j in q.mi]);lm.smooth.extend(q.smooth)
        # Rasterize the complete projected surface via a native BVH, not just
        # the vertices: later pieces cannot fall through unsampled grid holes.
        from mathutils.bvhtree import BVHTree
        tree=BVHTree.FromPolygons(co.tolist(),q.f,all_triangles=False)
        i0=max(0,int((co[:,0].min()+.85)/1.70*(G-1))-1);i1=min(G-1,int((co[:,0].max()+.85)/1.70*(G-1))+1)
        j0=max(0,int((co[:,1].min()+.72)/1.44*(G-1))-1);j1=min(G-1,int((co[:,1].max()+.72)/1.44*(G-1))+1)
        ztop=float(co[:,2].max()+.002);depth=float(np.ptp(co[:,2])+.004)
        for jj in range(j0,j1+1):
            for ii in range(i0,i1+1):
                hit,_,_,_=tree.ray_cast(Vector((float(xs[ii]),float(ys[jj]),ztop)),Vector((0,0,-1)),depth)
                if hit is not None:height[jj,ii]=max(height[jj,ii],hit.z)
        contacts.append({'leaf':k,'translation_m':lift,'min_support_clearance_m':float(clearance.min()),'median_clearance_m':float(np.median(clearance)),'min_lamina_centroid_clearance_m':float(np.min(centroids[:,2]+lift-cs)),'rigid_shape_preserved':True})
    litter=lm.finish(col)
    sk=Mesh('GATE | open vascular leaf skeletons');bone=plain('GATE | dried vascular fibres',(.16,.105,.048),.83)
    for k,(x,y) in enumerate([(-.12,-.34)]):
        b=Blade((x,y,0),(math.cos(k*2.4),math.sin(k*2.4),.05),(0,0,1),.15,.071,'piper',914+k,True)
        q=Mesh('skeleton');skeleton_leaf(q,b,bone);co=np.asarray(q.v);su,_,_=sample_support(co);co[:,2]+=float(np.max(su-co[:,2])+.0005)
        off=len(sk.v);sk.v.extend(map(tuple,co));sk.uv.extend(q.uv);sk.f.extend(tuple(i+off for i in f) for f in q.f);sk.mi.extend([sk.mat(q.mats[j]) for j in q.mi]);sk.smooth.extend(q.smooth)
    sk.finish(col)
    # Branching twigs sit rigidly on the same supporting pile.
    tw=Mesh('GATE | fallen petioles and branching twigs');drywood=plain('GATE | decomposing twig bark',(.023,.016,.010),.86)
    for k in range(38):
        x=r.uniform(-.82,.82);y=r.uniform(-.70,.70);a=r.random()*TAU;L=r.uniform(.06,.28);d=Vector((math.cos(a),math.sin(a),0));pts=np.array([tuple(Vector((x,y,0))+d*L*t+Vector((0,0,.008*math.sin(t*math.pi)))) for t in np.linspace(0,1,10)])
        su,_,_=sample_support(pts);pts[:,2]+=np.max(su-pts[:,2])+.002
        rad=r.uniform(.0009,.0028);tube(tw,pts,np.linspace(rad,rad*.22,10),drywood,7)
        if k%2==0:
            p=Vector(pts[5]);tube(tw,[p,p+d*L*.17+Vector((-d.y,d.x,0))*L*.23],[rad*.6,rad*.08],drywood,5)
    twig=tw.finish(col)
    (EV/'litter_support.json').write_text(json.dumps({'method':'rigid shape-preserving vertical seating on a sequential raster support; not a global collision or cloth solver','grid_resolution':G,'accepted_leaves':len(contacts),'leaves':contacts},indent=2))
    return base,litter,twig

def camera(name,position,target,lens=55):
    c=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.lens=lens;c.clip_start=.005;c.clip_end=200;return o

def light(name,position,target,power,size,color=(1,1,1)):
    l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;l.color=color;o=bpy.data.objects.new(name,l);bpy.context.scene.collection.objects.link(o);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

def configure():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=128;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.012;s.cycles.adaptive_min_samples=24;s.cycles.use_denoising=True
    s.cycles.max_bounces=10;s.cycles.diffuse_bounces=5;s.cycles.glossy_bounces=5;s.cycles.transmission_bounces=6;s.cycles.transparent_max_bounces=8
    s.render.resolution_x=1600;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';s.render.film_transparent=False
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0;s.render.use_persistent_data=False
    world=bpy.data.worlds.new('GATE | neutral environment');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.44,.5,1);world.node_tree.nodes['Background'].inputs[1].default_value=.2;s.world=world
    return s

def make_scene(kind):
    s=configure();col=add_collection('GATE | approved-scope candidate geometry');stem=stemmaterial();vein=plain('GATE | raised abaxial veins',(.087,.111,.031),.65)
    main=[]
    if kind in ['branch','cordate']:
        ob=create_branch(col,stem,vein,'piper' if kind=='branch' else 'cordate');main.append(ob)
        s.camera=camera('Review_camera',(.32,-1.32,.70),(.02,0,.29),66)
    elif kind=='fern':
        ob=create_fern(col,stem,vein);main.append(ob);s.camera=camera('Review_camera',(1.20,-1.85,1.65),(0,0,.30),59)
    elif kind=='patch':
        main.extend(append_existing_substrate(col))
        main.extend(create_ground(col,stem,vein))
        ferncol=add_collection('GATE | fern crown');f=create_fern(ferncol,stem,vein);f.location=(-.48,.34,.01);f.scale=(.67,)*3;main.append(f)
        branchcol=add_collection('GATE | leafy seedling');b=create_branch(branchcol,stem,vein,'piper',773);b.location=(.36,.10,soil_z(.36,.10)+.12);b.scale=(.67,)*3;main.append(b)
        for k in range(3):
            # Smaller independent developmental variants, not clone rows.
            b=create_branch(branchcol,stem,vein,'cordate' if k==0 else 'piper',712+k*81);b.location=((-.43,.50,.10)[k],(-.38,.40,-.46)[k],.035);b.scale=(.24+.05*k,)*3;b.rotation_euler[2]=k*1.8;main.append(b)
        # Every seedling joins its actual twig base to the soil. The imported
        # branch asset is a cut specimen; its model origin is not a root.
        bpy.context.view_layer.update();rootmesh=Mesh('GATE | connected seedling lower stems')
        for o in list(branchcol.objects):
            if o.type!='MESH':continue
            end=o.matrix_world@Vector((-.27,0,.25));scale=float(o.scale.x)
            start=Vector((end.x-.035*scale,end.y+.012*scale,soil_z(end.x-.035*scale,end.y+.012*scale)+.001))
            ps=[start.lerp(end,float(t))+Vector((.015*scale*math.sin(float(t)*math.pi),0,0)) for t in np.linspace(0,1,16)]
            tube(rootmesh,ps,np.linspace(.0044*scale,.0038*scale,16),stem,9)
        rootmesh.finish(branchcol)
        s.camera=camera('Review_camera',(1.14,-1.65,1.13),(0,.06,.13),57)
    # Neutral studio receiver for diagnostic models. The patch has its own earth.
    floor=Mesh('GATE | neutral evaluation surface');floor.add([(-200,-200,-.025),(200,-200,-.025),(200,200,-.025),(-200,200,-.025)],[(0,1,2,3)],[(0,0),(1,0),(1,1),(0,1)],plain('GATE | neutral background',(.022,.027,.029),.90),False);floor.finish(col)
    light('Key_soft',(-.75,-.85,1.65),(.0,0,.30),130,.95,(1.0,.96,.89))
    light('Fill',(.65,-.85,1.05),(0,0,.30),32,.85,(.78,.89,1.0))
    light('Key_side',(-.95,-.48,.65),(.0,0,.35),95,.38,(1.0,.96,.90))
    light('Key_back',(.25,.85,1.0),(.0,0,.35),125,.65,(1.0,.97,.90))
    for n in ['Key_side','Key_back']:bpy.data.objects[n].hide_render=True
    for o in main:o['gate_candidate']=True
    s['gate_scope']='Isolated authored reference-informed asset test; not a full forest replacement.'
    for im in bpy.data.images:
        if im.source=='FILE':im.pack()
    # Static native checks on topology, attributes, and finite coordinates.
    records=[]
    for ob in bpy.data.objects:
        if ob.type!='MESH':continue
        me=ob.data;me.calc_loop_triangles();co=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3)
        tri=np.array([tuple(t.vertices) for t in me.loop_triangles],dtype=np.int32)
        area=np.linalg.norm(np.cross(co[tri[:,1]]-co[tri[:,0]],co[tri[:,2]]-co[tri[:,0]]),axis=1)*.5 if len(tri) else np.zeros(0)
        records.append({'object':ob.name,'mesh_name':me.name,'vertices':len(co),'triangles':len(tri),'finite':bool(np.isfinite(co).all()),'zero_area_triangles':int(np.sum(area<1e-14)),'uv_layer':bool(me.uv_layers),'min_area':float(area.min()) if len(area) else None})
    p=ROOT/f'{kind.upper()}_ASSET_GATE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True)
    report={'completed':True,'kind':kind,'seed':SEED,'native_blender':bpy.app.version_string,'scope':s['gate_scope'],'file':str(p),'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'objects':records,'images_packed':len([i for i in bpy.data.images if i.packed_file]),'image_generation_used':False,'leaf_maps':'procedurally constructed connected multiscale vascular graph; photographs are not sampled'}
    (EV/f'{kind}_build.json').write_text(json.dumps(report,indent=2));print('BUILD_COMPLETED',kind,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['branch','cordate','fern','patch'],required=True);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    make_scene(a.kind)
