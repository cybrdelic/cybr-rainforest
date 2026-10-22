"""Deterministic anatomical leaf assets; photographs are references, never inputs.
Metre-independent XY shape in a normalized leaf domain. Major veins are authored
Bezier controls. Minor veins use an auxin-source space-colonization iteration,
with sparse tip joining. Height, albedo, thickness and roughness derive from that
same graph. No neural image generation or photographs enter the material maps.
"""
from __future__ import annotations
import json, math, hashlib, time
from pathlib import Path
import numpy as np
from scipy.spatial import Delaunay, cKDTree
from scipy.ndimage import gaussian_filter, map_coordinates, distance_transform_edt, zoom
from shapely.geometry import Polygon
from shapely import contains_xy
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'; ASSETS.mkdir(exist_ok=True)
N=2048
XMIN,XMAX,YMIN,YMAX=-.60,.60,-.20,1.12

def bez(p0,p1,p2,p3,n=60):
    t=np.linspace(0,1,n)[:,None];return (1-t)**3*np.array(p0)+3*(1-t)**2*t*np.array(p1)+3*(1-t)*t*t*np.array(p2)+t**3*np.array(p3)

def outline(fam):
    if fam=='cordate':
        left=np.concatenate([bez((0,0),(-.12,-.16),(-.39,-.13),(-.43,.13)),bez((-.43,.13),(-.46,.40),(-.17,.73),(-.064,.88))[1:],bez((-.064,.88),(-.035,.94),(-.026,1.02),(0,1.06))[1:]])
    elif fam=='elliptic':
        left=np.concatenate([bez((0,0),(-.105,.07),(-.305,.20),(-.30,.43)),bez((-.30,.43),(-.29,.66),(-.09,.88),(0,1.06))[1:]])
    elif fam=='lance':
        left=np.concatenate([bez((0,0),(-.065,.10),(-.205,.25),(-.19,.46)),bez((-.19,.46),(-.17,.69),(-.035,.95),(0,1.06))[1:]])
    else:raise ValueError(fam)
    right=left[::-1].copy();right[:,0]*=-1
    right[:,0]*=1+.045*np.sin(right[:,1]*5+1.3)
    out=np.concatenate([left,right[1:-1]])
    out[:,0]*=1+.006*np.sin(out[:,1]*31+1)+.004*np.sin(out[:,1]*61)
    return out

def rgb_encode(x):return np.where(x<=.0031308,x*12.92,1.055*np.maximum(x,0)**(1/2.4)-.055)

