import bpy,sys,os,json,math
from mathutils import Vector
from pathlib import Path
P=Path('inputs/historical/GREEN_TERROR_V11');bpy.ops.wm.open_mainfile(filepath=str(P/'GREEN_TERROR_V11_BUDGETED.blend'),use_scripts=False);s=bpy.context.scene;s.frame_set(1);cam=bpy.data.objects['04_BARK_AND_LITTER'];s.camera=cam;s.render.resolution_x=768;s.render.resolution_y=576
corners=cam.data.view_frame(scene=s);x=max(abs(v.x/v.z) for v in corners);y=max(abs(v.y/v.z) for v in corners);dg=bpy.context.evaluated_depsgraph_get();r=[]
for u,v in [(.83,.25),(.9,.5),(.9,.8),(.57,.3),(.53,.5),(.6,.74),(.18,.15),(.18,.4),(.14,.70),(.46,.22)]:
 ray=cam.matrix_world.to_quaternion() @ Vector(((2*u-1)*x,(1-2*v)*y,-1)).normalized();hit,p,n,face,ob,mat=s.ray_cast(dg,cam.matrix_world.translation,ray,distance=100)
 if hit:
  row={'pixel':[u,v],'object':ob.name,'collections':[c.name for c in ob.users_collection],'point':list(p),'normal':list(n),'matrix':[list(a) for a in mat]};r.append(row);print('HIT',row,flush=True)
(P/'evidence/camera_hosts.json').write_text(json.dumps(r,indent=2));sys.stdout.flush();os._exit(0)
