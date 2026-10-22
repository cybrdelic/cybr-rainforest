"""Read the narrow native checkpoint format: float32 scanline EXR, ZIP or NONE.

Supports multipart files written by the tested Blender file-output node. This
is not a general OpenEXR implementation; unsupported channel/compression/layout
features fail explicitly. Bytes remain scene-linear float32.
"""
from __future__ import annotations
import math
from pathlib import Path
import struct
import zlib
import numpy as np


def cstring(f) -> str:
    b=bytearray()
    while True:
        x=f.read(1)
        if not x:raise ValueError('Truncated EXR string')
        if x==b'\0':return b.decode('utf8')
        b.extend(x)
        if len(b)>65536:raise ValueError('Unreasonable EXR string')


def read(path: Path):
    with Path(path).open('rb') as f:
        magic,version=struct.unpack('<II',f.read(8))
        if magic!=20000630 or (version & 255)!=2:raise ValueError('Not a supported EXR')
        multipart=bool(version&0x1000)
        if version & (0x200|0x800):raise ValueError('Tiled/deep EXR is not supported')
        parts=[]
        while True:
            name=cstring(f)
            if not name:
                if not multipart and not parts:raise ValueError('No EXR header')
                break
            attrs={}
            while name:
                ty=cstring(f);size=struct.unpack('<I',f.read(4))[0];value=f.read(size)
                if len(value)!=size:raise ValueError('Truncated EXR attribute')
                attrs[name]=(ty,value);name=cstring(f)
            dw=struct.unpack('<4i',attrs['dataWindow'][1]);xmin,ymin,xmax,ymax=dw
            width,height=xmax-xmin+1,ymax-ymin+1
            if min(width,height)<=0 or width*height>268435456:raise ValueError('Unsupported EXR dimensions')
            compression=attrs['compression'][1][0]
            if compression not in (0,3):raise ValueError(f'Unsupported EXR compression {compression}')
            if 'type' in attrs and attrs['type'][1]!=b'scanlineimage':raise ValueError('Not scanline EXR')
            raw=attrs['channels'][1];channels=[];off=0
            while raw[off]!=0:
                stop=raw.index(0,off);channel=raw[off:stop].decode();off=stop+1
                kind,linear,pad0,pad1,pad2,xs,ys=struct.unpack_from('<i4Bii',raw,off);off+=16
                if kind!=2 or xs!=1 or ys!=1:raise ValueError('Expected full-resolution float32 channels')
                channels.append(channel)
            lines=16 if compression==3 else 1
            count=struct.unpack('<i',attrs['chunkCount'][1])[0] if 'chunkCount' in attrs else math.ceil(height/lines)
            part_name=attrs.get('name',('',b''))[1].decode() or str(len(parts))
            parts.append({'name':part_name,'attrs':attrs,'window':dw,'width':width,'height':height,
                          'compression':compression,'lines':lines,'count':count,'channels':channels,
                          'pixels':np.empty((height,len(channels),width),np.float32),
                          'covered':np.zeros(height,bool)})
            if not multipart:break
        offsets=[]
        for index,part in enumerate(parts):
            data=f.read(part['count']*8)
            if len(data)!=part['count']*8:raise ValueError('Truncated EXR offset table')
            offsets.extend((index,off) for off in struct.unpack('<'+'Q'*part['count'],data))
        for table_part,offset in offsets:
            f.seek(offset)
            idx=struct.unpack('<i',f.read(4))[0] if multipart else 0
            if idx!=table_part:raise ValueError('EXR part/offset mismatch')
            y,size=struct.unpack('<iI',f.read(8));packed=f.read(size)
            p=parts[idx];row=y-p['window'][1];rows=min(p['lines'],p['height']-row)
            if row<0 or rows<=0:raise ValueError('Invalid EXR scanline')
            nbytes=rows*len(p['channels'])*p['width']*4
            if size<nbytes and p['compression']==3:
                encoded=np.frombuffer(zlib.decompress(packed),np.uint8)
                if encoded.size!=nbytes:raise ValueError('Bad ZIP scanline length')
                values=np.empty(nbytes,np.uint8)
                values[0]=encoded[0]
                values[1:]=np.cumsum(encoded[1:].astype(np.int32)-128,dtype=np.int64)+int(encoded[0])
                decoded=np.empty(nbytes,np.uint8);middle=(nbytes+1)//2
                decoded[::2]=values[:middle];decoded[1::2]=values[middle:]
                data=decoded.tobytes()
            elif size==nbytes:data=packed
            else:raise ValueError('Unsupported/truncated EXR scanline payload')
            p['pixels'][row:row+rows]=np.frombuffer(data,'<f4').reshape(rows,len(p['channels']),p['width'])
            p['covered'][row:row+rows]=True
        result={}
        for p in parts:
            if not p['covered'].all():raise ValueError('Missing EXR scanlines')
            result[p['name']]={ch:p['pixels'][:,i,:].copy() for i,ch in enumerate(p['channels'])}
        return result


def rgb_parts(path: Path):
    parts=read(path);out={}
    for part,channels in parts.items():
        for semantic in ('Image','Normal','Albedo'):
            keys=[]
            for suffix in ('R','G','B') if semantic!='Normal' else ('X','Y','Z'):
                match=[name for name in channels if name==f'{semantic}.{suffix}' or name==suffix and part==semantic]
                if len(match)!=1:break
                keys.append(match[0])
            if len(keys)!=3 and semantic=='Normal':
                keys=[f'Normal.{suffix}' for suffix in ('R','G','B')]
                if not all(key in channels for key in keys):keys=[]
            if len(keys)==3:out[semantic]=np.stack([channels[key] for key in keys],axis=-1)
    if set(out)!=set(('Image','Normal','Albedo')):raise ValueError(f'Missing expected checkpoint parts: {list(parts)} / {list(out)}')
    if not all(np.isfinite(v).all() for v in out.values()):raise ValueError('Nonfinite checkpoint pixels')
    return out
