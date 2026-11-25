from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dialogues import dialogue_rows
from publication_arrangement import ESSAYS, METHODOLOGY, publication_inventory
from website_sync import Readable


ORIGIN = "https://www.museumofone.art"
TIMESTAMP = "2026-11-26T12:00:00Z"


def capture(slug, html="", *, archive_id=None, subjects=(), attachments=()):
    url = f"{ORIGIN}/{slug}/"
    return {
        "archive_id": archive_id or f"web-{slug}",
        "source": {
            "url": url, "title": slug, "kind": "page", "subjects": list(subjects),
            "published_at": TIMESTAMP, "updated_at": TIMESTAMP,
        },
        "readable_html": "".join(Readable(html, url).parts),
        "summary": "Published source summary",
        "original_published_at": TIMESTAMP,
        "first_captured_at": TIMESTAMP,
        "capture": {"captured_at": TIMESTAMP},
        "attachments": list(attachments),
    }


class DialogueAutomationTests(unittest.TestCase):
    def test_publish_guide_and_exchanges_updates_index_and_catalogue(self):
        guide = capture("the-dialogues", '''
            <div><h2>Banner exchange</h2><a href="/banner/">Read</a></div>
            <h2>Paragraph exchange</h2>
            <p><a href="/context/">Research context</a></p>
            <p><a href="/paragraph/#part-01">Read the exchange</a></p>
            <h3><a href="/linked-heading/">Linked heading</a></h3>
            <p><a href="https://outside.example/publication">Originally published elsewhere</a></p>
            <h2>Duplicate listing</h2><p><a href="/banner/">Read</a></p>
            <h2>Awaiting a public capture</h2><p><a href="/pending/">Read</a></p>
        ''')
        pdf = {"archive_path": "assets/website-captures/archived.pdf"}
        captures = [guide, capture("banner"), capture("context"),
                    capture("paragraph", attachments=[pdf, pdf]),
                    capture("linked-heading", subjects=[METHODOLOGY])]

        inventory = publication_inventory(captures, [])
        collections = {row["id"]: row["collection"] for row in inventory}
        self.assertEqual(collections["web-banner"], ESSAYS)
        self.assertEqual(collections["web-paragraph"], ESSAYS)
        self.assertEqual(collections["web-linked-heading"], METHODOLOGY)
        self.assertIsNone(collections["web-context"])

        rows = dialogue_rows(captures, inventory, [])
        self.assertEqual([row["title"] for row in rows],
                         ["Banner exchange", "Paragraph exchange", "Linked heading"])
        self.assertEqual(rows[1]["pdf_count"], 1)
        self.assertEqual(rows[2]["credits"],
                         [("https://outside.example/publication", "Originally published elsewhere")])

    def test_guide_keeps_working_if_its_published_slug_changes(self):
        guide = capture("conversations", '<h2>Dialogue</h2><p><a href="/exchange/">Read</a></p>',
                        archive_id="web-6aad4063ee54740001bdd0d9")
        captures = [guide, capture("exchange")]
        inventory = publication_inventory(captures, [])
        row, = dialogue_rows(captures, inventory, [])
        self.assertEqual(row["capture_path"], "website/web-exchange.html")


if __name__ == "__main__":
    unittest.main()
