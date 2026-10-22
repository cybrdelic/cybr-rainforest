"""Denoise an actual Cycles EXR in a clean process, without loading the forest.

The input contains scene-linear beauty, denoising normal and denoising albedo.
The compositor reuses the original camera's recorded display transform once.
No procedural/image-generation approximation, resampling or upscaling occurs.
"""
from __future__ import annotations
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import bpy


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source_arg=parser.add_mutually_exclusive_group(required=True)
    source_arg.add_argument('--input', type=Path)
    source_arg.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    a = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    started = time.time()
    source_path=a.manifest or a.input
    raw = json.loads((a.manifest or a.input.with_suffix('.json')).read_text())
    if not raw.get('completed'):
        raise RuntimeError('Incomplete Cycles checkpoint.')
    if a.manifest:
        for item in raw['linear_files'].values():
            if sha(Path(item['path']))!=item['sha256']:raise RuntimeError('Linear checkpoint bytes changed.')
    elif sha(a.input)!=raw['image_sha256']:
        raise RuntimeError('Missing or altered Cycles checkpoint.')
    record = dict(raw)
    record.update(completed=False, output=str(a.output.resolve()),
                  raw_checkpoint=str(source_path.resolve()), raw_checkpoint_sha256=sha(source_path),
                  denoised=True, denoising_deferred_to_separate_process=True,
                  denoising_quality='HIGH', denoising_prefilter='ACCURATE',
                  denoising_guides=['normal', 'albedo'],
                  transport_seconds=raw['seconds'], transport_peak_rss_mb=raw['peak_rss_mb'])
    record.pop('image_sha256', None)
    record.pop('image_bytes', None)
    report = a.output.with_suffix('.json')

    def save():
        temporary = report.with_suffix('.json.partial')
        temporary.write_text(json.dumps(record, indent=2))
        temporary.replace(report)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    save()
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 1
        scene.cycles.use_denoising = False
        scene.render.resolution_x = raw['width']
        scene.render.resolution_y = raw['height']
        scene.render.resolution_percentage = 100
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = a.threads
        scene.render.compositor_device = 'CPU'
        scene.render.compositor_denoise_device = 'CPU'
        scene.render.compositor_precision = 'FULL'
        scene.render.use_compositing = True
        # An empty camera only drives execution of the image-input compositor.
        # Its render result is not connected to the image output.
        data = bpy.data.cameras.new('Compositor execution only')
        camera = bpy.data.objects.new('Compositor execution only', data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        group = bpy.data.node_groups.new('GT7 | independent HDR denoise', 'CompositorNodeTree')
        scene.compositing_node_group = group
        denoise = group.nodes.new('CompositorNodeDenoise')
        if a.manifest:
            for semantic in ('Image','Normal','Albedo'):
                item=raw['linear_files'][semantic]
                image=bpy.data.images.load(str(Path(item['path']).resolve()),check_existing=False)
                image.colorspace_settings.name='Non-Color'
                input_node=group.nodes.new('CompositorNodeImage');input_node.image=image
                group.links.new(input_node.outputs['Image'],denoise.inputs[semantic])
        else:
            image=bpy.data.images.load(str(a.input.resolve()),check_existing=False)
            input_node=group.nodes.new('CompositorNodeImage');input_node.image=image
            image.size[:]
            if not all(input_node.outputs.get(n) is not None for n in ('Image','Normal','Albedo')):
                raise RuntimeError('Required raw normal/albedo channels are absent.')
            for semantic in ('Image','Normal','Albedo'):
                group.links.new(input_node.outputs[semantic],denoise.inputs[semantic])
        denoise.inputs['HDR'].default_value = True
        denoise.inputs['Prefilter'].default_value = 'Accurate'
        denoise.inputs['Quality'].default_value = 'High'
        group.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        output_node = group.nodes.new('NodeGroupOutput')
        group.links.new(denoise.outputs['Image'], output_node.inputs['Image'])
        scene.view_settings.view_transform = raw['view_transform']
        scene.view_settings.look = raw['look']
        scene.view_settings.exposure = raw['exposure']
        scene.view_settings.gamma = raw.get('gamma', 1.0)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.color_depth = '16'
        scene.render.filepath = str(a.output.resolve())
        print('OFFLINE_DENOISE_BEGIN', json.dumps({'input': str(source_path), 'width': raw['width'], 'height': raw['height']}), flush=True)
        result = bpy.ops.render.render(write_still=True)
        if 'FINISHED' not in result or not a.output.is_file():
            raise RuntimeError('Native denoising did not write the expected PNG.')
        peak = peak_rss_mib()
        record.update(completed=True, denoising_seconds=time.time() - started,
                      denoising_peak_rss_mb=peak, peak_rss_mb=max(raw['peak_rss_mb'], peak),
                      seconds=raw['seconds'] + time.time() - started,
                      image_sha256=sha(a.output), image_bytes=a.output.stat().st_size)
        save()
        print('OFFLINE_DENOISE_SUCCESS', json.dumps(record), flush=True)
    except BaseException as error:
        record['error'] = str(error)
        save()
        raise

if __name__ == '__main__':
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)
