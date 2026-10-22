"""Numerically generated anatomical tissue atlas, shared with leaf geometry."""
import bpy, numpy as np, math
from pathlib import Path

def atlas(root,size=1024):
    u=np.linspace(-1,1,size)[None,:];t=np.linspace(0,1,size)[:,None];v=np.abs(u)
    phase=(t-.13-.108*v**1.62)/.09125
    distance=np.abs(phase-np.rint(phase))*.09125
    second=np.exp(-(distance/.0022)**2)*(1-v*.55)
    mid=np.exp(-(u/.018)**2)*(1-t*.7)
    phase2=v*13+.18*np.sin(phase*math.tau)
    cross=np.exp(-(np.abs(phase2-np.rint(phase2))/.055)**2)*np.sin(np.pi*(phase-np.floor(phase)))**2
    height=np.clip(mid*.95+second*.40+cross*.075,0,1)
    fine=.5+.23*np.sin(u*773+t*391)*np.sin(u*437-t*601)+.12*np.cos(u*1933+t*777)
    tissue=np.clip(.46+height*.52+fine*.06,0,1)
    rgba=np.ones((size,size,4),np.float32);rgba[:,:,0]=height;rgba[:,:,1]=tissue;rgba[:,:,2]=fine
    im=bpy.data.images.new('GT11 numerical vascular atlas',width=size,height=size,alpha=True,float_buffer=True)
    # Blender stores image rows bottom-up; t=0 is the lower image edge.
    im.pixels.foreach_set(rgba.ravel());im.colorspace_settings.name='Non-Color'
    p=Path(root)/'assets'/'vascular_atlas.exr';p.parent.mkdir(parents=True,exist_ok=True)
    im.filepath_raw=str(p);im.file_format='OPEN_EXR';im.save();im.pack()
    return im

def material_leaf(m,atlas,legacy=None):
    m.use_nodes=True;ns=m.node_tree.nodes;ln=m.node_tree.links;ns.clear()
    def N(t):return ns.new(t)
    def L(a,b):ln.new(a,b)
    out=N('ShaderNodeOutputMaterial');bs=N('ShaderNodeBsdfPrincipled');geo=N('ShaderNodeNewGeometry')
    uv=N('ShaderNodeAttribute');uv.attribute_name='gt7_anatomical_uv'
    c=N('ShaderNodeAttribute');c.attribute_name='gt6_color'
    tex=N('ShaderNodeTexImage');tex.image=atlas;tex.interpolation='Linear';tex.extension='EXTEND';L(uv.outputs['Vector'],tex.inputs['Vector'])
    sep=N('ShaderNodeSeparateColor');L(tex.outputs['Color'],sep.inputs['Color'])
    if legacy is not None:
        rgb=N('ShaderNodeRGB');rgb.outputs[0].default_value=legacy;color=rgb.outputs[0]
    else:color=c.outputs['Color']
    vein_tint=N('ShaderNodeMixRGB');vein_tint.blend_type='MULTIPLY';vein_tint.inputs[0].default_value=.36;L(color,vein_tint.inputs[1]);vein_tint.inputs[2].default_value=(1.12,1.14,.84,1)
    fac=N('ShaderNodeMath');fac.operation='MULTIPLY';fac.inputs[1].default_value=.35;L(sep.outputs['Red'],fac.inputs[0])
    mod=N('ShaderNodeMixRGB');L(fac.outputs[0],mod.inputs[0]);L(color,mod.inputs[1]);L(vein_tint.outputs[0],mod.inputs[2])
    L(mod.outputs[0],bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value=.39;bs.inputs['IOR'].default_value=1.43;bs.inputs['Specular IOR Level'].default_value=.35
    bs.inputs['Coat Weight'].default_value=.065;bs.inputs['Coat Roughness'].default_value=.31
    bump=N('ShaderNodeBump');bump.inputs['Distance'].default_value=.00042;bump.inputs['Strength'].default_value=.72;L(sep.outputs['Red'],bump.inputs['Height'])
    micro=N('ShaderNodeBump');micro.inputs['Distance'].default_value=.000024;micro.inputs['Strength'].default_value=.34
    L(sep.outputs['Blue'],micro.inputs['Height']);L(bump.outputs['Normal'],micro.inputs['Normal']);L(micro.outputs['Normal'],bs.inputs['Normal'])
    tr=N('ShaderNodeBsdfTranslucent');L(mod.outputs[0],tr.inputs['Color']);L(micro.outputs['Normal'],tr.inputs['Normal'])
    ran=N('ShaderNodeMapRange');ran.inputs['From Min'].default_value=.46;ran.inputs['From Max'].default_value=1;ran.inputs['To Min'].default_value=.19;ran.inputs['To Max'].default_value=.055;L(sep.outputs['Green'],ran.inputs['Value'])
    mix=N('ShaderNodeMixShader');L(ran.outputs[0],mix.inputs[0]);L(bs.outputs[0],mix.inputs[1]);L(tr.outputs[0],mix.inputs[2]);L(mix.outputs[0],out.inputs['Surface'])
    m['gt11_tissue']='Shared geometric rib layout, vein-dependent transmission, two-scale cuticle relief. No image generation.'

def improve_bark():
    result=[]
    for m in bpy.data.materials:
        if m.name not in ('Scanned fissured bark | meter-scale relief','Scanned scaly bark | knots and broken plates','Wet fissured bark + epiphytic moss'):continue
        ns=m.node_tree.nodes;ln=m.node_tree.links
        for bs in list(ns):
            if bs.type!='BSDF_PRINCIPLED' or not bs.inputs['Base Color'].is_linked:continue
            source=bs.inputs['Base Color'].links[0].from_socket
            a=ns.new('ShaderNodeAttribute');a.attribute_name='gt11_colony_cover'
            mult=ns.new('ShaderNodeMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=.75;ln.new(a.outputs['Fac'],mult.inputs[0])
            mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';ln.new(mult.outputs[0],mix.inputs[0]);ln.new(source,mix.inputs[1]);mix.inputs[2].default_value=(.36,.43,.22,1);ln.new(mix.outputs[0],bs.inputs['Base Color'])
            bs.inputs['Roughness'].default_value=.76
        result.append(m.name)
    return result
