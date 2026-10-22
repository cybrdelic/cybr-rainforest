import ast,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cybr_runtime as runtime
from types import SimpleNamespace
class RuntimeTests(unittest.TestCase):
 def test_multilayer_does_not_silently_fall_back_to_single(self):
  prop=SimpleNamespace(enum_items=[SimpleNamespace(identifier="OPEN_EXR")])
  settings=SimpleNamespace(bl_rna=SimpleNamespace(properties={"file_format":prop}))
  scene=SimpleNamespace(render=SimpleNamespace(image_settings=settings))
  with self.assertRaisesRegex(RuntimeError,"refusing single-layer fallback"):
   runtime.configure_exr(scene,multilayer=True)
 def test_real_memory_is_positive_or_unavailable(self):
  value=runtime.peak_rss_mib();self.assertTrue(value is None or math.isfinite(value) and value>0)
 def test_unknown_peak_is_not_zero(self):
  self.assertIsNone(runtime.max_known(None,None));self.assertEqual(runtime.max_known(None,1.25),1.25)
 def test_explicit_missing_blender_fails(self):
  with self.assertRaises(FileNotFoundError):runtime.find_blender(str(ROOT/"definitely-not-a-blender"))
 def test_all_python_sources_parse(self):
  for path in ROOT.rglob("*.py"):
   if any(part in (".venv","work","output","__pycache__") for part in path.parts):continue
   with self.subTest(path=str(path.relative_to(ROOT))):ast.parse(path.read_text(encoding="utf-8"))
 def test_archived_scripts_use_portable_memory(self):
  for path in ROOT.rglob("*.py"):
   if path.name=="cybr_runtime.py" or "tests" in path.parts:continue
   text=path.read_text(encoding="utf-8");self.assertNotIn("resource.getrusage",text,str(path))
if __name__=="__main__":unittest.main()
