"""Native matched-camera rendering, separate first-surface guide pass."""
import bpy,sys,os,argparse,json,time,hashlib,resource,traceback,gc,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--output',required=True);ap.add_argument('--camera',default='04_BARK_AND_LITTER');ap.add_argument('--width',type=int,default=768);ap.add_argument('--height',type=int,default=576);ap.add_argument('--samples',type=int,default=24);ap.add_argument('--mode',choices=['radiance','guides','normals'],default='radiance');ap.add_argument('--top',type=int,default=0);ap.add_argument('--bottom',type=int);ap.add_argument('--frame',type=int,default=1)
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);start=time.time();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    r={'completed':False,'scene':a.scene,'scene_sha256':sha(a.scene),'camera':a.camera,'width':a.width,'height':a.height,'mode':a.mode,'samples':a.samples,'renderer':'CYCLES','image_generated':False,'native_resolution':True}
    rp=out.with_suffix('.json')
    def save():rp.write_text(json.dumps(r,indent=2))
    save();bpy.ops.wm.open_mainfile(filepath=a.scene,load_ui=False,use_scripts=False);s=bpy.context.scene
    s.timeline_markers.clear();s.frame_set(a.frame);s.camera=bpy.data.objects[a.camera]
    r['camera_matrix']=[list(x) for x in s.camera.matrix_world];r['lens_mm']=s.camera.data.lens
    # Packed bytes are externalized verbatim in memory solely for tiled I/O.
    tex=ROOT/'.render_textures';tex.mkdir(exist_ok=True)
    for i in bpy.data.images:
        if i.packed_file:
            raw=i.packed_file.data;ext=Path(i.filepath).suffix or '.png';p=tex/(hashlib.sha256(raw).hexdigest()+ext)
            if not p.exists():p.write_bytes(raw)
            i.unpack(method='REMOVE');i.filepath=str(p);i.buffers_free()
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=a.samples;s.cycles.use_sample_subset=False;s.cycles.time_limit=0;s.cycles.use_adaptive_sampling=False;s.cycles.use_denoising=False;s.cycles.use_guiding=False
    bpy.context.preferences.view.show_developer_ui=True;bpy.context.preferences.experimental.use_cycles_debug=True
    s.cycles.debug_bvh_layout='EMBREE';s.cycles.debug_bvh_type='STATIC_BVH';s.cycles.debug_use_compact_bvh=True;s.cycles.debug_use_spatial_splits=False
    r['native_bvh']='EMBREE compact; debug settings explicitly enabled'
    s.render.use_texture_cache=True;s.render.use_auto_generate_texture_cache=True;s.cycles.debug_use_texture_cache_eviction=True;s.cycles.debug_texture_cache_preserve_unused=0
    bpy.context.preferences.filepaths.texture_cache_directory=str(ROOT/'.texture_cache')
    s.render.threads_mode='FIXED';s.render.threads=4;s.render.use_persistent_data=False;s.render.use_motion_blur=False
    s.render.resolution_x=a.width;s.render.resolution_y=a.height;s.render.resolution_percentage=100;s.render.use_border=False
    for vl in s.view_layers:
        vl.samples=0
        for o in (vl,vl.cycles):
            for prop in o.bl_rna.properties:
                if prop.identifier.startswith('use_pass_') and prop.type=='BOOLEAN' and not prop.is_readonly:setattr(o,prop.identifier,prop.identifier=='use_pass_combined')
        for av in list(vl.aovs):vl.aovs.remove(av)
        vl.cycles.denoising_store_passes=False
    r.update(exposure=float(s.view_settings.exposure),look=s.view_settings.look,view_transform=s.view_settings.view_transform,gamma=s.view_settings.gamma)
    if a.bottom is not None and (a.top>0 or a.bottom<a.height):
        s.render.use_border=True;s.render.use_crop_to_border=True;s.render.border_min_x=0;s.render.border_max_x=1
        s.render.border_min_y=(a.height-a.bottom+.25)/a.height if a.bottom<a.height else 0;s.render.border_max_y=(a.height-a.top+.25)/a.height if a.top>0 else 1
        r['crop_top']=a.top;r['crop_bottom']=a.bottom;r['height']=a.bottom-a.top
    s.render.use_compositing=False;s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.render.image_settings.color_mode='RGBA';s.render.image_settings.exr_codec='ZIP';s.render.filepath=str(out)
    if a.mode!='radiance':
        volume_only=set();s.cycles.use_light_tree=False
        r['guide_emissive_light_sampling']='NONE; camera-visible emission is not a scene light'
        # This pass contains no illumination/indirect estimator in the guides.
        for mat in bpy.data.materials:
            if hasattr(mat.cycles,'emission_sampling'):mat.cycles.emission_sampling='NONE'
            if not mat.use_nodes:continue
            ns=mat.node_tree.nodes;ln=mat.node_tree.links;outn=next((n for n in ns if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
            if outn is None:continue
            if not outn.inputs['Surface'].is_linked:
                volume_only.add(mat.name)
                continue
            for l in list(outn.inputs['Volume'].links):ln.remove(l)
            bs=next((n for n in ns if n.type=='BSDF_PRINCIPLED'),None)
            em=ns.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1
            if bs:
                color=bs.inputs['Base Color']
                if color.is_linked:ln.new(color.links[0].from_socket,em.inputs['Color'])
                else:em.inputs['Color'].default_value=color.default_value
            else:em.inputs['Color'].default_value=(.05,.05,.05,1)
            if a.mode=='normals':
                for edge in list(em.inputs['Color'].links):ln.remove(edge)
                geo=ns.new('ShaderNodeNewGeometry');mul=ns.new('ShaderNodeVectorMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=(.5,.5,.5)
                add=ns.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.5,.5,.5)
                normal_socket=bs.inputs['Normal'].links[0].from_socket if bs and bs.inputs['Normal'].is_linked else geo.outputs['Normal']
                ln.new(normal_socket,mul.inputs[0]);ln.new(mul.outputs[0],add.inputs[0]);ln.new(add.outputs[0],em.inputs['Color'])
            ln.new(em.outputs[0],outn.inputs['Surface'])
        r['volume_only_objects_excluded_from_surface_guide']=[]
        for ob in s.objects:
            if ob.type=='MESH' and len(ob.data.materials)>0 and all(m and m.name in volume_only for m in ob.data.materials):
                ob.hide_render=True;r['volume_only_objects_excluded_from_surface_guide'].append(ob.name)
        for n in s.world.node_tree.nodes:
            if n.type=='BACKGROUND':n.inputs['Strength'].default_value=0
        r['guide_encoding']='normal * 0.5 + 0.5' if a.mode=='normals' else 'first-surface material base color'
        # Write native combined emission and geometric normals directly.
        # No compositor is kept resident alongside the forest.
        s.render.use_compositing=False;s.render.image_settings.file_format='OPEN_EXR'
    gc.collect();ctypes.CDLL(None).malloc_trim(0);save();print('NATIVE_RENDER_BEGIN',r,flush=True)
    bpy.ops.render.render(write_still=True)
    if not out.exists():
        candidates=list(out.parent.glob(out.stem+'*.exr'))
        if len(candidates)==1:candidates[0].replace(out)
    if not out.is_file():raise RuntimeError('No native EXR output '+str(out))
    r.update(completed=True,seconds=time.time()-start,peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,image_sha256=sha(out),image_bytes=out.stat().st_size);save();print('NATIVE_RENDER_DONE',r,flush=True)
if __name__=='__main__':
    try:main()
    except BaseException:traceback.print_exc();sys.stdout.flush();os._exit(1)
    sys.stdout.flush();os._exit(0)
