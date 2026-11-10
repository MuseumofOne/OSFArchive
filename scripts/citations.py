"""Derive citations from an item record without changing its bibliographic claims.

The model describes the selected deposited edition, not the catalogue page or an
earlier edition. Source journal statements are transcribed literally; subjects,
editorial summaries and repository creator roles never imply authorship, journal
membership, peer review or Scholar eligibility. Scholar tags are descriptive
metadata, not a claim that a page meets every inclusion requirement.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from urllib.parse import urlsplit


def _text(value):
    return " ".join(str(value or "").split())


def _doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", _text(value), flags=re.I)


def _date_parts(value):
    value = _text(value)
    if not re.fullmatch(r"\d{4}(?:-\d{2}){0,2}", value):
        return []
    parts = [int(part) for part in value.split("-")]
    try:
        date(parts[0], parts[1] if len(parts) > 1 else 1,
             parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return []
    return parts


def _display_name(person):
    if person.get("literal"):
        return person["literal"]
    return " ".join(filter(None, [person.get("given"), person.get("family")]))


def _authors(record):
    """Only bibliographic authors qualify; a source creator can have another role.

    A comma-form repository name supplies name parts only when its display name
    exactly matches the independently supplied bibliographic author. Unparsed
    names remain literal names rather than guessing their cultural name order.
    """
    authors = record.get("bibliographic_authors") or record.get("author") or []
    if isinstance(authors, str):
        authors = [authors]
    elif isinstance(authors, dict):
        authors = [authors]
    result = []
    for author in authors:
        if isinstance(author, dict):
            person = {key: _text(author[key]) for key in ("family", "given", "literal") if author.get(key)}
            if not person and author.get("name"):
                person = {"literal": _text(author["name"])}
            elif person and "literal" not in person and "family" not in person:
                person = {"literal": person["given"]}
        else:
            label = _text(author)
            person = {"literal": label} if label else {}
            for creator in record.get("creators") or []:
                name = _text(creator.get("name")) if isinstance(creator, dict) else ""
                if name.count(",") == 1:
                    family, given = [part.strip() for part in name.split(",", 1)]
                    if family and given and f"{given} {family}".casefold() == label.casefold():
                        person = {"family": family, "given": given}
                        break
        if person and person not in result:
            result.append(person)
    return result


def build_citation_model(record, *, catalogue_url=None, pdf_url=None):
    """Return one portable, derived citation model; never mutate ``record``.

    ``pdf_url`` must identify the actual PDF, not a viewer. The caller can pass
    a verified local reading-copy URL; external repository links remain access
    links unless explicitly supplied here. No PDF location is invented.
    """
    resource_type = _text(record.get("type"))
    kind = {"book": "book", "journal article": "article-journal",
            "working paper": "report", "technical note": "report", "dataset": "dataset"}.get(resource_type.casefold(), "document")
    issued = _text(record.get("date"))
    parts = _date_parts(issued)
    doi = _doi(record.get("doi"))
    from identities import edition_isbn
    model = {
        "id": str(record.get("id") or record.get("accession") or ""),
        "title": _text(record.get("source_title") or record.get("title")),
        "authors": _authors(record), "type": kind, "resource_type": resource_type,
        "date": issued if parts else "", "date_parts": parts,
        "doi": doi, "url": "https://doi.org/" + doi if doi else _text(record.get("zenodo_url") or catalogue_url),
        "catalogue_url": _text(catalogue_url),
        "pdf_url": _text(pdf_url), "publisher": _text(record.get("publisher")),
        "language": _text(record.get("language")), "version": _text(record.get("version")),
        "source_citation": _text(record.get("citation")),
    }
    # A serial's isPartOf relation on a book does not make that book an article.
    if kind == "article-journal":
        journal = record.get("source_journal") or {}
        serial = record.get("serial") or {}
        if isinstance(journal, dict) and journal.get("title"):
            model["journal"] = _text(journal["title"])
            for source_key, key in (("volume", "volume"), ("issue", "issue"), ("pages", "pages")):
                if journal.get(source_key):
                    model[key] = _text(journal[source_key])
        elif serial.get("source_relation") in ("isPublishedIn", "isPartOf") and serial.get("title"):
            model["journal"] = _text(serial["title"])
        if model.get("journal") and serial.get("source_relation") in ("isPublishedIn", "isPartOf") and serial.get("issn"):
            model["issn"] = _text(serial["issn"])
    if kind == "book":
        if edition_isbn(record):
            model["isbn"] = _text(edition_isbn(record))
        if record.get("edition_statement"):
            model["edition"] = _text(record["edition_statement"])
    if record.get("source_abstract"):
        model["abstract"] = _text(record["source_abstract"])
    # These exact series statements are present in the reviewed source citation.
    # Keep the full citation as a note as well; do not infer a series from a title.
    if kind == "report":
        match = re.search(r"\b(Museum of One Research Working Paper) No\. (\d+)\b", model["source_citation"])
        if match:
            model["series"], model["number"] = match.groups()
    return model


def visible_citation(model):
    authors = "; ".join(_display_name(author) for author in model["authors"])
    lead = authors + ". " if authors else ""
    if model.get("date"):
        lead += "(" + model["date"] + "). "
    title = model.get("title", "")
    text = lead + title + ("" if title.endswith((".", "!", "?")) else ".")
    details = []
    if model.get("journal"):
        journal = model["journal"]
        if model.get("volume"):
            journal += ", " + model["volume"]
            if model.get("issue"):
                journal += "(" + model["issue"] + ")"
        elif model.get("issue"):
            journal += ", issue " + model["issue"]
        if model.get("pages"):
            journal += ", " + model["pages"]
        details.append(journal)
    if model.get("series"):
        details.append(model["series"] + " No. " + model["number"])
    if model.get("edition"):
        details.append(model["edition"])
    if model.get("version"):
        details.append("Version: " + model["version"])
    if model.get("publisher") and model["publisher"] not in details:
        details.append(model["publisher"])
    if details:
        text += " " + ". ".join(details) + "."
    if model.get("url"):
        text += " " + model["url"]
    return text


def csl_json(model):
    result = {"id": model["id"], "type": model["type"], "title": model["title"]}
    if model["authors"]:
        result["author"] = deepcopy(model["authors"])
    if model["date_parts"]:
        result["issued"] = {"date-parts": [model["date_parts"][:]]}
    for key, target in (("doi", "DOI"), ("url", "URL"), ("publisher", "publisher"),
                        ("language", "language"), ("journal", "container-title"),
                        ("volume", "volume"), ("issue", "issue"), ("pages", "page"),
                        ("isbn", "ISBN"), ("issn", "ISSN"), ("version", "version"),
                        ("edition", "edition"), ("series", "collection-title"),
                        ("number", "number"), ("abstract", "abstract")):
        if model.get(key):
            result[target] = model[key]
    if model.get("source_citation"):
        result["note"] = "Source citation retained verbatim: " + model["source_citation"]
    return result


def _bib_escape(value):
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
                    "&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#", "$": r"\$"}
    return "".join(replacements.get(character, character) for character in _text(value))


def bibtex(model):
    kind = {"book": "book", "article-journal": "article", "report": "techreport"}.get(model["type"], "misc")
    fields = [("title", model["title"])]
    if model["authors"]:
        names = []
        for author in model["authors"]:
            if author.get("literal"):
                # Extra braces retain an unparsed personal or corporate name.
                names.append("{" + _bib_escape(author["literal"]) + "}")
            else:
                names.append(_bib_escape(author["family"]) + (", " + _bib_escape(author["given"]) if author.get("given") else ""))
        author_field = "  author = {" + " and ".join(names) + "}"
    else:
        author_field = None
    if model["date_parts"]:
        fields += [("year", str(model["date_parts"][0])), ("date", model["date"])]
        if len(model["date_parts"]) > 1:
            fields.append(("month", str(model["date_parts"][1])))
    for key, target in (("doi", "doi"), ("url", "url"), ("publisher", "institution" if kind == "techreport" else "publisher"),
                        ("journal", "journal"), ("volume", "volume"), ("issue", "number"),
                        ("pages", "pages"), ("isbn", "isbn"), ("issn", "issn"),
                        ("edition", "edition"), ("version", "version"),
                        ("series", "type" if kind == "techreport" else "series"), ("number", "number")):
        if model.get(key):
            fields.append((target, model[key]))
    notes = []
    if model["type"] == "dataset":
        notes.append("Dataset")
    if model.get("source_citation"):
        notes.append("Source citation retained verbatim: " + model["source_citation"])
    if notes:
        fields.append(("note", " ".join(notes)))
    rendered = ["  " + key + " = {" + _bib_escape(value) + "}" for key, value in fields]
    if author_field:
        rendered.insert(1, author_field)
    key = "museumofone" + re.sub(r"[^A-Za-z0-9_-]", "", model["id"])
    return "@" + kind + "{" + key + ",\n" + ",\n".join(rendered) + "\n}\n"


def ris(model):
    kind = {"book": "BOOK", "article-journal": "JOUR", "report": "RPRT", "dataset": "DATA"}.get(model["type"], "GEN")
    fields = [("TY", kind), ("ID", model["id"]), ("TI", model["title"])]
    for author in model["authors"]:
        name = author.get("literal") or author.get("family", "") + (", " + author["given"] if author.get("given") else "")
        fields.append(("AU", name))
    if model["date_parts"]:
        fields += [("PY", str(model["date_parts"][0])), ("DA", model["date"].replace("-", "/"))]
    for key, target in (("doi", "DO"), ("url", "UR"), ("publisher", "PB"),
                        ("journal", "JO"), ("volume", "VL"), ("issue", "IS"),
                        ("isbn", "SN"), ("issn", "SN"), ("language", "LA"),
                        ("edition", "ET"), ("abstract", "AB"), ("series", "T2"), ("number", "M1")):
        if model.get(key):
            fields.append((target, model[key]))
    if model.get("pages"):
        pages = re.split(r"\s*(?:–|—|--)\s*|(?<=\d)-(?=\d)", model["pages"], maxsplit=1)
        fields.append(("SP", pages[0]))
        if len(pages) > 1:
            fields.append(("EP", pages[1]))
    if model.get("version"):
        fields.append(("N1", "Repository version: " + model["version"]))
    if model.get("source_citation"):
        fields.append(("N1", "Source citation retained verbatim: " + model["source_citation"]))
    return "\n".join(tag + "  - " + _text(value) for tag, value in fields) + "\nER  - \n"


def scholar_meta(model):
    """Return HTML meta name/content pairs for applicable academic publications.

    Callers must HTML-escape both values. A page also needs accessible crawlable
    scholarly content; tags alone cannot establish eligibility or indexing.
    Dataset PDFs remain datasets even when the deposited representation is PDF.
    """
    if model["type"] not in ("book", "article-journal", "report") or not (model["title"] and model["authors"] and model["date_parts"]):
        return []
    pairs = [("citation_title", model["title"])]
    pairs += [("citation_author", _display_name(author)) for author in model["authors"]]
    pairs.append(("citation_publication_date", model["date"].replace("-", "/")))
    for key, name in (("doi", "citation_doi"), ("journal", "citation_journal_title"),
                      ("volume", "citation_volume"), ("issue", "citation_issue"),
                      ("isbn", "citation_isbn"), ("issn", "citation_issn")):
        if model.get(key):
            pairs.append((name, model[key]))
    if model.get("pdf_url") and urlsplit(model["pdf_url"]).scheme in ("http", "https"):
        pairs.append(("citation_pdf_url", model["pdf_url"]))
    return pairs
