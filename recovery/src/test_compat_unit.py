import unittest
from types import SimpleNamespace
from exr_compat import configure_exr
class Props:
 def __init__(self,values):self.values=values
 def get(self,name):
  vals=self.values.get(name)
  return SimpleNamespace(enum_items=[SimpleNamespace(identifier=v) for v in vals]) if vals is not None else None
class Tests(unittest.TestCase):
 def scene(self,formats,media=None):
  p={'file_format':formats}
  if media is not None:p['media_type']=media
  return SimpleNamespace(render=SimpleNamespace(image_settings=SimpleNamespace(bl_rna=SimpleNamespace(properties=Props(p)))))
 def test_new_multilayer(self):
  s=self.scene(['OPEN_EXR'],['IMAGE','MULTI_LAYER_IMAGE','VIDEO'])
  self.assertEqual(configure_exr(s,multilayer=True)['media_type'],'MULTI_LAYER_IMAGE')
 def test_single(self):
  s=self.scene(['OPEN_EXR'],['IMAGE','MULTI_LAYER_IMAGE']);r=configure_exr(s);self.assertEqual((r['media_type'],r['color_depth']),('IMAGE','32'))
 def test_old_multilayer(self):
  s=self.scene(['OPEN_EXR','OPEN_EXR_MULTILAYER']);self.assertEqual(configure_exr(s,multilayer=True)['file_format'],'OPEN_EXR_MULTILAYER')
 def test_fails_on_missing_media_mode(self):
  with self.assertRaises(RuntimeError):configure_exr(self.scene(['OPEN_EXR'],['IMAGE','VIDEO']),multilayer=True)
 def test_fails_without_exr(self):
  with self.assertRaises(RuntimeError):configure_exr(self.scene(['PNG'],['IMAGE']))
 def test_legacy_alias_only_when_supported(self):
  s=self.scene(['OPEN_EXR'],['IMAGE','MULTILAYER_IMAGE']);self.assertEqual(configure_exr(s,multilayer=True)['media_type'],'MULTILAYER_IMAGE')
if __name__=='__main__':unittest.main()
