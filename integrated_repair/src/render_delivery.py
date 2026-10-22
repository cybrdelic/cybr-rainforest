"""Render either frozen native delivery with explicit, portable paths.

The forest uses separate scene-linear radiance, surface-color and shading-normal
passes followed by full-frame OIDN. Nothing is resized or geometrically culled.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default=os.environ.get('BLENDER', 'blender'))
    parser.add_argument('--kind', choices=('forest', 'ground'), required=True)
    parser.add_argument('--scene', type=Path)
    parser.add_argument('--camera', default='04_BARK_AND_LITTER')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if min(args.width, args.height, args.samples, args.threads) <= 0:
        parser.error('Dimensions, samples and thread count must be positive.')
    scene = (args.scene or ROOT / ('GREEN_TERROR_FOREST_REPAIRED_FINAL.blend' if args.kind == 'forest'
                                  else 'GROUND_SECTION_FINAL.blend')).resolve()
    if not scene.is_file():
        parser.error(f'Model is missing: {scene}. Supply --scene or unpack the packed model beside README.md.')
    executable = shutil.which(args.blender)
    if not executable and not args.dry_run:
        parser.error('Blender executable was not found; supply --blender /path/to/blender.')
    executable = executable or args.blender
    output = args.output.resolve()
    if output.suffix.lower() != '.png':
        parser.error('--output must be a PNG path.')
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MALLOC_ARENA_MAX='2', OMP_NUM_THREADS=str(args.threads),
               MALLOC_TRIM_THRESHOLD_='131072')
    base = [executable, '-b', '-t', str(args.threads), '--python-exit-code', '1', '-P']
    commands = []
    if args.kind == 'ground':
        commands.append([sys.executable, str(ROOT/'src/render_memory_safe.py'),
                         '--blender', executable, '--scene', str(scene), '--output', str(output),
                         '--width', str(args.width), '--height', str(args.height),
                         '--samples', str(args.samples), '--threads', str(args.threads)])
    else:
        raw = output.parent / (output.stem + '_linear')
        raw.mkdir(exist_ok=True)
        for mode, spp in (('radiance', args.samples), ('guides', 4), ('normals', 4)):
            commands.append(base + [str(ROOT/'src/render_forest.py'), '--', '--scene', str(scene),
                                    '--output', str(raw/(mode+'.exr')), '--camera', args.camera,
                                    '--width', str(args.width), '--height', str(args.height),
                                    '--samples', str(spp), '--mode', mode])
        commands.append([sys.executable, str(ROOT/'legacy/src/finish.py'), '--radiance', str(raw/'radiance.exr'),
                         '--guides', str(raw/'guides.exr'), '--normals', str(raw/'normals.exr'),
                         '--output', str(raw/'linear.json')])
        commands.append(base + [str(ROOT/'legacy/src/denoise_checkpoint.py'), '--', '--manifest',
                                str(raw/'linear.json'), '--output', str(output)])
    state = {'completed': False, 'source_scene': str(scene), 'requested_output': str(output),
             'commands': commands, 'stages': []}
    status = output.with_suffix('.launcher.json')
    if args.dry_run:
        print(json.dumps(state, indent=2))
        return
    status.write_text(json.dumps(state, indent=2))
    for index, cmd in enumerate(commands):
        begin = time.monotonic()
        log = output.parent / f'{output.stem}.stage_{index:02d}.log'
        with log.open('w') as handle:
            result = subprocess.run(cmd, env=env, stdout=handle, stderr=subprocess.STDOUT)
        state['stages'].append({'index': index, 'returncode': result.returncode,
                                'seconds': time.monotonic()-begin, 'log': str(log)})
        status.write_text(json.dumps(state, indent=2))
        if result.returncode:
            raise RuntimeError(f'Native stage {index} failed ({result.returncode}). Read {log}.')
    record = json.loads(output.with_suffix('.json').read_text())
    if not output.is_file() or not record.get('completed'):
        raise RuntimeError('Native stages exited, but no completed output record exists.')
    state['completed'] = True
    status.write_text(json.dumps(state, indent=2))
    print(output)

if __name__ == '__main__':
    main()
