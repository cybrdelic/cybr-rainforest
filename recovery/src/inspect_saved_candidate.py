import bpy,json,sys,hashlib,time,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'recovered_library/GREEN_TERROR_A01_FOREST_CANDIDATE.blend'
t=time.time();bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def simple(v):
 try:return v.to_dict()
 except AttributeError:pass
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 try:return list(v)
 except:return str(v)
s=bpy.context.scene;out=ROOT/'recovered_library/embedded_sources';out.mkdir(exist_ok=True)
texts=[]
for text in bpy.data.texts:
 name=re.sub(r'[^A-Za-z0-9._-]','_',text.name);content=text.as_string();target=out/name;target.write_text(content)
 texts.append({'name':text.name,'path':str(target),'bytes':len(content),'sha256':hashlib.sha256(content.encode()).hexdigest()})
images=[]
for im in bpy.data.images:
 if im.source=='FILE':images.append({'name':im.name,'filepath':im.filepath,'packed':bool(im.packed_file),'packed_bytes':len(im.packed_file.data) if im.packed_file else 0,'sha256':hashlib.sha256(im.packed_file.data).hexdigest() if im.packed_file else None})
r={'completed':True,'scope':'Recovered Library A01 checkpoint audit, no V14 identity assumed','scene':str(p),'scene_bytes':p.stat().st_size,'scene_sha256':digest(p),'saved_version':list(bpy.data.version),'native_version':bpy.app.version_string,'scene_properties':{k:simple(s[k]) for k in s.keys()},'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'vertices':sum(len(m.vertices) for m in bpy.data.meshes),'faces':sum(len(m.polygons) for m in bpy.data.meshes),'collections':[c.name for c in bpy.data.collections],'images':images,'external_libraries':[l.filepath for l in bpy.data.libraries],'cameras':{o.name:{'matrix':[list(r) for r in o.matrix_world],'lens':o.data.lens} for o in s.objects if o.type=='CAMERA'},'embedded_texts':texts,'root_count':sum(o.get('gt6_instance_count',0) for o in s.objects),'frame_range':[s.frame_start,s.frame_end],'seconds':time.time()-t,'no_embedded_source_executed':True}
(ROOT/'evidence/A01_NATIVE_AUDIT.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ('completed','scene_properties','objects','vertices','faces','root_count','frame_range','seconds')},indent=2))
