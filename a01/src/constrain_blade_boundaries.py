"""Replace unconstrained raster-grid triangulation by native constrained CDT.
Curve boundaries are explicit edges. Interior samples cannot leave staircase
bites along an entire-margin leaf. Maps are resampled at returned CDT vertices.
"""
import sys,json,time
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ROOT=Path(__file__).resolve().parents[1]
def bilinear(a,uv):
    h,w=a.shape;x=np.clip(uv[:,0]*(w-1),0,w-1);y=np.clip(uv[:,1]*(h-1),0,h-1);ix=x.astype(int);iy=y.astype(int);ix1=np.minimum(ix+1,w-1);iy1=np.minimum(iy+1,h-1);fx=x-ix;fy=y-iy
    return ((1-fx)*(1-fy)*a[iy,ix]+fx*(1-fy)*a[iy,ix1]+(1-fx)*fy*a[iy1,ix]+fx*fy*a[iy1,ix1]).astype(np.float32)
def main():
    report=[]
    for fam in ['cordate','elliptic','lance']:
        p=ROOT/'assets'/f'{fam}.npz';d=dict(np.load(p));boundary=d['boundary'];xy=d['xy']
        # All original points plus exact silhouette constraints.
        coords=np.concatenate([boundary,xy]);ids=list(range(len(boundary)));edges=[(i,(i+1)%len(boundary)) for i in ids]
        signed=float(np.sum(boundary[:,0]*np.roll(boundary[:,1],-1)-boundary[:,1]*np.roll(boundary[:,0],-1)))
        if signed<0:ids.reverse()
        result=delaunay_2d_cdt([Vector(v) for v in coords],edges,[ids],1,1e-7,False)
        newxy=np.array(result[0],np.float32);faces=np.array(result[2],np.int32)
        # Reuse field values by nearest interpolation; UV itself remains exact.
        # Position changes of merged input samples are below 1e-7 normalized.
        src=d['xy'];uv=(newxy-[-.60,-.20])/[1.20,1.32]
        # Native mathutils KDTree for small numerical fields.
        from mathutils.kdtree import KDTree
        kd=KDTree(len(src))
        for i,v in enumerate(src):kd.insert((float(v[0]),float(v[1]),0),i)
        kd.balance();nearest=[kd.find((float(v[0]),float(v[1]),0))[1] for v in newxy]
        d.update(xy=newxy,uv=uv.astype(np.float32),faces=faces,relief=d['relief'][nearest],panel_distance=d['panel_distance'][nearest])
        np.savez_compressed(p,**d)
        report.append({'family':fam,'native_cdt':True,'explicit_boundary_edges':len(edges),'vertices':len(newxy),'triangles':len(faces)})
    (ROOT/'evidence/constrained_boundaries.json').write_text(json.dumps({'completed':True,'assets':report},indent=2))
if __name__=='__main__':main()