def make(fam,seed):
    rng=np.random.default_rng(seed);boundary=outline(fam);poly=Polygon(boundary)
    if not poly.is_valid:raise ValueError('invalid outline')
    nodes=[];parents=[];orders=[];edges=[]
    # Each sample is connected to the graph, including lateral control curves.
    def addline(points,order,attach=-1):
        ids=[];parent=attach
        for i,p in enumerate(points):
            if i==0 and attach>=0:ids.append(attach);continue
            idx=len(nodes);nodes.append(list(p));parents.append(parent);orders.append(order)
            if parent>=0:edges.append((parent,idx,order))
            ids.append(idx);parent=idx
        return ids
    mid=bez((0,0),(.004,.28),(-.006,.70),(0,1.06),161);mids=addline(mid,0)
    for side in (-1,1):
        for k,y in enumerate([.08,.195,.31,.43,.55,.66,.76,.85]):
            dy=.17*(1-y)+.035
            endy=y+dy
            xs=np.linspace(0,.54,601)*side
            valid=contains_xy(poly,xs,np.full(601,endy))
            ext=xs[valid][-1]*.94
            base=np.array((0,y));p1=(ext*.40,y+.018);p2=(ext*.88,endy-.075)
            curve=bez(base,p1,p2,(ext,endy),55)
            attach=mids[int(round(y/1.06*160))]
            curve[0]=nodes[attach]
            keep=contains_xy(poly,curve[:,0],curve[:,1]);curve=curve[keep]
            if len(curve)>3:addline(curve,1,attach)
        if fam=='cordate':
            for end in [(side*.31,.11),(side*.255,-.048)]:
                curve=bez((0,.013),(side*.10,.035),(end[0]*.75,end[1]-.015),end,46)
                attach=2;curve[0]=nodes[attach];addline(curve,1,attach)
    # Blue-noise-like candidates: sources are removed near existing veins.
    candidates=rng.uniform([-.55,-.15],[.55,1.06],(13000,2))
    sources=candidates[contains_xy(poly,candidates[:,0],candidates[:,1])][:4300]
    arr=np.asarray(nodes);sources=sources[cKDTree(arr).query(sources)[0]>.011]
    for it in range(65):
        if not len(sources):break
        a=np.asarray(nodes);tree=cKDTree(a);dist,near=tree.query(sources)
        remaining=dist>.0065;sources=sources[remaining];dist=dist[remaining];near=near[remaining]
        influenced=dist<.10
        if not influenced.any():break
        sv=sources[influenced];nv=near[influenced];ds=dist[influenced]
        dirs=(sv-a[nv])/ds[:,None]
        sums=np.zeros((len(nodes),2));np.add.at(sums,nv,dirs)
        used=np.unique(nv);length=np.linalg.norm(sums[used],axis=1);used=used[length>1e-8]
        directions=sums[used]/np.linalg.norm(sums[used],axis=1)[:,None]
        proposed=a[used]+.0058*directions
        valid=contains_xy(poly,proposed[:,0],proposed[:,1])
        olddist=tree.query(proposed)[0];valid &= olddist>.0028
        used=used[valid];proposed=proposed[valid]
        if len(used)==0:break
        for parent,p in zip(used,proposed):
            idx=len(nodes);nodes.append(p.tolist());parents.append(int(parent));orders.append(2);edges.append((int(parent),idx,2))
    # Sparse close joins between different minor branches, not a periodic lattice.
    a=np.array(nodes);tree=cKDTree(a);pairs=tree.query_pairs(.0080)
    joins=0
    for i,j in sorted(pairs):
        if orders[i]!=2 or orders[j]!=2 or abs(i-j)<8 or parents[i]==j or parents[j]==i:continue
        if parents[i]==parents[j]:continue
        if rng.random()<.03:
            edges.append((i,j,3));joins+=1
    # Downstream demand controls the taper of the minor veins.
    demand=np.ones(len(nodes),np.float32)
    for i in range(len(nodes)-1,-1,-1):
        if parents[i]>=0:demand[parents[i]]+=demand[i]
    # High-resolution graph maps; Pillow used only to rasterize modeled veins.
    size=N
    graphmaps=[]
    def pix(p):return ((p[0]-XMIN)/(XMAX-XMIN)*(size-1),(p[1]-YMIN)/(YMAX-YMIN)*(size-1))
    for order in (0,1,2):
        im=Image.new('L',(size,size),0);d=ImageDraw.Draw(im)
        for i,j,o in edges:
            if (order<2 and o!=order) or (order==2 and o<2):continue
            if o==0:radius=.0028*(1-.72*max(0,a[j,1]))
            elif o==1:radius=.00115*(.45+.55*(1-min(abs(a[j,0])/.40,1)))
            else:radius=.00020+.00010*min(4,demand[j]**.32)
            width=max(1,int(radius*2*size/(XMAX-XMIN)))
            d.line([pix(a[i]),pix(a[j])],fill=255,width=width)
        graphmaps.append(gaussian_filter(np.asarray(im,np.float32)/255,.7))
    major,secondary,minor=graphmaps
    height=(major*.73+secondary*.31+minor*.14).clip(0,1)
    # Deterministic continuous tissue variation; amplitude constrained.
    noise=np.zeros((N,N),np.float32)
    for grid,amp in [(5,.50),(13,.28),(37,.13),(113,.055),(401,.025)]:
        small=rng.uniform(-1,1,(grid,grid)).astype(np.float32)
        large=zoom(small,(N/grid,N/grid),order=1)[:N,:N]
        noise+=large*amp
    fine=rng.normal(0,1,(N,N)).astype(np.float32);fine=gaussian_filter(fine,1.0)
    yy,xx=np.meshgrid(np.linspace(YMIN,YMAX,N),np.linspace(XMIN,XMAX,N),indexing='ij')
    within=contains_xy(poly,xx,yy)
    edge_distance=distance_transform_edt(within)/N*(XMAX-XMIN)
    edge=np.exp(-edge_distance/.0035)*within
    vein=np.maximum(major,secondary*.74)
    # Linear colors, using restrained pigment variation rather than black blotches.
    base=np.array([.021,.057,.008],np.float32) if fam=='cordate' else np.array([.032,.080,.010],np.float32)
    col=base[None,None,:]*(1+noise[:,:,None]*.42+fine[:,:,None]*.05)
    tint=np.array([.057,.115,.025],np.float32)
    mix=(vein*.50+minor*.64).clip(0,.65)[:,:,None]
    col=col*(1-mix)+tint*mix
    col*=1-edge[:,:,None]*.18
    # Tiny clustered mature marks, sparse and correlated in color/roughness only.
    marks=np.zeros((N,N),np.float32)
    for _ in range(3):
        cx,cy=rng.uniform(-.30,.30),rng.uniform(.10,.87)
        r=rng.uniform(.0015,.004)
        marks+=np.exp(-((xx-cx)**2+(yy-cy)**2)/r**2).astype(np.float32)
    col*=1-marks[:,:,None]*.38
    rough=(.38+noise*.13+minor*.04+marks*.15).clip(.27,.55)
    thick=(.30+major*.65+secondary*.26+minor*.07+noise*.015).clip(.18,1)
    # Data array: height, thickness, roughness; RGB 16bit via separate grayscale maps.
    Image.fromarray(np.flipud((rgb_encode(col).clip(0,1)*255+.5).astype('uint8'))).save(ASSETS/f'{fam}_albedo.png')
    for key,img in [('relief',height),('thickness',thick),('roughness',rough)]:
        Image.fromarray(np.flipud((img.clip(0,1)*65535+.5).astype(np.uint16))).save(ASSETS/f'{fam}_{key}.png')
    # Outline-conforming triangulation. No full grid cells are cut for damage.
    gx,gy=np.meshgrid(np.arange(-.55,.55,.0075),np.arange(-.16,1.065,.0075))
    grid=np.c_[gx.ravel(),gy.ravel()]
    grid=grid[contains_xy(poly.buffer(-.002),grid[:,0],grid[:,1])]
    points=np.concatenate([boundary,grid,a[::5]])
    points=np.unique(np.round(points,6),axis=0)
    dt=Delaunay(points)
    faces=dt.simplices;center=points[faces].mean(axis=1)
    faces=faces[contains_xy(poly,center[:,0],center[:,1])]
    # Drop faces crossing a concave cleft; keep entire triangle inside silhouette.
    keep=np.ones(len(faces),bool)
    for i in range(3):
        midpt=(points[faces[:,i]]+points[faces[:,(i+1)%3]])*.5
        keep &= contains_xy(poly.buffer(1e-6),midpt[:,0],midpt[:,1])
    faces=faces[keep]
    oriented=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    faces[oriented<0]=faces[oriented<0][:,[0,2,1]]
    uv=(points-[XMIN,YMIN])/[XMAX-XMIN,YMAX-YMIN]
    samplecoords=np.array([uv[:,1]*(N-1),uv[:,0]*(N-1)])
    relief=map_coordinates(height,samplecoords,order=1)
    distance=map_coordinates(distance_transform_edt(height<.10)/N,samplecoords,order=1)
    np.savez_compressed(ASSETS/f'{fam}.npz',xy=points.astype(np.float32),faces=faces.astype(np.int32),uv=uv.astype(np.float32),relief=relief.astype(np.float32),panel_distance=distance.astype(np.float32),boundary=boundary.astype(np.float32),vein_xy=a.astype(np.float32),vein_edges=np.asarray(edges,np.int32))
    return {'family':fam,'nodes':len(nodes),'edges':len(edges),'loop_joins':joins,'vertices':len(points),'triangles':len(faces),'texture_size':[N,N],'seed':seed,'outline_valid':poly.is_valid}

if __name__=='__main__':
    t=time.time();results=[]
    for fam,seed in [('cordate',30401),('elliptic',30402),('lance',30403)]:
        print('building',fam,flush=True);results.append(make(fam,seed));print(results[-1],flush=True)
    (ROOT/'evidence/vascular_generation.json').write_text(json.dumps({'completed':True,'seconds':time.time()-t,'assets':results,'photos_used_as_textures':False,'image_generation_used':False},indent=2))
