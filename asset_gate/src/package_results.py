"""Validate the frozen outputs, make review sheets, and assemble durable archives."""
from pathlib import Path
import json,hashlib,struct,zipfile,ast,shutil,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];E=R/'evidence';D=R/'review_renders';O=R.parent

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert json.loads((E/'FINAL_PROGRESS.json').read_text()).get('completed')
assert json.loads((E/'MATTE_FINAL_PROGRESS.json').read_text()).get('completed')
validation=json.loads((E/'PACKED_NATIVE_VALIDATION.json').read_text());assert validation['completed'] and validation['source_forest_unchanged']
rows=[]
for p in sorted(D.glob('*.png')):
 rec=json.loads(p.with_suffix('.json').read_text());assert rec['completed'] and sha(p)==rec['image_sha256'];assert sha(Path(rec['scene']))==rec['scene_sha256'],p.name
 header=p.read_bytes()[:29];w,h,depth,color=struct.unpack('>IIBB',header[16:26]);assert depth==16 and (w,h)==(rec['width'],rec['height'])
 with Image.open(p) as im:
  im.load();thumb=im.copy();thumb.thumbnail((128,128));a=np.array(thumb.convert('RGB'))
  assert a.std()>5,p.name
 rows.append({'file':str(p.relative_to(R)),'width':w,'height':h,'bit_depth':depth,'sha256':sha(p),'scene':Path(rec['scene']).name,'scene_sha256':rec['scene_sha256'],'samples_max':rec['samples_max'],'lighting':rec['lighting'],'separate_denoising':rec.get('denoising_separate_process',False)})
assert len(rows)==9,len(rows)
video=json.loads((E/'VIDEO_DELIVERY.json').read_text());assert video['completed'] and sha(Path(video['path']))==video['sha256']
plan=json.loads((E/'VIDEO_PLAN.json').read_text());frame_hashes=[]
assert sha(R/'BRANCH_INSPECTION_ANIMATION.blend')==plan['animation_sha256']
for frame in range(1,97):
 p=R/'video_frames'/f'{frame:04d}.png';fr=json.loads(p.with_suffix('.json').read_text())
 assert fr.get('completed') and fr['animation_sha256']==plan['animation_sha256']
 assert sha(p)==fr['image_sha256'] and fr['samples']==32 and fr['frame']==frame
 with Image.open(p) as im:im.load();assert im.size==(960,720)
 frame_hashes.append(fr['image_sha256'])
assert len(set(frame_hashes))==96
# Controlled light changes share exactly one camera, geometry and exposure.
lightrows=[json.loads((D/f'{n}.json').read_text()) for n in ['03_BRANCH_SOFT','04_BRANCH_SIDE','05_BRANCH_BACK']]
assert len({x['scene_sha256'] for x in lightrows})==1;assert all(np.allclose(lightrows[0]['camera_matrix'],x['camera_matrix']) for x in lightrows)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
board=Image.new('RGB',(1800,496),(18,20,21));dr=ImageDraw.Draw(board)
for k,(n,label) in enumerate([('03_BRANCH_SOFT','SOFT LIGHT'),('04_BRANCH_SIDE','SIDE LIGHT'),('05_BRANCH_BACK','BACKLIGHT')]):
 im=Image.open(D/f'{n}.png').convert('RGB');im=im.resize((600,450),Image.Resampling.LANCZOS);board.paste(im,(k*600,46));dr.text((k*600+18,13),label,font=font,fill=(235,235,230))
