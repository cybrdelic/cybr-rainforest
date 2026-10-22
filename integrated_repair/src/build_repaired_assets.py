import bpy,sys,os,json,time,hashlib,argparse
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_assets as B
import repair_geometry as R
ROOT=B.ROOT

def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def main(kind):
 t=time.time();s=B.configure();c=B.add_collection('REPAIR | asset geometry');stem=B.stemmaterial();vein=B.plain('GATE | raised abaxial veins',(.087,.111,.031),.65)
 support=None
 if kind=='patch':
  B.append_existing_substrate(c)
  soil=B.Mesh('REPAIR | original sampled soil');vs=[];fs=[];uv=[];nx,ny=161,141
  for iy,y in enumerate(np.linspace(-.72,.72,ny)):
   for ix,x in enumerate(np.linspace(-.85,.85,nx)):
    vs.append((float(x),float(y),B.soil_z(float(x),float(y))));uv.append((ix/(nx-1),iy/(ny-1)))
    if ix and iy:
     a=(iy-1)*nx+ix-1;fs.append((a,a+1,a+1+nx,a+nx))
  soil.add(vs,fs,uv,B.soilmat());soil.finish(c)
  print('Support BVH starting',flush=True)
  grid=R.SupportGrid(-.85,.85,-.72,.72,480,B.SUPPORT_BVHS)
  _,support=R.litter_patch(c,stem,vein,grid,count=360,seed=3771)
  (B.EV/'repaired_litter_contacts.json').write_text(json.dumps(support,indent=2));print('Contact pass complete',support['accepted'],flush=True)
  fc=B.add_collection('REPAIR | fern crown');root=R.fern_meshes(fc,stem,vein,881);root.location=(-.48,.34,.01);root.scale=(.67,)*3
  bc=B.add_collection('REPAIR | leafy seedlings')
  for k,(loc,H,fam) in enumerate([((.36,.1,.015),.55,'piper'),((-.43,-.38,.01),.2,'cordate'),((.5,.40,.012),.22,'piper'),((.1,-.46,.009),.20,'piper')]):
   o=R.rooted_plant(bc,stem,vein,173+k*89,H,fam,lod=True);o.location=loc
  s.camera=B.camera('Review_camera',(1.14,-1.65,1.13),(0,.06,.13),57)
 elif kind=='fern':
  R.fern_meshes(c,stem,vein,881);s.camera=B.camera('Review_camera',(1.20,-1.85,1.65),(0,0,.30),59)
 elif kind=='branch':
  B.create_branch(c,stem,vein,'piper',773);s.camera=B.camera('Review_camera',(.32,-1.32,.70),(.02,0,.29),66)
 floor=B.Mesh('REPAIR | neutral evaluation surface');floor.add([(-200,-200,-.025),(200,-200,-.025),(200,200,-.025),(-200,200,-.025)],[(0,1,2,3)],[(0,0),(1,0),(1,1),(0,1)],B.plain('REPAIR | neutral background',(.022,.027,.029),.9),False);floor.finish(c)
 B.light('Key_soft',(-.75,-.85,1.65),(0,0,.3),130,.95,(1,.96,.89));B.light('Fill',(.65,-.85,1.05),(0,0,.3),32,.85,(.78,.89,1))
 B.light('Key_side',(-.95,-.48,.65),(0,0,.35),95,.38,(1,.96,.90));B.light('Key_back',(.25,.85,1),(0,0,.35),125,.65,(1,.97,.9))
 for n in ['Key_side','Key_back']:bpy.data.objects[n].hide_render=True
 changes=R.material_adjustments()
 for im in bpy.data.images:
  if im.source=='FILE' and not im.packed_file:im.pack()
 out=ROOT/(kind.upper()+'_REPAIRED.blend');bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
 report={'completed':True,'kind':kind,'scene':str(out),'scene_sha256':sha(out),'seconds':time.time()-t,'image_generation_used':False,'material_changes':changes,'litter_accepted':support['accepted'] if support else None,'scope':'asset repair; original camera/lighting preserved, no forest rollout in this build'}
 (B.EV/(kind+'_repair_build.json')).write_text(json.dumps(report,indent=2));print('DONE',report,flush=True)
if __name__=='__main__':main(sys.argv[-1])
