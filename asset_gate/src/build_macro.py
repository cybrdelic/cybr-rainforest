"""Inspect the actual first leaf in the branch; do not substitute an isolated proxy.
Upper/lower views use lights reflected about the lamina's local plane so relative
illumination is comparable. The studio receiver is hidden for this macro only.
"""
import sys,random,math,json,bpy,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
import build_assets as B
p=R/'BRANCH_ASSET_GATE.blend'
r=random.Random(773);t=.09;root=Vector((-.27+.51*t,.022*math.sin(t*3.7),.25+.18*t+.014*math.sin(t*5)))
d=B.unit((-r.uniform(.45,.86),r.uniform(-.35,.12),r.uniform(-.95,-.45)))
length=r.uniform(.15,.215)*(1-.26*t);end=root+d*.018+Vector((0,-.002,.004));normal=B.unit((r.uniform(-.14,.14),-1,r.uniform(.12,.32)))
b=B.Blade(end,d,normal,length,length*.40,'piper',773,False);center=b.pos(.50,0);n=b.normal_at(.50,0)
for side in ['UPPER','UNDERSIDE']:
 bpy.ops.wm.open_mainfile(filepath=str(p),use_scripts=False,load_ui=False);s=bpy.context.scene
 bpy.data.objects['GATE | neutral evaluation surface'].hide_render=True
 cam=s.camera;cam.location=center+n*(.32 if side=='UPPER' else -.32);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=65
 if side=='UNDERSIDE':
  for o in bpy.data.objects:
   if o.type!='LIGHT':continue
   v=o.location-center;o.location=center+v-2*v.dot(n)*n
   direction=o.rotation_euler.to_matrix()@Vector((0,0,-1));direction-=2*direction.dot(n)*n;o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
 bpy.context.view_layer.update();s.render.resolution_x=1440;s.render.resolution_y=1920;s['inspection_surface']=side;s['inspection_uses_actual_branch_geometry']=True
 path=R/f'LEAF_{side}_INSPECTION.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 (R/'evidence'/f'macro_{side.lower()}.json').write_text(json.dumps({'completed':True,'source_scene':str(p),'same_branch_geometry':True,'source_sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'output_scene':str(path),'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'blade_length_m':length,'blade_width_m':length*.40,'camera_matrix':[list(row) for row in cam.matrix_world],'lighting':'Mirrored about lamina plane for underside; upper unchanged','studio_receiver_hidden':True},indent=2))
