"""Create and render one isolated botanical study without changing the checkout."""
import argparse,json,shutil,subprocess,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cybr_runtime import find_blender
def main():
 p=argparse.ArgumentParser();p.add_argument("--workdir",type=Path,required=True);p.add_argument("--blender");p.add_argument("--kind",choices=("branch","cordate","fern"),default="branch")
 p.add_argument("--width",type=int,default=320);p.add_argument("--height",type=int,default=240);p.add_argument("--samples",type=int,default=8);p.add_argument("--threads",type=int,default=2);p.add_argument("--timeout",type=int,default=600)
 a=p.parse_args();work=a.workdir.expanduser().resolve()
 if min(a.width,a.height,a.samples,a.threads,a.timeout)<=0:p.error("Dimensions, samples, threads and timeout must be positive.")
 if work.exists():p.error("--workdir must be a new directory; existing work is never overwritten.")
 blender=find_blender(a.blender);version=subprocess.run([blender,"--version"],capture_output=True,text=True,check=True,timeout=30).stdout.splitlines()[0];parsed=re.search(r"Blender (\d+)\.(\d+)",version)
 if not parsed or tuple(map(int,parsed.groups()))<(4,5):p.error("Blender 4.5+ is required; found "+version)
 shutil.copytree(ROOT/"asset_gate",work);shutil.copy2(ROOT/"cybr_runtime.py",work/"cybr_runtime.py");family={"branch":"piper","cordate":"cordate","fern":"fern"}[a.kind]
 commands=[[sys.executable,str(work/"src/make_atlases.py"),"--family",family],[blender,"--factory-startup","--background","--threads",str(a.threads),"--python-exit-code","1","--python",str(work/"src/build_assets.py"),"--","--kind",a.kind],[blender,"--factory-startup","--background","--threads",str(a.threads),"--python-exit-code","1","--python",str(work/"src/render_asset.py"),"--","--scene",str(work/(a.kind.upper()+"_ASSET_GATE.blend")),"--out",str(work/"renders/smoke.png"),"--lighting","soft","--width",str(a.width),"--height",str(a.height),"--samples",str(a.samples)]]
 for command in commands:subprocess.run(command,cwd=work,check=True,timeout=a.timeout)
 (work/"portable-run.json").write_text(json.dumps({"blender":version,"commands":commands,"scope":"One isolated static botanical study; not the missing full forest or a completed film."},indent=2),encoding="utf-8");print(work/"renders/smoke.png")
if __name__=="__main__":main()
