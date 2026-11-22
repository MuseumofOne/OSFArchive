from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive_design import script_url

class DiscoveryScriptVersionTests(unittest.TestCase):
    def test_code_only_release_gets_a_new_script_url_without_publication_changes(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);assets=root/'dist/assets';assets.mkdir(parents=True)
            script=assets/'research-discovery.js';script.write_text('first version')
            original=script_url(root,script.name)
            script.write_text('visible-page automatic refresh')
            updated=script_url(root,script.name)
            self.assertNotEqual(original,updated)
            self.assertEqual(updated,'assets/research-discovery.js?v='+sha256(script.read_bytes()).hexdigest()[:12])

if __name__=='__main__':unittest.main()
