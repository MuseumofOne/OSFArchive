"""Source-checked analytic descriptions of parts within deposited book editions.

Components are local catalogue descriptions. They inherit authorship and rights
context from their parent edition; they do not create new repository deposits.
"""
from copy import deepcopy
from html import escape


def _e(value):
    return escape(str(value if value is not None else ""), quote=True)


def _books(contents):
    return contents.get("books", contents)


def attach_contents(records, contents):
    """Attach portable, source-qualified parts without mutating source data.

    The returned list contains the same record objects, as other build-time
    enrichment helpers do. Calling this twice replaces rather than duplicates
    descriptions. ``contents`` may be the complete JSON or its ``books`` member.
    """
    books = _books(contents)
    for record in records:
        rid = str(record["id"])
        book = books.get(rid, {})
        parts = []
        for index, component in enumerate(book.get("components", []), 1):
            part = deepcopy(component)
            part.update({
                "parent_id": rid,
                "parent_doi": record.get("doi"),
                "reference": f'{record["accession"]}/C{index:03}',
                "url": f'parts/{rid}-{component["id"]}.html',
                "reader_url": f'read/{rid}.html#page={component["pdf_start"]}',
                "description_level": "Local analytic description of a publication component",
                "creator": record.get("author", ""),
                "creator_inheritance": "Responsibility inherited from the parent publication; no separate chapter-level deposit or independent authorship claim is made.",
                "source": deepcopy(book.get("source", {})),
            })
            parts.append(part)
        record["contents"] = parts
    return records


def _printed(part):
    start, end = part.get("printed_start"), part.get("printed_end")
    if not start:
        return "Not separately transcribed"
    return str(start) if not end or start == end else f"{start}–{end}"


def _pdf(part):
    start, end = part["pdf_start"], part.get("pdf_end")
    return str(start) if not end or start == end else f"{start}–{end}"


def component_schema(record, part, origin):
    """Identify the local description separately from its DOI-bearing parent."""
    origin = origin.rstrip("/")
    parent_url = f'{origin}/items/{record["id"]}.html'
    doi = str(record.get("doi") or "").removeprefix("https://doi.org/")
    parent_identity = "https://doi.org/" + doi if doi else parent_url + "#publication"
    child_url = f'{origin}/{part["url"]}'
    child = {
        "@type": "Chapter" if part["type"] in ("Chapter", "Essay") else "CreativeWork",
        "@id": child_url + "#component",
        "url": child_url,
        "name": part["title"],
        "identifier": {"@type": "PropertyValue", "propertyID": "Local analytic description reference", "value": part["reference"]},
        "isPartOf": {"@id": parent_identity},
        "description": f'{part["type"]} in {record["title"]}. Local analytic description of the parent edition; creator attribution is inherited from that publication.',
        "position": int(part["id"][1:]),
        "pagination": _printed(part),
        "pageStart": part.get("printed_start", ""),
        "encoding": {"@type": "MediaObject", "contentUrl": f'{origin}/{part["evidence"]["file"]}#page={part["pdf_start"]}', "encodingFormat": "application/pdf", "description": f'Source PDF file page {_pdf(part)}; this URL opens the complete parent publication.'},
        "subjectOf": {"@id": child_url + "#description"},
    }
    if part.get("printed_end"):
        child["pageEnd"] = part["printed_end"]
    # Attribution is explicitly scoped in the description and visible record.
    if record.get("author"):
        child["author"] = {"@type": "Person", "name": record["author"]}
    parent = {"@type": "Book", "@id": parent_identity, "name": record["title"], "url": parent_url, "hasPart": {"@id": child_url + "#component"}}
    page = {"@type": "WebPage", "@id": child_url + "#description", "url": child_url, "name": part["title"], "mainEntity": {"@id": child_url + "#component"}, "description": "Local catalogue description of a component; no separate publication identifier is assigned."}
    return {"@context": "https://schema.org", "@graph": [page, child, parent]}


def _rows(record, base=""):
    rows = []
    for part in record.get("contents", []):
        rows.append(f'<tr><th scope="row"><a href="{base}{_e(part["url"])}">{_e(part["reference"])}</a></th><td><a href="{base}{_e(part["url"])}">{_e(part["title"])}</a><small>{_e(part["type"])} · Part of this edition</small></td><td>{_e(_printed(part))}</td><td><a href="{base}{_e(part["reader_url"])}">{_e(_pdf(part))} ↗</a></td></tr>')
    return ''.join(rows)


def contents_table(record, base=""):
    """Reusable contents block for a parent item page (base='../')."""
    if not record.get("contents"):
        return ""
    return f'<div class="table-scroll"><table class="inventory-table"><caption>Analytic contents · {_e(record["short_title"] if record.get("short_title") else record["title"])}</caption><thead><tr><th scope="col">Local part reference</th><th scope="col">Title / component</th><th scope="col">Printed pages</th><th scope="col">PDF file pages / read</th></tr></thead><tbody>{_rows(record, base)}</tbody></table></div>'


