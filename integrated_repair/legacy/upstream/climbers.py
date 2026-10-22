"""Surface-attached climbers and bryophytes on the actual living tree mesh.

The woody host is ray cast in its own coordinates. New geometry is collected
with its host before the shared bending modes are baked, so attachment points
undergo the same deformation. Moss is polygonal shoots, never flat green cards.
"""
import math
import random
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

Z=Vector((0,0,1))


class SurfaceMesh:
    def __init__(self,materials):
        self.keys=['bark_smooth','stem','leaf_dark','leaf_mid','leaf_new','leaf_vein','moss']
        self.materials=materials;self.vertices=[];self.faces=[];self.uv=[];self.mi=[]
        self.counts={'climbing_stems':0,'climber_leaves':0,'aerial_roots':0,'moss_shoots':0}

    def vertex(self,p):
        self.vertices.append(tuple(p));return len(self.vertices)-1

    def face(self,f,uv,key):
        self.faces.append(tuple(f));self.uv.extend(uv);self.mi.append(self.keys.index(key))

    def tube(self,points,radii,key='stem',sides=6):
        points=[Vector(p) for p in points];rings=[];last=None;v=0;lengths=[]
        if isinstance(radii,(int,float)):radii=[radii]*len(points)
        for i,(p,r) in enumerate(zip(points,radii)):
            t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            if last is None:
                a=t.cross(Z if abs(t.z)<.93 else Vector((1,0,0))).normalized()
            else:a=(last-t*last.dot(t)).normalized()
            b=t.cross(a).normalized();last=a
            if i:v+=(p-points[i-1]).length
            lengths.append(v)
            rings.append([self.vertex(p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)))
                          for j in range(sides)])
        for i in range(len(rings)-1):
            for j in range(sides):
                k=(j+1)%sides
                self.face((rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]),
                          ((j/sides,lengths[i]),((j+1)/sides,lengths[i]),
                           ((j+1)/sides,lengths[i+1]),(j/sides,lengths[i+1])),key)

    def leaf(self,base,axis,normal,length,width,rng,key='leaf_mid'):
        axis=Vector(axis).normalized();normal=Vector(normal)
        normal=(normal-axis*normal.dot(axis)).normalized()
        side=axis.cross(normal).normalized();base=Vector(base)
        along,across=10,4;start=len(self.vertices);phase=rng.random()*math.tau
        for i in range(along+1):
            t=i/along;profile=max(.004,math.sin(math.pi*t)**.64*(1.20-.44*t))
            c=base+axis*length*t+normal*length*(.13*math.sin(math.pi*t)-.19*t*t)
            for j in range(across+1):
                s=j*2/across-1
                w=width*.5*profile*(1+.035*math.sin(31*t+phase)*abs(s))
                p=c+side*(s*w)+normal*width*(-.075*s*s*profile+.018*math.sin(53*t-abs(s)*2.5))
                self.vertex(p)
        for i in range(along):
            for j in range(across):
                a=start+i*(across+1)+j
                self.face((a,a+1,a+across+2,a+across+1),
                          ((j/across,i/along),((j+1)/across,i/along),
                           ((j+1)/across,(i+1)/along),(j/across,(i+1)/along)),key)
        mid=[]
        for i in range(11):
            t=i/10;mid.append(base+axis*length*t+normal*(length*(.13*math.sin(math.pi*t)-.19*t*t)+.0015))
        self.tube(mid,[.0018*(1-.85*i/10) for i in range(11)],'leaf_vein',4)
        self.counts['climber_leaves']+=1

    def moss(self,p,n,rng):
        p=Vector(p);n=Vector(n).normalized()
        a=n.cross(Z if abs(n.z)<.95 else Vector((1,0,0))).normalized();b=n.cross(a)
        for shoot in range(rng.randrange(7,15)):
            angle=rng.random()*math.tau;off=rng.uniform(0,.028)
            root=p+(a*math.cos(angle)+b*math.sin(angle))*off
            axis=(n*rng.uniform(.55,1.2)+Z*.42).normalized()
            h=rng.uniform(.009,.033);tip=root+axis*h
            for k in range(5):
                phi=angle+k*2.4;d=a*math.cos(phi)+b*math.sin(phi)
                c=root+axis*(h*(.18+k*.12));w=rng.uniform(.0011,.0027)
                end=c+d*h*.45+axis*h*.28
                ids=[self.vertex(c),self.vertex((c+end)*.5+b*w),
                     self.vertex(end),self.vertex((c+end)*.5-b*w)]
                self.face(ids,((.5,0),(0,.45),(.5,1),(1,.45)),'moss')
            self.counts['moss_shoots']+=1

    def finish(self,name):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.faces)
        for key in self.keys:mesh.materials.append(self.materials.get(key,self.materials['stem']))
        mesh.polygons.foreach_set('material_index',self.mi)
        mesh.polygons.foreach_set('use_smooth',[True]*len(self.faces))
        uv=mesh.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',[v for p in self.uv for v in p])
        mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob)
        for k,v in self.counts.items():ob[k]=v
        ob['attachment']='Ray casts against actual host wood; same rooted wind deformation as host'
        ob['leaf_count']=self.counts['climber_leaves']
        return ob


