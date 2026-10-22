"""Exact EXR channel extraction/assembly; no resizing, painting, or image generation."""
import json,hashlib,struct,sys,argparse
from pathlib import Path
import numpy as np
import exr_checkpoint as X

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write_exr(path,pixels):
    a=np.asarray(pixels,np.float32);h,w,c=a.shape
    if c!=3 or not np.isfinite(a).all():raise ValueError('Invalid float32 RGB')
    def attr(name,typ,b):return name.encode()+b'\0'+typ.encode()+b'\0'+struct.pack('<I',len(b))+b
    ch=b''.join(k.encode()+b'\0'+struct.pack('<iB3xii',2,0,1,1) for k in 'BGR')+b'\0'
    hdr=struct.pack('<II',20000630,2)+attr('channels','chlist',ch)+attr('compression','compression',b'\0')
    window=struct.pack('<4i',0,0,w-1,h-1)
    hdr+=attr('dataWindow','box2i',window)+attr('displayWindow','box2i',window)+attr('lineOrder','lineOrder',b'\0')+attr('pixelAspectRatio','float',struct.pack('<f',1))+attr('screenWindowCenter','v2f',struct.pack('<ff',0,0))+attr('screenWindowWidth','float',struct.pack('<f',1))+b'\0'
    offset=len(hdr)+8*h;chunk=8+w*12
    with Path(path).open('wb') as f:
        f.write(hdr);f.write(struct.pack('<'+'Q'*h,*[offset+i*chunk for i in range(h)]))
        for y in range(h):f.write(struct.pack('<ii',y,w*12));f.write(a[y,:,::-1].T.astype('<f4').tobytes())

def rgb(part,semantic=None):
    suffix=('X','Y','Z') if semantic=='Normal' else ('R','G','B')
    out=[]
    for s in suffix:
        match=[k for k in part if k==s or k.endswith('.'+s)]
        if len(match)!=1:raise ValueError('Ambiguous channels '+str(list(part)))
        out.append(part[match[0]])
    return np.stack(out,-1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--radiance',required=True);ap.add_argument('--guides',required=True);ap.add_argument('--output',required=True);ap.add_argument('--normals');a=ap.parse_args()
    r=json.loads(Path(a.radiance).with_suffix('.json').read_text());g=json.loads(Path(a.guides).with_suffix('.json').read_text())
    assert r['completed'] and g['completed'] and r['scene_sha256']==g['scene_sha256'] and r['camera_matrix']==g['camera_matrix']
    radiance=X.read(Path(a.radiance));guides=X.read(Path(a.guides))
    print('channels',[(k,list(v)) for k,v in radiance.items()],[(k,list(v)) for k,v in guides.items()])
    image=rgb(next(iter(radiance.values())));d={'Image':image}
    if a.normals:
        nr=json.loads(Path(a.normals).with_suffix('.json').read_text())
        assert nr['completed'] and nr['scene_sha256']==r['scene_sha256'] and nr['camera_matrix']==r['camera_matrix']
        d['Albedo']=rgb(next(iter(guides.values())))
        nd=X.read(Path(a.normals));d['Normal']=2*rgb(next(iter(nd.values())))-1
        r['normal_guide_record']=nr;r['seconds']+=nr['seconds']
    else:
        for sem in ('Albedo','Normal'):
            p=guides.get(sem)
            if p is None:
                merged=next(iter(guides.values()));p={k:v for k,v in merged.items() if k.startswith(sem+'.')}
            try:d[sem]=rgb(p,sem)
            except ValueError:d[sem]=rgb(p)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);r['linear_files']={}
    for sem,im in d.items():
        p=out.parent/(out.stem+'_'+sem+'.exr');write_exr(p,im);r['linear_files'][sem]={'path':str(p),'sha256':sha(p)}
    r['true_first_surface_guides']=True;r['guide_samples']=g['samples'];r['seconds']+=g['seconds'];out.write_text(json.dumps(r,indent=2));print('ASSEMBLY_COMPLETE',out)
if __name__=='__main__':main()
