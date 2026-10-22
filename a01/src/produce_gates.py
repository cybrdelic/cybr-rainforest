"""Run build, controlled integration and asset plates. Atomic gate statuses."""
import time,json,traceback
from pathlib import Path
from run_jobs import native,forest,studio
ROOT=Path(__file__).resolve().parents[1]
status={'completed':False,'started':time.time(),'completed_tasks':[]}
def save():
    p=ROOT/'evidence/production_status.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(status,indent=2));t.replace(p)
def task(name,fn):
    status['current']=name;save();fn();status['completed_tasks'].append(name);save()
try:
    task('Build local candidate',lambda:native('integrate_foliage_candidate.py',[],'integration.log'))
    task('Matched baseline render',lambda:forest('inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend','FOREST_CONTROL'))
    task('Matched candidate render',lambda:forest(str(ROOT/'A01_FOREST_CANDIDATE.blend'),'FOREST_CANDIDATE'))
    task('Macro plate',lambda:studio('macro','soft',2048,128))
    for light in ('soft','grazing','back'):
        task('Branch '+light,lambda light=light:studio('branch',light,1600,128))
    task('Fern plate',lambda:studio('fern','soft',1600,128))
    task('Woody branch plate',lambda:studio('woody','soft',1600,128))
    task('Litter support study',lambda:native('litter_section.py',[],'litter_section.log'))
    status.update(completed=True,seconds=time.time()-status['started']);save()
except BaseException as e:
    status.update(completed=False,error=str(e));save();traceback.print_exc();raise
