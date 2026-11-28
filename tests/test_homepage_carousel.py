"""The visual capture remains separate from Ghost record reconciliation."""

from base64 import b64decode
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import homepage_carousel as carousel
from website_sync import digest

IMAGE = carousel.HOME + "assets/images/museum/painting.png"
PNG = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j3ioAAAAASUVORK5CYII=")
AT = "2026-11-28T08:00:00Z"


def panel(identifier=carousel.ARCHIVE_PANEL, image=IMAGE, note="Displayed without cropping."):
    return f"""
<section class="home-panel" id="{identifier}" data-index-label="Archive">
  <div class="gallery-stage"><img src="/preview.png" data-mo1-original-src="{image}" alt=""></div>
  <div class="tag-content"><span class="panel-kind">Library</span>
    <h2 class="tag-name">Digital Archive Library</h2>
    <div class="tag-description"><p>View the archive &amp; catalogue.</p></div>
    <a class="gallery-enter" href="/digital-archive-library/">Enter the archive</a>
  </div>
  <details class="artwork-credit"><summary>Image: Carl Spitzweg</summary>
    <p>Carl Spitzweg, <em>The Bookworm</em>. MGS 2265. Public domain.</p>
    <p>{note}</p><p><a href="{image}">Full image</a>
      <a href="https://example.org/source">Source record</a></p>
    <script>ordinarySourceScript()</script><button>Site control</button>
  </details>
</section>"""


def home(*panels):
    return f'<main class="site-main"><div id="museum-panels">{"".join(panels)}</div></main>'


class Fetch:
    def __init__(self, document, assets=None):
        self.document = document
        self.assets = {IMAGE: PNG} if assets is None else assets
        self.calls = []

    def get(self, url, limit):
        self.calls.append(url)
        return self.document.encode() if url == carousel.HOME else self.assets[url]


class HomepageCarouselTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.public = self.work / "public"
        self.entry = self.public / carousel.MANIFEST
        self.out = self.work / "dist"
        self.report(AT)

    def report(self, timestamp, mode="apply"):
        (self.work / "report.json").write_text(json.dumps({"mode":mode,"checked_at":timestamp}))

    def write(self, path, text):
        file = self.out / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)

    def compile(self):
        def layout(title, description, content, path):
            return f"<html><head><title>{title}</title></head><body>{content}</body></html>"
        return carousel.build_carousel(self.work, self.out, self.write, layout)

    def test_preserves_panel_order_source_links_caption_and_exact_bytes(self):
        fetch = Fetch(home(panel("panel-first"), panel()))
        manifest = carousel.capture(self.work, fetch)
        self.assertEqual(fetch.calls, [carousel.HOME, IMAGE])
        self.assertEqual([s["id"] for s in manifest["slides"]], ["panel-first",carousel.ARCHIVE_PANEL])
        claim, = manifest["assets"]
        self.assertEqual((self.public / claim["path"]).read_bytes(), PNG)
        self.assertEqual(claim["sha256"], digest(PNG))
        self.assertEqual((claim["width"], claim["height"]), (1, 1))
        self.assertEqual(self.compile(), manifest["content_sha256"])
        self.assertEqual((self.out / "metadata" / carousel.MANIFEST).read_bytes(), self.entry.read_bytes())
        self.assertEqual((self.out / claim["path"]).read_bytes(), PNG)
        rendered = (self.out / carousel.PAGE).read_text()
        self.assertIn("<em>The Bookworm</em>. MGS 2265. Public domain.", rendered)
        self.assertIn('href="https://example.org/source"', rendered)
        self.assertIn(f'href="{IMAGE}"', rendered)
        self.assertIn(f'src="{claim["path"]}"', rendered)
        self.assertNotIn("ordinarySourceScript", rendered)
        self.assertNotIn("Site control", rendered)
        self.assertNotIn("/preview.png", rendered)

    def test_same_content_keeps_digest_and_caption_change_updates_it(self):
        first = carousel.capture(self.work, Fetch(home(panel())))
        self.report("2026-11-28T09:00:00Z")
        second = carousel.capture(self.work, Fetch(home(panel())))
        changed = carousel.capture(self.work, Fetch(home(panel(note="Updated public caption."))))
        self.assertNotEqual(first["website_checked_at"], second["website_checked_at"])
        self.assertEqual(first["content_sha256"], second["content_sha256"])
        self.assertNotEqual(second["content_sha256"], changed["content_sha256"])

    def test_incomplete_and_external_sources_preserve_last_verified_snapshot(self):
        carousel.capture(self.work, Fetch(home(panel())))
        previous = self.entry.read_bytes()
        for document in (home(panel("panel-first")), home(panel(image="https://example.org/copy.png")),
                         home(panel(note='<a href="javascript:alert(1)">Bad link</a>'))):
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    carousel.capture(self.work, Fetch(document))
                self.assertEqual(self.entry.read_bytes(), previous)
        with self.assertRaises(ValueError):
            carousel.capture(self.work, Fetch(home(panel()), {IMAGE:b"<html>Error</html>"}))
        self.assertEqual(self.entry.read_bytes(), previous)

    def test_verified_source_integrity_precedes_build_replacement(self):
        manifest = carousel.capture(self.work, Fetch(home(panel())))
        self.compile()
        claim, = manifest["assets"]
        original = (self.out / claim["path"]).read_bytes()
        (self.public / claim["path"]).write_bytes(b"X" * len(PNG))
        with self.assertRaisesRegex(ValueError, "failed fixity"):
            self.compile()
        self.assertEqual((self.out / claim["path"]).read_bytes(), original)

    def test_build_without_capture_omits_its_generated_output(self):
        carousel.capture(self.work, Fetch(home(panel())))
        self.compile()
        self.entry.unlink()
        self.assertIsNone(self.compile())
        self.assertFalse((self.out / carousel.PAGE).exists())
        self.assertFalse((self.out / "metadata" / carousel.MANIFEST).exists())
        self.assertFalse((self.out / carousel.MEDIA).exists())


if __name__ == "__main__":
    unittest.main()
