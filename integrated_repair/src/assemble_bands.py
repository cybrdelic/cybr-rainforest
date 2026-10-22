"""Assemble exact native full-resolution pixel rows, then denoise once.
No blending, rescaling, invented pixels, or use of diagnostic PNGs.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'legacy/src'))
import exr_checkpoint as X
from finish import rgb,write_exr

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    plan=json.loads(a.plan.read_text());w=plan['width'];h=plan['height'];height=plan['band_rows'];outputs={};allrows=[];first=None
    for mode,semantic in [('radiance','Image'),('guides','Albedo'),('normals','Normal')]:
        pixels=np.zeros((h,w,3),np.float32);covered=np.zeros(h,np.int32)
        for index,top in enumerate(range(0,h,height)):
            bottom=min(h,top+height);p=a.plan.parent/f'{mode}_{index:02d}.exr';rec=json.loads(p.with_suffix('.json').read_text())
            if not rec.get('completed') or rec['image_sha256']!=sha(p):raise RuntimeError(f'Incomplete/altered band: {p}')
            if rec['scene_sha256']!=plan['scene_sha256'] or rec['mode']!=mode:raise RuntimeError('Mixed scene or pass')
            if rec.get('crop_top',0)!=top or rec.get('crop_bottom',h)!=bottom:raise RuntimeError('Wrong row bounds')
            if first is None:first=dict(rec)
            for key in ('camera_matrix','lens_mm','exposure','view_transform','look','gamma'):
                if rec[key]!=first[key]:raise RuntimeError('Camera or display mismatch: '+key)
            data=rgb(next(iter(X.read(p).values())))
            if data.shape!=(bottom-top,w,3) or not np.isfinite(data).all():raise RuntimeError(f'Native band shape/data mismatch: {data.shape}')
            pixels[top:bottom]=2*data-1 if mode=='normals' else data
            covered[top:bottom]+=1;allrows.append({'file':str(p),'record':str(p.with_suffix('.json')),'mode':mode,'top':top,'bottom':bottom,'sha256':rec['image_sha256'],'seconds':rec['seconds'],'peak_rss_mb':rec['peak_rss_mb']})
        if not np.all(covered==1):raise RuntimeError('Missing or overlapping native pixel rows')
        if semantic=='Albedo':background_mask=np.max(np.abs(pixels),axis=2)<1e-10
        if semantic=='Normal':pixels[background_mask]=0
        dest=a.output.parent/(a.output.stem+'_'+semantic+'.exr');write_exr(dest,pixels);outputs[semantic]={'path':str(dest),'sha256':sha(dest)}
    first.pop('crop_top',None);first.pop('crop_bottom',None);first.pop('image_sha256',None);first.pop('image_bytes',None)
    first.update(completed=True,width=w,height=h,mode='radiance',samples=plan['samples'],linear_files=outputs,
                 seconds=sum(r['seconds'] for r in allrows),peak_rss_mb=max(r['peak_rss_mb'] for r in allrows),
                 true_first_surface_guides=True,guide_samples=4,bands=allrows,zero_background_normal_samples=int(background_mask.sum()),
                 assembly='Exact float32 native rows; no resizing, blending or repeated pixels; one full-frame denoise follows.',
                 geometry_culled_for_memory=False,geometry_decimated_for_memory=False,
                 source_plan=str(a.plan),source_plan_sha256=sha(a.plan))
    a.output.write_text(json.dumps(first,indent=2));print('VERIFIED_BAND_ASSEMBLY',a.output)
if __name__=='__main__':main()
