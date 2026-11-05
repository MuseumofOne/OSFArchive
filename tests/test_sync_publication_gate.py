import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_website_sync.py"


class PublicationGateTests(unittest.TestCase):
    def run_report(self, contents):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            if contents is not None:
                path.write_text(contents)
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
            )

    def test_verified_empty_source_can_publish_confirmed_withdrawals(self):
        self.assertEqual(
            self.run_report(
                json.dumps({"mode": "apply", "eligible_records": 0})
            ).returncode,
            0,
        )

    def test_source_outage_cannot_replace_the_last_deployment(self):
        result = self.run_report(
            json.dumps({"mode": "suspended", "eligible_records": 0})
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retain the last successful deployment", result.stderr)

    def test_missing_or_malformed_reports_never_authorize_publication(self):
        for content in [None, "{", "[]", "{}", '{"mode":"unexpected"}']:
            with self.subTest(content=content):
                self.assertNotEqual(self.run_report(content).returncode, 0)
