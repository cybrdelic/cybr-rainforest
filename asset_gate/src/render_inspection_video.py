"""Native branch inspection reel. Two real camera moves; no image interpolation.
This is a static botanical asset inspection, NOT forest animation or wind physics.
"""
from pathlib import Path
import bpy,sys,os,math,time,json,hashlib,resource
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parents[1];D=R/'video_frames';D.mkdir(exist_ok=True)
source=R/'BRANCH_ASSET_GATE.blend'
scene=R/'BRANCH_INSPECTION_ANIMATION.blend';plan_path=R/'evidence/VIDEO_PLAN.json'
resume=False
if scene.is_file() and plan_path.is_file():
 plan=json.loads(plan_path.read_text())
 current_source=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
 current_animation=hashlib.file_digest(scene.open('rb'),'sha256').hexdigest()
 if current_source!=plan.get('source_sha256') or current_animation!=plan.get('animation_sha256'):
  raise RuntimeError('Scene bytes differ from the existing frame plan. Use a new output directory instead of mixing sequences.')
 if (plan.get('width'),plan.get('height'),plan.get('frames'),plan.get('fps'),plan.get('samples_per_frame'))!=(960,720,96,24,32):
  raise RuntimeError('Existing sequence settings differ. Do not mix source frames.')
 bpy.ops.wm.open_mainfile(filepath=str(scene),load_ui=False,use_scripts=False);s=bpy.context.scene;cam=s.camera;resume=True
 print('RESUME_VERIFIED_NATIVE_SEQUENCE',flush=True)
if not resume:
 bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
 s=bpy.context.scene;s.timeline_markers.clear();s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=True;s.cycles.seed=52713;s.cycles.use_animated_seed=False
 s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.fps=24;s.frame_start=1;s.frame_end=96;s.render.use_persistent_data=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
 bpy.context.preferences.view.show_developer_ui=True;bpy.context.preferences.experimental.use_cycles_debug=True;s.cycles.debug_bvh_layout='EMBREE';s.cycles.debug_bvh_type='STATIC_BVH';s.cycles.debug_use_compact_bvh=True
 for vl in s.view_layers:vl.samples=0
 cam=s.camera;target=Vector((.02,0,.29));original=cam.location.copy();poses=[]
 for frame in range(1,97):
  shot=0 if frame<=48 else 1;u=((frame-1)%48)/47;ease=u*u*(3-2*u);angle=math.radians(-13+26*ease)*(1 if shot==0 else -1)
  cam.location=target+Matrix.Rotation(angle,3,'Z')@(original-target);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_euler',frame=frame)
  for name in ['Key_soft','Key_side','Key_back']:
   ob=bpy.data.objects[name];ob.hide_render=(name!=('Key_soft' if shot==0 else 'Key_back'));ob.keyframe_insert('hide_render',frame=frame)
  bpy.context.view_layer.update();poses.append({'frame':frame,'shot':'soft orbit' if shot==0 else 'backlit orbit','matrix':[list(v) for v in cam.matrix_world]})
 s.frame_set(1)
 scene=R/'BRANCH_INSPECTION_ANIMATION.blend';bpy.ops.wm.save_as_mainfile(filepath=str(scene),compress=True)
 plan={'source_scene':str(source),'source_sha256':hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),'animation_scene':str(scene),'animation_sha256':hashlib.file_digest(scene.open('rb'),'sha256').hexdigest(),'frames':96,'width':960,'height':720,'fps':24,'samples_per_frame':32,'camera_motion_only':True,'foliage_motion':False,'image_generation_used':False,'frame_interpolation_used':False,'poses':poses}
 (R/'evidence/VIDEO_PLAN.json').write_text(json.dumps(plan,indent=2))

bpy.context.preferences.view.show_developer_ui=True;bpy.context.preferences.experimental.use_cycles_debug=True;s.render.use_persistent_data=True
for frame in range(1,97):
 p=D/f'{frame:04d}.png';record=p.with_suffix('.json')
 if p.is_file() and record.is_file():
  prev=json.loads(record.read_text())
  if prev.get('completed') and prev.get('animation_sha256')==plan['animation_sha256'] and prev.get('image_sha256')==hashlib.file_digest(p.open('rb'),'sha256').hexdigest():continue
 s.frame_set(frame);s.render.filepath=str(p);t=time.monotonic()
 bpy.ops.render.render(write_still=True)
 rec={'completed':True,'frame':frame,'image_sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'animation_sha256':plan['animation_sha256'],'width':960,'height':720,'samples':32,'seconds':time.monotonic()-t,'camera_matrix':[list(v) for v in cam.matrix_world]}
 record.write_text(json.dumps(rec));(R/'evidence/VIDEO_PROGRESS.json').write_text(json.dumps({'completed':frame==96,'frames_complete':frame,'expected':96}));print('NATIVE_FRAME',frame,rec['seconds'],flush=True)
(R/'evidence/VIDEO_PROGRESS.json').write_text(json.dumps({'completed':True,'frames_complete':96,'expected':96}))
print('NATIVE_SEQUENCE_COMPLETE',flush=True)
