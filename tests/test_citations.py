"""Citations agree across exports without promoting source roles or dates."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from citations import build_citation_model, visible_citation, csl_json, bibtex, ris, scholar_meta


class Citations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {r["id"]: r for r in json.loads((ROOT / "data/catalogue.json").read_text())}

    def model(self, rid):
        return build_citation_model(self.records[rid], catalogue_url="https://archive.example/items/" + rid + ".html", pdf_url="https://archive.example/assets/documents/" + rid + ".pdf")

    def test_book_cites_selected_edition_not_first_edition_or_deposit_date(self):
        record = self.records["19864099"]
        before = deepcopy(record)
        model = self.model("19864099")
        self.assertEqual(record, before)
        self.assertEqual(csl_json(model)["issued"], {"date-parts": [[2026, 4]]})
        self.assertEqual(csl_json(model)["DOI"], record["doi"])
        self.assertEqual(csl_json(model)["author"], [{"family": "Vale", "given": "Dorian"}])
        self.assertIn("(2026-04)", visible_citation(model))
        self.assertIn("date = {2026-04}", bibtex(model))
        self.assertIn("DA  - 2026/04\n", ris(model))
        self.assertNotIn("2026/04/01", ris(model))
        self.assertEqual(dict(scholar_meta(model))["citation_publication_date"], "2026/04")
        self.assertEqual(dict(scholar_meta(model))["citation_pdf_url"], model["pdf_url"])

    def test_year_precision_and_book_serial_relation_do_not_create_journal(self):
        model = self.model("19864115")
        self.assertEqual(csl_json(model)["issued"]["date-parts"], [[2025]])
        self.assertEqual(dict(scholar_meta(model))["citation_publication_date"], "2025")
        self.assertNotIn("journal", model)
        self.assertNotIn("container-title", csl_json(model))
        self.assertNotIn("citation_journal_title", dict(scholar_meta(model)))

    def test_journal_metadata_is_source_qualified_and_literal(self):
        model = self.model("21786998")
        source = self.records["21786998"]
        self.assertEqual(model["journal"], source["source_journal"]["title"])
        self.assertEqual(csl_json(model)["type"], "article-journal")
        self.assertEqual(csl_json(model)["ISSN"], "2819-7232")
        self.assertIn("@article{", bibtex(model))
        self.assertIn("TY  - JOUR\n", ris(model))
        self.assertEqual(dict(scholar_meta(model))["citation_journal_title"], model["journal"])
        corrected = self.model("20593003")
        self.assertEqual(corrected["journal"], "Journal of Post-Interpretive Criticism")
        self.assertNotIn("issn", corrected)
        historical = json.loads((ROOT / "data/source/20593003.json").read_text())
        self.assertEqual(historical["metadata"]["journal"]["title"], "Journal of Post-Interpretive Critiism")

    def test_corrected_manual_remains_distinct_from_dataset_and_its_original_snapshot(self):
        record = self.records["20100136"]
        model = self.model("20100136")
        historical = json.loads((ROOT / "data/source/20100136.json").read_text())
        self.assertEqual(record["type"], "Other")
        self.assertEqual(csl_json(model)["type"], "document")
        self.assertIn("TY  - GEN\n", ris(model))
        self.assertEqual(historical["metadata"]["resource_type"]["type"], "dataset")
        self.assertEqual(record["doi"], historical["doi"])
        self.assertEqual(record["date"], historical["metadata"]["publication_date"])
        self.assertEqual(csl_json(self.model("20100139"))["type"], "dataset")

    def test_dataset_is_citable_but_receives_no_scholar_article_tags(self):
        model = self.model("20100139")
        self.assertEqual(csl_json(model)["type"], "dataset")
        self.assertIn("TY  - DATA\n", ris(model))
        self.assertIn("Dataset", bibtex(model))
        self.assertEqual(scholar_meta(model), [])
        self.assertNotIn("container-title", csl_json(model))
        self.assertIn(model["doi"], visible_citation(model))

    def test_working_paper_preserves_documented_series_and_source_citation(self):
        for rid, number in (("23430200", "2"), ("23428974", "1")):
            model = self.model(rid)
            self.assertEqual(model["series"], "Museum of One Research Working Paper")
            self.assertEqual(model["number"], number)
            self.assertIn(model["source_citation"], csl_json(model)["note"])
            self.assertIn("No. " + number, visible_citation(model))
            self.assertIn("number = {" + number + "}", bibtex(model))
            self.assertIn("M1  - " + number + "\n", ris(model))

    def test_source_creators_and_editorial_summary_do_not_become_authors_or_abstract(self):
        model = self.model("21715085")
        self.assertEqual(model["authors"], [{"family": "Vale", "given": "Dorian"}])
        self.assertNotIn("Museum of One", [v for k, v in scholar_meta(model) if k == "citation_author"])
        self.assertNotIn("abstract", csl_json(model))
        record = deepcopy(self.records["21715085"])
        record.pop("source_journal", None)
        record.pop("serial", None)
        record["keywords"] = ["Journal of Post-Interpretive Criticism", "ISSN 2819-7232"]
        self.assertNotIn("journal", build_citation_model(record))

    def test_no_filled_date_no_missing_author_inference_no_pdf_invention(self):
        record = deepcopy(self.records["19864099"])
        record["date"] = "2026-02-31"
        model = build_citation_model(record)
        self.assertNotIn("issued", csl_json(model))
        self.assertEqual(scholar_meta(model), [])
        record["date"] = "2026"
        model = build_citation_model(record)
        self.assertNotIn("citation_pdf_url", dict(scholar_meta(model)))
        record.pop("author")
        model = build_citation_model(record)
        self.assertEqual(model["authors"], [])
        self.assertEqual(scholar_meta(model), [])

    def test_bibtex_and_ris_escape_untrusted_source_values(self):
        record = {"id": "test", "title": "A {title} & 50% #1 $value", "author": "A collective\nTY  - JOUR", "type": "Book", "date": "2026"}
        model = build_citation_model(record)
        output = bibtex(model)
        self.assertIn(r"\{title\} \& 50\% \#1 \$value", output)
        self.assertEqual(ris(model).count("\nTY  - "), 0)


if __name__ == "__main__":
    unittest.main()
