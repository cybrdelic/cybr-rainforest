import bpy,sys,os,json
bpy.ops.wm.open_mainfile(filepath='inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_BUDGETED.blend',use_scripts=False)
s=bpy.context.scene;r={}
for o,n in [(s.cycles,'cycles'),(s.render,'render')]:
 r[n]={}
 for p in o.bl_rna.properties:
  if any(t in p.identifier for t in ('sample','time','bounce','filter','film','tile','seed','volume','transparent')):
   try:r[n][p.identifier]=getattr(o,p.identifier)
   except:pass
print('SETTINGS',json.dumps(r,default=str,indent=2),flush=True);sys.stdout.flush();os._exit(0)
