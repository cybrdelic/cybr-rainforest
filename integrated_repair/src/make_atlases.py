"""Deterministic anatomical maps. Photographs are never sampled or used as textures.
Prescribed primary/secondary skeleton + attractor-driven fine vein growth.
This is a small hybrid implementation, not a full reproduction of Runions et al.
"""
from pathlib import Path
import json, math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter, distance_transform_edt, zoom
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'assets'; A.mkdir(exist_ok=True)
W,H=1536,2048

def profile(t,family):
    t=np.clip(t,0,1)
    if family=='cordate':
        return np.maximum(0,np.sin(np.pi*(.09+.91*t)))**.65*(1.34-.65*t)
    if family=='fern':return np.maximum(0,np.sin(np.pi*(.035+.965*t)))**.33*(1.12-.38*t)
    tip=np.clip((t-.72)/.28,0,1);tip=tip*tip*(3-2*tip)
    return np.maximum(0,np.sin(np.pi*t))**.70*(1.26-.42*t)*(1-.62*tip)

def main(family,seed):
    rng=np.random.default_rng(seed); metric=np.array([.46,1.])
    ps=[];parents=[];order=[];major=[]
    def path(points,lev,parent=-1):
        inds=[]
        for p in points:
            idx=len(ps); ps.append(tuple(p));parents.append(parent);order.append(lev);inds.append(idx);parent=idx
        major.append({'level':lev,'uv':np.asarray(points).tolist()});return inds
    trunk=np.column_stack((.5+.005*np.sin(np.linspace(0,np.pi,101)),np.linspace(0,1,101)))
    main_ids=path(trunk,0)
    if family=='cordate': levels=[.025,.095,.21,.35,.50,.65,.78,.88]
    elif family=='fern': levels=np.linspace(.065,.93,20)
    else: levels=[.035,.105,.205,.315,.435,.56,.67,.775,.865,.925]
    for si,sg in enumerate([-1,1]):
        for k,level in enumerate(levels):
            tt=float(np.clip(level+rng.normal(0,.009),.015,.97)); parent=main_ids[int(tt*100)]
            s=np.linspace(0,1,25)
            rise=(.24 if family=='cordate' else .185 if family=='piper' else .070)*(1-tt)**.65
            # lower cordate veins initially spread down into basal lobes.
            y=tt+rise*(.26*s+.74*s*s)
            if family=='cordate' and k==0:y=tt-.055*np.sin(s*np.pi)+.18*s*s
            y=np.clip(y,.008,.995)
            x=.5+sg*.5*profile(y,family)*(.93*s)
            x+=.004*np.sin(s*7+k)*s*(1-s)
            pts=np.column_stack((x,y));ids=path(pts,1,parent)
    # Attractor-directed secondary mesh growth is not an unconnected Voronoi overlay.
    cand=rng.uniform([.01,.015],[.99,.985],(2200 if family!='fern' else 1500,2))
    inside=np.abs(cand[:,0]-.5)<.495*profile(cand[:,1],family)
    attractors=cand[inside]; initial=len(ps); N0=len(ps)
    for it in range(78):
        points=np.asarray(ps);tree=cKDTree(points*metric);dst,ids=tree.query(attractors*metric)
        alive=dst>.010
        attractors=attractors[alive];dst=dst[alive];ids=ids[alive]
        if not len(attractors):break
        selected=dst<.125;source=attractors[selected];nearest=ids[selected]
        vectors=(source-points[nearest])*metric;vectors/=np.maximum(np.linalg.norm(vectors,axis=1)[:,None],1e-10)
        unique,inv=np.unique(nearest,return_inverse=True);sums=np.zeros((len(unique),2));np.add.at(sums,inv,vectors)
        norms=np.linalg.norm(sums,axis=1);good=norms>1e-7;unique=unique[good];sums=sums[good]/norms[good,None]
        new=points[unique]+(.0078*sums)/metric
        new[:,1]=np.clip(new[:,1],.003,.997)
        new[:,0]=np.clip(new[:,0],.5-.495*profile(new[:,1],family),.5+.495*profile(new[:,1],family))
        for p,pa in zip(new,unique):ps.append(tuple(p));parents.append(int(pa));order.append(2)
        if len(ps)>12000:break
    points=np.asarray(ps);flux=np.ones(len(ps))
    for k in range(len(ps)-1,-1,-1):
        if parents[k]>=0:flux[parents[k]]+=flux[k]
    # Joining nearby terminal tips produces sparse reticulate anastomoses.
    kids=np.bincount(np.array(parents)[np.array(parents)>=0],minlength=len(ps));tips=np.where((kids==0)&(np.arange(len(ps))>=initial))[0]
    tree=cKDTree(points*metric);loops=[]
    for k in tips:
        ds,js=tree.query(points[k]*metric,k=7)
        for d,j in zip(ds[1:],js[1:]):
            if .002<d<.015 and j!=parents[k] and parents[j]!=k and abs(k-j)>3:
                loops.append((int(k),int(j)));break
    bands=[Image.new('L',(W,H),0) for _ in range(3)];draw=[ImageDraw.Draw(i) for i in bands]
    def xy(q):return (float(q[0]*(W-1)),float((1-q[1])*(H-1)))
    for k,pa in enumerate(parents):
        if pa<0:continue
        lev=order[k]
        if lev==0:width=int(max(2,12*(1-points[k,1]*.86)))
        elif lev==1:width=int(max(1,6.0*(1-points[k,1]*.65)))
        else:width=max(1,min(3,round(flux[k]**.22*.65)))
        draw[lev].line([xy(points[pa]),xy(points[k])],fill=255,width=width)
    for i,j in loops:draw[2].line([xy(points[i]),xy(points[j])],fill=200,width=1)
    v0,v1,v2=[gaussian_filter(np.asarray(im,np.float32)/255,.65) for im in bands]
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32);t=1-yy/(H-1);x=xx/(W-1)
    def fb(n,amp):
        a=rng.normal(0,1,(n,n)).astype(np.float32);a=zoom(a,(H/n,W/n),order=3)[:H,:W];return a/(a.std()+1e-6)*amp
    low=fb(9,.04);medium=fb(43,.018);fine=fb(180,.009);micro=rng.normal(0,.004,(H,W)).astype(np.float32)
    profilef=profile(t,family);edge=np.clip(1-np.abs(x-.5)/np.maximum(.5*profilef,.001),0,1)
    vein=np.clip(v0+v1*.85+v2*.58,0,1)
    # Mild cellular undulation and shared thickness around the connected network.
    cells=distance_transform_edt((v2+v1+v0)<.18).astype(np.float32)
    height=np.clip(.35+.35*v0+.18*v1+.09*v2+np.clip(cells/18,0,1)*.18+fine*.18,0,1)
    major_distance=distance_transform_edt((v0+v1)<.12).astype(np.float32)
    panel=np.sin(np.clip(major_distance/70,0,1)*np.pi*.5)**2
    np.save(A/f'{family}_panel.npy',zoom(gaussian_filter(panel,4),(.25,.25),order=1).astype(np.float32))
    rough=np.clip(.47+low*.38+medium*.45-vein*.035+fine,.31,.61)
    thick=np.clip(.27+v0*.64+v1*.36+v2*.085+edge*.12,0,1)
    for age in ['mature','young','dead','underside']:
        if age=='mature':base=np.array([.172,.283,.081],np.float32)
        elif age=='young':base=np.array([.265,.351,.108],np.float32)
        elif age=='underside':base=np.array([.275,.361,.165],np.float32)
        else:base=np.array([.262,.188,.122],np.float32)
        factor=1+low+medium+fine+micro
        if age=='dead':factor+=fb(11,.16)+fb(38,.05)
        rgb=base[None,None,:]*factor[:,:,None]
        tint=np.array([.105,.115,.046],np.float32) if age!='dead' else np.array([.075,.049,.022],np.float32)
        rgb+=vein[:,:,None]*tint*.80
        rgb-=np.exp(-edge/.018)[:,:,None]*np.array([.036,.049,.016])
        Image.fromarray(np.uint8(np.clip(rgb,0,1)*255),'RGB').save(A/f'{family}_{age}.png')
    for name,data in [('height',height),('roughness',rough),('thickness',thick)]:
        Image.fromarray(np.uint16(data*65535)).save(A/f'{family}_{name}.png')
    (A/f'{family}_network.json').write_text(json.dumps({'seed':seed,'family':family,'major':major,'node_count':len(ps),'joining_edges':len(loops),'nodes':points.tolist(),'parent':parents,'order':order,'growth':'prescribed main skeleton with attractor-driven fine branching and terminal joining'},separators=(',',':')))
    print(family, len(ps),len(loops),flush=True)
if __name__=='__main__':
    for f,s in [('piper',61317),('cordate',71521),('fern',31741)]:main(f,s)
