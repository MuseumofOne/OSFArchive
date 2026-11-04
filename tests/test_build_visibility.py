"""A future private catalogue entry must stop the build before any public write."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicBuildBoundary(unittest.TestCase):
    def test_private_entry_fails_before_overwriting_previous_artifacts(self):
        record = copy.deepcopy(json.loads((ROOT/'data/catalogue.json').read_text())[0])
        record['private'] = True
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            shutil.copytree(ROOT/'scripts', staging/'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            (staging/'data/source').mkdir(parents=True)
            (staging/'data/catalogue.json').write_text(json.dumps([record]))
            shutil.copyfile(ROOT/'data/source'/(record['id']+'.json'), staging/'data/source'/(record['id']+'.json'))
            (staging/'dist').mkdir()
            sentinel = staging/'dist/index.html'
            sentinel.write_text('Previous validated public release')
            result = subprocess.run([sys.executable, '-B', str(staging/'scripts/build.py')],
                                    cwd=staging, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not eligible for public export', result.stderr)
            self.assertEqual(sentinel.read_text(), 'Previous validated public release')
            self.assertEqual(list((staging/'dist').iterdir()), [sentinel])


if __name__ == '__main__':
    unittest.main()