def decorate_tree(name,wood,materials,seed,height,radius):
    """Return one small merged decorator mesh, shared with the tree prototype."""
    rng=random.Random(seed+309187);mesh=SurfaceMesh(materials)
    vertices=[v.co.copy() for v in wood.data.vertices]
    polygons=[tuple(p.vertices) for p in wood.data.polygons]
    bvh=BVHTree.FromPolygons(vertices,polygons,all_triangles=False,epsilon=.0001)
    ray_radius=max(3.,radius*7.)
    def seat(z,a,offset=.008):
        d=Vector((math.cos(a),math.sin(a),0))
        hit,normal,_,_=bvh.ray_cast(d*ray_radius+Z*z,-d,ray_radius*1.6)
        if hit is None:return None
        return hit+normal*offset,normal
    vines=2 if radius<.28 else 3
    for k in range(vines):
        h=min(height*.25,rng.uniform(4.8,9.5));phase=rng.random()*math.tau
        slope=rng.uniform(-.39,.39);r=rng.uniform(.007,.019)*(1+radius*.55)
        points=[];normals=[]
        for j in range(94):
            z=.09+h*j/93;a=phase+slope*z+.10*math.sin(z*2.8+phase)
            result=seat(z,a,r*.65)
            if result:
                p,n=result;points.append(p);normals.append(n)
        if len(points)<4:continue
        mesh.tube(points,[r*(1-.62*j/(len(points)-1)) for j in range(len(points))],'bark_smooth',7)
        mesh.counts['climbing_stems']+=1
        for j in range(5,len(points)-5,5):
            if rng.random()<.18:continue
            p,n=points[j],normals[j];side=n.cross(Z).normalized()*rng.choice((-1,1))
            petiole=p+n*rng.uniform(.06,.14)+side*rng.uniform(.03,.10)
            mesh.tube([p,(p+petiole)*.5+Z*.025,petiole],[.003,.0023,.0014],'stem',5)
            length=rng.uniform(.17,.39)*(1+j/len(points)*.40)
            axis=(Z*.60+side*.64+n*.13).normalized()
            mesh.leaf(petiole,axis,n,length,length*rng.uniform(.48,.67),rng,
                      'leaf_new' if j>len(points)*.85 else rng.choice(('leaf_dark','leaf_mid')))
        if k==0:
            start=points[-1];end=start+normals[-1]*rng.uniform(.18,.6)
            end.z=.015
            root=[]
            for j in range(45):
                t=j/44;p=start.lerp(end,t)
                p+=normals[-1]*(.17*math.sin(math.pi*t))+Vector((.02*math.sin(21*t),.02*math.sin(15*t),0))
                root.append(p)
            mesh.tube(root,[.011*(1-.83*j/44) for j in range(45)],'bark_smooth',6)
            mesh.counts['aerial_roots']+=1
    # Moss colonizes patchy lower bark and root shoulders, not an even green sleeve.
    wet_aspect=rng.random()*math.tau
    for i in range(150 if radius>.35 else 95):
        z=rng.uniform(.04,min(3.4,height*.12));a=wet_aspect+rng.gauss(0,.73)
        if math.sin(z*5.3+a*2.1)+math.sin(z*2.7-a*3.4)<-.35:continue
        result=seat(z,a,.004)
        if result:mesh.moss(*result,rng)
    return [mesh.finish(name+'_attached_climbers_and_moss')]