board.save(R/'BRANCH_LIGHTING_REVIEW.jpg',quality=94)
board=Image.new('RGB',(1440,1152),(18,20,21));dr=ImageDraw.Draw(board)
for k,frame in enumerate([1,24,48,49,72,96]):
 im=Image.open(R/'video_frames'/f'{frame:04d}.png').convert('RGB');im=im.resize((480,360),Image.Resampling.LANCZOS);x=(k%3)*480;y=(k//3)*576
 board.paste(im,(x,y+42));dr.text((x+18,y+12),f'FRAME {frame:03d}',font=font,fill=(235,235,230))
# Crop unused margins in presentation only; source video/images remain untouched.
board.crop((0,0,1440,978)).save(R/'VIDEO_FRAME_REVIEW.jpg',quality=93)
contact=json.loads((E/'litter_support.json').read_text());technical=[]
for k in ['branch','cordate','fern','patch']:
 b=json.loads((E/f'{k}_build.json').read_text());uniq={v['mesh_name']:v for v in b['objects']};technical.append({'family':k,'unique_meshes':len(uniq),'unique_triangles':sum(v['triangles'] for v in uniq.values()),'zero_area_triangles':sum(v['zero_area_triangles'] for v in uniq.values()),'packed_images':b['images_packed']})
canonical=['make_atlases.py','build_assets.py','build_macro.py','refine_litter_materials.py','render_asset.py','render_memory_safe.py','denoise_linear_asset.py','render_inspection_video.py','encode_inspection.py','validate_packed_delivery.py','package_results.py']
sources=[]
for n in canonical:
 p=R/'src'/n;ast.parse(p.read_text());sources.append({'path':f'src/{n}','sha256':sha(p)})
review={'completed_native_assets':True,'full_forest_rebuilt':False,'visual_approval_for_forest_replication':False,'original_scene_unchanged':True,'primary_review_findings':['The branch makes fine venation, attachment and upper/lower surface differences substantially more readable than the earlier simple blades.','The fern frame orientation was corrected after native review; shared pinnae still show regularity.','The patch preserves curled litter instead of flattening leaves onto terrain. In the native 2K view, several dead leaves still look paper-like and stand too prominently above their support; that appearance is not approved for full-forest replication.'],'remaining_limits':['No new whole-forest branching/placement rollout in this package.','Stems remain too uniformly cylindrical and material response is authored, not spectrally measured.','Leaf edges and decay states remain finite procedural variants.','Local support raster is not a collision-free cloth or global equilibrium solution. Decay detail and shape/contact/material balance still need a further visual pass.','The four-second film is a branch inspection, not rainforest wind animation.','No exact botanical specimen reconstruction or hyperrealism certification.']}
report={'project':'GREEN TERROR','revision':'Reference-informed asset gate','completed':True,'scope':'Completed native asset studies and bounded substrate section; not a full-forest revision','native_renderer':'Blender Cycles','blender_version':validation['blender'],'image_generation_used':False,'native_resolution':True,'original_scene_sha256':validation['original_sha256'],'source_forest_unchanged':True,'stills':rows,'video':video,'asset_geometry':technical,'litter_support':{'accepted_leaves':contact['accepted_leaves'],'grid_resolution':contact['grid_resolution'],'min_sampled_clearance_m':min(r['min_support_clearance_m'] for r in contact['leaves']),'method':contact['method']},'controlled_lighting_test':{'same_scene':True,'same_camera':True,'same_dimensions':True,'lights':['soft','side','back']},'references':'README.md','substrate_provenance':'provenance/ORIGINAL_ASSET_MANIFEST.json','source_scripts':sources,'visual_review':review,'presentation_sheets':'Contact sheets are resized presentations; linked PNGs are the native originals.'}
(R/'DELIVERY_REPORT.json').write_text(json.dumps(report,indent=2));(E/'VISUAL_REVIEW.json').write_text(json.dumps(review,indent=2))
repair=json.loads((E/'2K_MEMORY_REPAIR.json').read_text());repair.update(completed_repair_test=True,native_2k_output='review_renders/07_LITTER_PATCH.png');(E/'2K_MEMORY_REPAIR.json').write_text(json.dumps(repair,indent=2))
# Durable, self-contained result bundles: no runtime executable, no font files.
renderfiles=[D/x['file'].split('/')[-1] for x in rows]+[D/(Path(x['file']).stem+'.json') for x in rows]
visual=renderfiles+[Path(video['path']),R/'BRANCH_LIGHTING_REVIEW.jpg',R/'VIDEO_FRAME_REVIEW.jpg',R/'DELIVERY_REPORT.json',R/'README.md']
evidence=[p for p in E.glob('*.json') if p.name not in ['DELIVERY_PROGRESS.json','FINAL_PROGRESS.json','FREEZE_STATUS.json'] and p.stat().st_size<3_000_000]
sourcefiles=[R/'src'/n for n in canonical]+list((R/'assets').glob('*'))+[R/'README.md',R/'requirements.txt']+list((R/'provenance').glob('*.json'))+evidence
models=[R/name for name in ['BRANCH_ASSET_GATE.blend','CORDATE_ASSET_GATE.blend','FERN_ASSET_GATE.blend','PATCH_ASSET_GATE.blend','LEAF_UPPER_INSPECTION.blend','LEAF_UNDERSIDE_INSPECTION.blend','BRANCH_INSPECTION_ANIMATION.blend']]
project=visual+sourcefiles+models+[p for p in (R/'video_frames').glob('*.json')]
# Native source frames are supplied in their own smaller inspection archive.
frames=[p for p in (R/'video_frames').glob('*.png')]+[p for p in (R/'video_frames').glob('*.json')]+[E/'VIDEO_PLAN.json',E/'VIDEO_DELIVERY.json']
def bundle(name,paths):
 dest=O/name;seen=set()
 with zipfile.ZipFile(dest,'w') as z:
  for p in paths:
   if not p.is_file() or p.suffix in ['.blend1','.pyc']:continue
   arc=str(p.relative_to(R))
   if arc in seen:continue
   seen.add(arc);kind=zipfile.ZIP_STORED if p.suffix.lower() in ['.blend','.png','.jpg','.mp4','.exr'] else zipfile.ZIP_DEFLATED
   z.write(p,arc,compress_type=kind)
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None
 return {'file':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'entries':len(seen)}
archives=[bundle('GREEN_TERROR_ASSET_GATE_RENDERS.zip',visual),bundle('GREEN_TERROR_ASSET_GATE_PROJECT.zip',project),bundle('GREEN_TERROR_ASSET_GATE_NATIVE_FRAMES.zip',frames),bundle('GREEN_TERROR_ASSET_GATE_REBUILD_SOURCE.zip',sourcefiles+[R/'DELIVERY_REPORT.json'])]
(R/'ARCHIVES.json').write_text(json.dumps(archives,indent=2));print(json.dumps(archives,indent=2))
