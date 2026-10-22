"""Portable native-tool utilities. Missing telemetry is None, never a false zero."""
from pathlib import Path
import os
import shutil
import sys


def peak_rss_mib():
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            process = ctypes.windll.kernel32.GetCurrentProcess
            process.restype = wintypes.HANDLE
            query = ctypes.windll.psapi.GetProcessMemoryInfo
            query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            query.restype = wintypes.BOOL
            if query(process(), ctypes.byref(counters), counters.cb):
                return counters.PeakWorkingSetSize / (1024 * 1024)
        except (ImportError, AttributeError, OSError):
            pass
        return None
    try:
        import resource
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return raw / (1024 * 1024 if sys.platform == 'darwin' else 1024)
    except (ImportError, AttributeError, OSError):
        return None


def max_known(*values):
    values = [value for value in values if value is not None]
    return max(values) if values else None


def trim_allocator():
    """Optional glibc optimization; absence does not change scene contents."""
    if not sys.platform.startswith('linux'):
        return False
    try:
        import ctypes
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int
        return bool(trim(0))
    except (AttributeError, OSError):
        return False


def enable_cycles_debug(bpy):
    """Enable optional controls only when the installed Blender exposes them."""
    preferences = bpy.context.preferences
    if hasattr(preferences.view, 'show_developer_ui'):
        preferences.view.show_developer_ui = True
    experimental = getattr(preferences, 'experimental', None)
    if experimental is not None and hasattr(experimental, 'use_cycles_debug'):
        experimental.use_cycles_debug = True


def find_blender(explicit=None):
    choice = explicit or os.environ.get('BLENDER')
    if choice:
        found = shutil.which(choice) or choice
        if not Path(found).is_file():
            raise FileNotFoundError('Blender executable does not exist: ' + str(choice))
        return str(Path(found).resolve())
    found = shutil.which('blender')
    if found:
        return found
    candidates = []
    if sys.platform == 'win32':
        root = os.environ.get('PROGRAMFILES')
        if root:
            candidates = sorted((Path(root) / 'Blender Foundation').glob('Blender */blender.exe'), reverse=True)
    elif sys.platform == 'darwin':
        candidates = [Path('/Applications/Blender.app/Contents/MacOS/Blender')]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError('Install Blender 4.5+ and pass --blender, set BLENDER, or add blender to PATH.')


def enum_ids(obj, name):
    prop = obj.bl_rna.properties.get(name)
    return {item.identifier for item in prop.enum_items} if prop else set()


def configure_exr(scene, *, multilayer=False):
    """Same capability contract as recovery/src/exr_compat.py."""
    settings = scene.render.image_settings
    formats = enum_ids(settings, 'file_format')
    media = enum_ids(settings, 'media_type')
    if media:
        if multilayer:
            target = next((name for name in ('MULTI_LAYER_IMAGE', 'MULTILAYER_IMAGE') if name in media), None)
            if target is None:
                raise RuntimeError('Native build lacks multilayer media support: ' + repr(sorted(media)))
            settings.media_type = target
        elif 'IMAGE' in media:
            settings.media_type = 'IMAGE'
    if multilayer and 'OPEN_EXR_MULTILAYER' in formats:
        settings.file_format = 'OPEN_EXR_MULTILAYER'
    elif multilayer and not media:
        raise RuntimeError('Native build lacks multilayer EXR support; refusing single-layer fallback. Use a Blender build exposing OPEN_EXR_MULTILAYER or a multilayer media mode.')
    elif 'OPEN_EXR' in formats:
        settings.file_format = 'OPEN_EXR'
    else:
        raise RuntimeError('Native build lacks OpenEXR support: ' + repr(sorted(formats)))
    settings.color_mode = 'RGBA'
    settings.color_depth = '32'
    settings.exr_codec = 'ZIP'
    return {'file_format': settings.file_format, 'media_type': getattr(settings, 'media_type', None),
            'color_depth': settings.color_depth, 'available_media_enums': sorted(media)}
