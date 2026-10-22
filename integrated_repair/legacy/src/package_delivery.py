"""Package only verified structural tests, not stale intermediate renders."""
import json,hashlib,struct,zipfile,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 scene=ROOT/'GREEN_TERROR_V11_STRUCTURE.blend';scene_hash=sha(scene)
 validation=json.loads((ROOT/'evidence/native_reopen.json').read_text())
 assert validation['passed'] and validation['scene_sha256']==scene_hash
 imgs=[]
 for stem in ('04_STRUCTURAL_REBUILD','02_BRANCHING_REBUILD'):
  p=ROOT/'renders'/(stem+'.png');r=json.loads(p.with_suffix('.json').read_text());assert r['completed'] and r['image_sha256']==sha(p) and r['scene_sha256']==scene_hash
  hdr=p.open('rb').read(32);assert hdr[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',hdr[16:24]);assert(w,h)==(r['width'],r['height'])
  imgs.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'width':w,'height':h,'bit_depth':hdr[24],'samples':r['samples'],'native_cycles':True,'separate_surface_guides':True,'scene_sha256':scene_hash,'seconds':r['seconds'],'peak_rss_mb':r['peak_rss_mb']})
 base=json.loads((ROOT/'qc/before.json').read_text());after=json.loads((ROOT/'renders/04_STRUCTURAL_REBUILD.json').read_text())
 keys=('camera_matrix','lens_mm','width','height','samples','exposure','view_transform','look','gamma')
 comparison={k:base[k]==after[k] for k in keys};assert all(comparison.values())
 script_records=[]
 for folder in ('src','upstream'):
  for p in (ROOT/folder).glob('*.py'):
   ast.parse(p.read_text());script_records.append({'file':str(p.relative_to(ROOT)),'sha256':sha(p)})
 report={'project':'GREEN TERROR','revision':'V11 structural rebuild — native look-development tests','completed_native_tests':True,'photorealism_claim':False,'production_stills_complete':False,'new_video_complete':False,'scene_file':scene.name,'scene_bytes':scene.stat().st_size,'scene_sha256':scene_hash,'native_version':validation['native_version'],'native_build':validation['native_build'],'baseline':'Preserved V9 scene with exact missing textures relinked, freshly rerendered. Not a recovered V10/V10R model.','image_generation_used':False,'upscaling_used':False,'original_placements_retained':validation['original_placements'],'packed_texture_count':len(validation['packed_images']),'comparison_controls':comparison,'lights_and_world_preserved':validation['checks']['lights'] and validation['checks']['world'],'stills':imgs,'rendered_source_scripts':script_records,'memory_tradeoffs':['Shared native moss microshoots and fern fronds, with separate seeded forms.','Lower geometric tessellation for small shrub and midstory blades; high-detail foreground blades preserved.','Original forest placement controllers and full stand retained.'],'visual_assessment':{'observed':'The new close-up has more articulated leaf surfaces and different surrounding shoot silhouettes. The wider view has more overlapping lateral growth instead of predominantly bare upright stems.','not_resolved':'Large leaves still read too uniformly, the bark remains visually dominant and insufficiently articulated, the shelf fungi/litter retain older stylized forms, and the wide shot is a low-sample test. No massive photorealism or final-quality claim.'},'remaining_limits':['Static frame-one look development; no upgraded wind or new demo video.','Finite branching families still repeat.','No global leaf/wood/litter collision-relaxation solver.','Bark and litter retain inherited scan-based assets and older macrostructure.','Tests are native 768-pixel-wide images, not a full-resolution cinematic delivery.','New source package rebuild requires the preserved V9 input checkpoint; the packed output scene can be opened independently.']}
 (ROOT/'DELIVERY_REPORT.json').write_text(json.dumps(report,indent=2))
 entries=[]
 for folder in ('src','upstream','assets','provenance','renders'):
  entries += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 entries += [ROOT/'README.md',ROOT/'DELIVERY_REPORT.json']
 entries += list((ROOT/'evidence').glob('*.json'))
 entries += [ROOT/'qc/before.png',ROOT/'qc/before.json',ROOT/'qc/after.png',ROOT/'qc/after.json']
 if (ROOT/'renders/SAME_CAMERA_COMPARISON.png').exists():pass # Already included through renders.
 dest=ROOT.parent/'GREEN_TERROR_V11_STRUCTURAL_REBUILD.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for p in sorted(set(entries)):z.write(p,'GREEN_TERROR_V11/'+str(p.relative_to(ROOT)))
 print('PACKAGE',dest,dest.stat().st_size,sha(dest));print('MODEL',scene,scene.stat().st_size,scene_hash)
if __name__=='__main__':main()
