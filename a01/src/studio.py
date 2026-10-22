"""Native Cycles asset gate; same specimen/camera, separately controlled lighting."""
# Locate the shared runtime in the checkout or portable study copy.
import sys as _runtime_sys
from pathlib import Path as _RuntimePath
for _runtime_parent in _RuntimePath(__file__).resolve().parents:
    if (_runtime_parent / "cybr_runtime.py").is_file():
        _runtime_sys.path.insert(0, str(_runtime_parent))
        break
from cybr_runtime import peak_rss_mib, max_known, configure_exr
from pathlib import Path
import sys,os,argparse,json,time,hashlib,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import botanical_assets as A

def look(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,target,energy,size,col):
    ld=bpy.data.lights.new(name,'AREA');ld.energy=energy;ld.shape='DISK';ld.size=size;ob=bpy.data.objects.new(name,ld);col.objects.link(ob);ob.location=loc;look(ob,target);return ob

def lighting(s,kind):
    for ob in list(bpy.data.objects):
        if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
    col=s.collection;target=(0,0,.39)
    if kind=='soft':
        area('Soft daylight key',(-1.5,-2.3,2.2),target,380,1.6,col);area('Sky fill',(2.0,-.5,1.7),target,90,2.2,col)
    elif kind=='grazing':
        area('Grazing side key',(-1.7,-.15,1.25),target,260,.65,col);area('Soft fill',(1.4,-2.1,1.4),target,105,2,col)
    elif kind=='back':
        area('Backlight transmission',(0,1.3,1.6),target,350,1.2,col);area('Front diffuse fill',(1,-2,1.4),target,85,2.5,col)
    if s.world is None:s.world=bpy.data.worlds.new('A01 neutral world')
    s.world.color=(.05,.05,.05);s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.34,.40,.46,1);s.world.node_tree.nodes.get('Background').inputs[1].default_value=.12

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--specimen',choices=['branch','woody','fern','group','macro'],default='branch');ap.add_argument('--light',choices=['soft','grazing','back'],default='soft');ap.add_argument('--width',type=int,default=1600);ap.add_argument('--samples',type=int,default=128);ap.add_argument('--output',required=True);ap.add_argument('--build-only',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    t=time.time();bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    spec=bpy.data.collections.new('A01 | approved-candidate botanical assets');s.collection.children.link(spec)
    if a.specimen in ('branch','macro'):A.heartleaf_branch(spec)
    elif a.specimen=='woody':A.woody_branch(spec)
    elif a.specimen=='fern':A.fern(spec)
    else:A.heartleaf_branch(spec,(-.32,.18,0));A.woody_branch(spec,(.28,.15,0));A.fern(spec,(0,-.15,0),scale=.65)
    # Neutral matte stage is only an asset inspection background.
    mat=A.plain_material('A01 | neutral inspection stage',(.055,.060,.064),.88)
    A.mesh_from('Inspection floor',[(-200,-200,-.012),(200,-200,-.012),(200,200,-.012),(-200,200,-.012)],[(0,1,2,3)],s.collection,mat)
    cam=bpy.data.cameras.new('A01 reference camera');co=bpy.data.objects.new('A01 reference camera',cam);s.collection.objects.link(co);s.camera=co
    if a.specimen=='macro':co.location=(.03,-.90,.56);look(co,(-.06,-.10,.32));cam.lens=66
    elif a.specimen=='fern':co.location=(1.0,-1.65,1.04);look(co,(0,0,.20));cam.lens=55
    elif a.specimen=='group':co.location=(1.0,-2.1,1.25);look(co,(0,.04,.35));cam.lens=49
    else:co.location=(.60,-2.12,1.07);look(co,(0,0,.45));cam.lens=57
    cam.dof.use_dof=False;lighting(s,a.light)
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=a.samples;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE'
    s.cycles.max_bounces=10;s.cycles.diffuse_bounces=5;s.cycles.glossy_bounces=5;s.cycles.transmission_bounces=8;s.cycles.seed=18371
    s.render.resolution_x=a.width;s.render.resolution_y=round(a.width*.75);s.render.resolution_percentage=100
    s.render.threads_mode='FIXED';s.render.threads=4;s.render.use_persistent_data=False
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.0
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16'
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);s.render.filepath=str(out)
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
    scene=ROOT/f'A01_{a.specimen}_{a.light}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(scene),compress=True)
    report={'completed':False,'image_generation_used':False,'photographs_used_as_textures':False,'scene':str(scene),'specimen':a.specimen,'light':a.light,'camera':[list(v) for v in co.matrix_world],'width':a.width,'height':s.render.resolution_y,'samples':a.samples,'renderer':'Cycles','blender':bpy.app.version_string,'native_resolution':True,'denoised':True,'geometry_source_sha256':hashlib.file_digest((ROOT/'src/botanical_assets.py').open('rb'),'sha256').hexdigest()}
    out.with_suffix('.json').write_text(json.dumps(report,indent=2))
    if a.build_only:return
    bpy.ops.render.render(write_still=True)
    report.update(completed=out.exists(),seconds=time.time()-t,image_sha256=hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),peak_rss_mb=peak_rss_mib())
    out.with_suffix('.json').write_text(json.dumps(report,indent=2));print('COMPLETED',report,flush=True)
if __name__=='__main__':main()
