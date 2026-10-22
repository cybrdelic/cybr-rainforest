"""Configure native EXR through RNA capabilities, without assuming enum spellings."""
from __future__ import annotations

def enum_ids(obj, name):
    prop = obj.bl_rna.properties.get(name)
    return {item.identifier for item in prop.enum_items} if prop else set()

def configure_exr(scene, *, multilayer=False):
    settings = scene.render.image_settings
    formats = enum_ids(settings, 'file_format')
    media = enum_ids(settings, 'media_type')
    if media:
        if multilayer:
            target = next((name for name in ('MULTI_LAYER_IMAGE', 'MULTILAYER_IMAGE') if name in media), None)
            if target is None:
                raise RuntimeError('Native build lacks a multilayer media enum: ' + repr(sorted(media)))
            settings.media_type = target
        elif 'IMAGE' in media:
            settings.media_type = 'IMAGE'
    if multilayer and 'OPEN_EXR_MULTILAYER' in formats:
        settings.file_format = 'OPEN_EXR_MULTILAYER'
    elif 'OPEN_EXR' in formats:
        settings.file_format = 'OPEN_EXR'
    else:
        raise RuntimeError('Native build lacks OpenEXR support: ' + repr(sorted(formats)))
    settings.color_mode = 'RGBA'
    settings.color_depth = '32'
    settings.exr_codec = 'ZIP'
    return {'file_format': settings.file_format,
            'media_type': getattr(settings, 'media_type', None),
            'color_depth': settings.color_depth,
            'available_media_enums': sorted(media)}
