import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import bpy,numpy as np
import build_assets as B,repair_geometry as R
bpy.ops.wm.read_factory_settings(use_empty=True)
m=B.plain('Test',(.05,.05,.02));out=[]
def check(name,ok,detail=None):
 out.append({'name':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name)
def leaf(seed):
 q=B.Mesh('Test');B.leaf(q,(0,0,0),(1,0,.01),(0,0,1),.13,.065,'piper',seed,m,m,0,True,False);return q
for seed in (3811,3842,3911):
 a=leaf(seed);b=leaf(seed);check('deterministic leaf %d'%seed,np.array_equal(a.v,b.v))
 g=R.SupportGrid(-.85,.85,-.72,.72,120,base_func=lambda x,y:.02*x)
 fixed,rec=R.relax_leaf(np.array(a.v),a.f,g,a.last_lamina_count)
 check('finite contact vertices %d'%seed,np.isfinite(fixed).all())
 check('reduced clearance %d'%seed,rec['median_clearance_after_m']<=rec['median_clearance_before_m'])
 check('bounded p95 strain %d'%seed,rec['edge_strain_p95']<.05,rec['edge_strain_p95'])
 check('supported samples %d'%seed,rec['min_centroid_clearance_m']>-.0002,rec['min_centroid_clearance_m'])
 check('not flat %d'%seed,np.ptp(fixed[:,2])>.0003)
R.B.Blade=R.RepairBlade
for seed in (10,20,30):
 b=R.RepairBlade((0,0,0),(1,0,0),(0,0,1),.1,.018,'fern',seed)
 normal=b.normal_at(.5,.1);check('fern normal finite %d'%seed,np.isfinite(normal).all())
 check('normal is unit %d'%seed,abs(normal.length-1)<1e-5)
root=B.EV/'solver_tests.json';root.write_text(json.dumps({'completed':True,'passed':True,'tests':out,'count':len(out)},indent=2));print('SOLVER_TESTS_PASSED',len(out),flush=True)