def build_content_pages(records, contents, write, layout, origin):
    """Write the contents directory and each component's contextual record."""
    attach_contents(records, contents)
    described = [record for record in records if record.get("contents")]
    count = sum(len(record["contents"]) for record in described)
    directory = f'''<div class="page-head"><div class="breadcrumb"><a href="index.html">Archive</a> / Analytic contents</div><div class="eyebrow">Publication components / Source-checked description</div><h1>Inside the publications</h1><p>{count} chapter, essay and supporting-text descriptions across {len(described)} published editions. Enter a book through its contents, follow an individual text, and open its first page in the reading room.</p></div><section class="item-section"><h2>Reading the references</h2><p>Titles are transcribed from full headings in the deposited PDFs and checked against their contents lists. A part reference identifies a local description within a parent publication. The edition DOI, authorship and rights remain attached to that publication.</p><p>PDF file pages count from the first file page. Printed page labels retain the book’s own pagination, including roman numerals for front matter. They can differ from the reading room page counter.</p></section>'''
    for record in described:
        directory += f'<section class="item-section" id="book-{record["id"]}"><div class="section-head"><div><div class="section-no">{_e(record["accession"])} / {_e(record.get("author"))}</div><h2><a href="items/{record["id"]}.html">{_e(record["title"])}</a></h2></div><a class="text-link" href="read/{record["id"]}.html">Open complete publication ↗</a></div>{contents_table(record)}</section>'
    write("contents.html", layout("Inside the publications", "Source-checked chapter and essay descriptions with printed pagination, source evidence and direct reading-room access.", directory, "contents.html"))
    paths = ["contents.html"]
    for record in described:
        parts = record["contents"]
        for index, part in enumerate(parts):
            evidence = part["evidence"]
            rid = str(record["id"])
            doi = str(record.get("doi") or "").removeprefix("https://doi.org/")
            content = f'''<div class="page-head"><div class="breadcrumb"><a href="../index.html">Archive</a> / <a href="../contents.html#book-{rid}">Publication contents</a> / {_e(part["reference"])}</div><div class="eyebrow">Analytic record / {_e(part["type"])}</div><h1>{_e(part["title"])}</h1><p>Part of <a href="../items/{rid}.html">{_e(record["title"])}</a></p><div class="action-row"><a class="button" href="../{_e(part["reader_url"])}">Read from PDF page {part["pdf_start"]} ↗</a><a class="text-link" href="../items/{rid}.html">Parent item record ↗</a></div></div><section class="item-section"><h2>Component description</h2><dl class="metadata"><div><dt>Local part reference</dt><dd>{_e(part["reference"])}</dd></div><div><dt>Level of description</dt><dd>Publication component · Local analytic description</dd></div><div><dt>Form</dt><dd>{_e(part["type"])} · Text in a digital PDF publication</dd></div><div><dt>Creator / responsibility</dt><dd>{_e(record.get("author"))}<br><small>{_e(part["creator_inheritance"])}</small></dd></div><div><dt>Parent item</dt><dd><a href="../items/{rid}.html">{_e(record["accession"])} · {_e(record["title"])}</a></dd></div><div><dt>Printed page labels</dt><dd>{_e(_printed(part))}</dd></div><div><dt>PDF file pages</dt><dd>{_e(_pdf(part))} · One-based file sequence</dd></div><div><dt>Source edition DOI</dt><dd><a href="https://doi.org/{_e(doi)}">{_e(doi)}</a><br><small>Identifies the complete parent edition.</small></dd></div><div><dt>Rights and reuse</dt><dd>Consult the <a href="../items/{rid}.html#rights">parent edition’s rights statement</a> and notices in the publication. Chapter-level rights have not been separately assigned by this catalogue.</dd></div></dl></section><section class="item-section"><h2>Source and description note</h2><p>This record describes a component within a published edition. It is not a separate Zenodo deposit and carries no newly assigned DOI. The title is a heading transcription, not an editorial abstract.</p><dl class="metadata"><div><dt>Title evidence</dt><dd>{_e(evidence["title_source"])}</dd></div><div><dt>Source file</dt><dd><a href="../{_e(evidence["file"])}#page={part["pdf_start"]}">Open deposited PDF at page {part["pdf_start"]} ↗</a></dd></div><div><dt>Description method</dt><dd>{_e(evidence["method"])}</dd></div><div><dt>Source review</dt><dd>{_e(evidence["reviewed"])} · Local catalogue review date</dd></div></dl></section><nav class="record-tabs" aria-label="Adjacent publication components">'''
            if index:
                previous = parts[index-1]
                content += f'<a href="{_e(previous["url"].split("/")[-1])}">← {_e(previous["title"])}</a>'
            content += f'<a href="../contents.html#book-{rid}">Complete contents ↑</a>'
            if index+1 < len(parts):
                following = parts[index+1]
                content += f'<a href="{_e(following["url"].split("/")[-1])}">{_e(following["title"])} →</a>'
            content += '</nav>'
            write(part["url"], layout(part["title"], f'{part["type"]} in {record["short_title"] if record.get("short_title") else record["title"]}. Printed pages {_printed(part)}; PDF file pages {_pdf(part)}.', content, part["url"], "../", schema=component_schema(record, part, origin)))
            paths.append(part["url"])
    return paths
