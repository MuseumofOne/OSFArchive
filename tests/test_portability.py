import importlib.util, pathlib, tempfile, unittest, json
spec=importlib.util.spec_from_file_location('portable',pathlib.Path(__file__).resolve().parents[1]/'scripts/portable.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PortableTests(unittest.TestCase):
 def test_private_runtime_excluded_public_cache_included(self):
  with tempfile.TemporaryDirectory(prefix='Mirror Drive ') as d:
   r=pathlib.Path(d)
   for name in ['data/a.json','.sync-work/public/discovery.json','.sync-work/state.json','.sync-work/vault/private.json','.local/secret','.venv/bin/python']:
    q=r/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('{}')
   self.assertEqual(set(p.inventory(r)),{'data/a.json','.sync-work/public/discovery.json'})
 def test_reject_symlink_escape(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);(r/'escape').symlink_to('/tmp',target_is_directory=True)
   with self.assertRaises(ValueError):p.inventory(r)
 def test_private_destination(self):
  with self.assertRaises(ValueError):p.outside(pathlib.Path('/tmp/archive/backups'),pathlib.Path('/tmp/archive'))
 def test_changed_manifest_rejected_before_content(self):
  with tempfile.TemporaryDirectory() as d:
   q=pathlib.Path(d)/'manifest';q.write_text('{}')
   with self.assertRaisesRegex(ValueError,'Untrusted'):p.verify(pathlib.Path(d),q,'bad')
