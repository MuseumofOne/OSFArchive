from pathlib import Path
import struct, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from image_dimensions import dimensions, enrich_images


class ImageHeaders(unittest.TestCase):
    def test_existing_cover_measurements_match_known_source_pixels(self):
        expected = {
            "foundational-essays.jpg": (750, 1197),
            "essays-from-field.webp": (750, 1196),
            "threads-of-sand.webp": (750, 1125),
            "moral-evidence-space.jpg": (750, 1197),
        }
        for name, size in expected.items():
            self.assertEqual(dimensions(str(ROOT / "dist/assets" / name)), size)

    def test_png_and_gif_headers_and_corrupt_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, body in [
                (
                    "p.png",
                    b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 320, 240),
                ),
                ("p.gif", b"GIF89a" + struct.pack("<HH", 45, 36)),
            ]:
                (p / name).write_bytes(body)
            self.assertEqual(dimensions(str(p / "p.png")), (320, 240))
            self.assertEqual(dimensions(str(p / "p.gif")), (45, 36))
            for i, body in enumerate(
                [b"", b"\xff\xd8", b"not an image", b"RIFF\x00\x00\x00\x00WEBPVP8L"]
            ):
                f = p / str(i)
                f.write_bytes(body)
                self.assertIsNone(dimensions(str(f)))

    def test_enrichment_preserves_supplied_dimensions_and_never_reads_external_paths(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "assets").mkdir()
            (out / "assets/a.gif").write_bytes(b"GIF89a" + struct.pack("<HH", 45, 36))
            original = '<img src="../assets/a.gif"><img src="https://elsewhere.example/a.gif"><img src="/../../outside.gif"><img src="../assets/a.gif" width="99">'
            html = enrich_images(
                original, "website/record.html", out, "https://archive.museumofone.art"
            )
            self.assertIn('<img src="../assets/a.gif" width="45" height="36">', html)
            self.assertIn('<img src="../assets/a.gif" width="99">', html)
            self.assertIn('<img src="https://elsewhere.example/a.gif">', html)
            self.assertIn('<img src="/../../outside.gif">', html)


if __name__ == "__main__":
    unittest.main()
