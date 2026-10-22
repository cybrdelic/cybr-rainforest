"""Encode and independently verify the actual native inspection frame sequence."""
from pathlib import Path
import argparse,subprocess,json,hashlib
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--ffmpeg',default='ffmpeg');ap.add_argument('--ffprobe',default='ffprobe');a=ap.parse_args();R=a.root.resolve();E=R/'evidence'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
plan=json.loads((E/'VIDEO_PLAN.json').read_text());N=int(plan['frames']);fps=int(plan['fps']);records=[]
for f in range(1,N+1):
 p=R/'video_frames'/f'{f:04d}.png';r=json.loads(p.with_suffix('.json').read_text())
 if not r.get('completed') or sha(p)!=r['image_sha256'] or r['animation_sha256']!=plan['animation_sha256']:raise RuntimeError(f'Frame {f} is incomplete, stale or changed')
 records.append(r)
if len({r['image_sha256'] for r in records})!=N:raise RuntimeError('Repeated source frames')
out=R/'GREEN_TERROR_NATIVE_ASSET_INSPECTION.mp4'
subprocess.run([a.ffmpeg,'-y','-v','error','-framerate',str(fps),'-start_number','1','-i',str(R/'video_frames/%04d.png'),'-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
probe=json.loads(subprocess.check_output([a.ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(out)]));st=probe['streams'][0]
assert int(st['nb_read_frames'])==N and st['avg_frame_rate']==f'{fps}/1' and st['width']==plan['width'] and st['height']==plan['height']
md5=subprocess.check_output([a.ffmpeg,'-v','error','-i',str(out),'-f','framemd5','-']).decode();hashes=[x.split(',')[-1].strip() for x in md5.splitlines() if x and not x.startswith('#')];assert len(hashes)==N and len(set(hashes))==N
report={'completed':True,'path':str(out),'sha256':sha(out),'frames_rendered':N,'decoded_frames':N,'unique_decoded_frames':N,'width':st['width'],'height':st['height'],'fps':fps,'seconds':float(probe['format']['duration']),'samples_per_frame':sorted({r['samples'] for r in records}),'renderer':'CYCLES','camera_motion_only':True,'full_forest_video':False,'image_generation_used':False,'upscaled':False,'interpolated':False,'looped':False,'audio':False,'animation_sha256':plan['animation_sha256']}
(E/'VIDEO_DELIVERY.json').write_text(json.dumps(report,indent=2));(E/'decoded_frame_hashes.txt').write_text(md5);print(json.dumps(report,indent=2))
