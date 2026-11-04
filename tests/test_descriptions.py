from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from descriptions import repository_description_html


class SourceDescription(unittest.TestCase):
    def test_transcription_preserves_source_words_without_running_markup(self):
        result = repository_description_html({'source_description_html': '<p>1980–2025 &amp; <em>witnessing</em>.</p><p>Edition &lt;two&gt;.</p><script>alert("injected")</script><img src=x onerror="bad()">'})
        self.assertIn('<p>1980–2025 &amp; witnessing.</p>', result)
        self.assertIn('<p>Edition &lt;two&gt;.</p>', result)
        self.assertNotIn('<script', result)
        self.assertNotIn('<img', result)
        self.assertNotIn('injected', result)
        self.assertNotIn('bad()', result)
        self.assertIn('Source transcription', result)

    def test_absent_description_does_not_invent_one(self):
        self.assertEqual(repository_description_html({'summary': 'An editorial summary'}), '')


if __name__ == '__main__':
    unittest.main()
