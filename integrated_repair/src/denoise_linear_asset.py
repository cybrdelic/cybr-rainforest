"""Denoise true Cycles multilayer radiance+native guides in a fresh process.
No geometry, no resizing, no invented surface guides. One AgX display transform.
"""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
from pathlib import Path
import bpy,sys,argparse,json,time,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);p=Path(a.input);out=Path(a.output)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
transport_record=p.with_name(p.stem+'_transport.json')
r=json.loads(p.with_suffix('.json').read_text())
if not r.get('linear_checkpoint') and transport_record.is_file():r=json.loads(transport_record.read_text())
assert r['completed'] and sha(p)==r['image_sha256'];transport_record.write_text(json.dumps(r,indent=2));t=time.monotonic()
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.cycles.use_denoising=False;s.render.resolution_x=r['width'];s.render.resolution_y=r['height'];s.render.resolution_percentage=100;s.render.compositor_device='CPU';s.render.compositor_denoise_device='CPU';s.render.compositor_precision='FULL';s.render.use_compositing=True
cam=bpy.data.objects.new('Compositor evaluation camera',bpy.data.cameras.new('Compositor camera'));s.collection.objects.link(cam);s.camera=cam
ng=bpy.data.node_groups.new('Independent native HDR denoising','CompositorNodeTree');s.compositing_node_group=ng
im=bpy.data.images.load(str(p),check_existing=False);im.size[:];node=ng.nodes.new('CompositorNodeImage');node.image=im
print('NATIVE_CHANNELS',[o.name for o in node.outputs],flush=True)
den=ng.nodes.new('CompositorNodeDenoise');den.inputs['HDR'].default_value=True;den.inputs['Prefilter'].default_value='Accurate';den.inputs['Quality'].default_value='High'
for dst,names in [('Image',['Image','Combined']),('Normal',['Denoising Normal','Normal']),('Albedo',['Denoising Albedo','Albedo'])]:
 src=next((node.outputs.get(n) for n in names if node.outputs.get(n) is not None),None)
 if src is None:raise RuntimeError('Missing actual '+dst+' render pass: '+str([o.name for o in node.outputs]))
 ng.links.new(src,den.inputs[dst])
ng.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor');result=ng.nodes.new('NodeGroupOutput');ng.links.new(den.outputs['Image'],result.inputs['Image'])
s.view_settings.view_transform=r['view_transform'];s.view_settings.look=r['look'];s.view_settings.exposure=r['exposure'];s.view_settings.gamma=r['gamma'];s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';s.render.filepath=str(out)
rec={**r,'completed':False,'output':str(out),'denoised':True,'linear_checkpoint':False,'raw_checkpoint':str(p),'transport_record':str(transport_record),'raw_checkpoint_sha256':sha(p),'denoising_separate_process':True,'denoising':'Native OIDN High / Accurate, matching Cycles normal and albedo'};out.with_suffix('.json').write_text(json.dumps(rec,indent=2))
bpy.ops.render.render(write_still=True)
rec.update(completed=True,image_sha256=sha(out),transport_seconds=r['seconds'],denoising_seconds=time.monotonic()-t,seconds=r['seconds']+time.monotonic()-t,peak_rss_mb=max_known(r.get('peak_rss_mb'),peak_rss_mib()));out.with_suffix('.json').write_text(json.dumps(rec,indent=2));print('NATIVE_FINISH_COMPLETE',flush=True)
