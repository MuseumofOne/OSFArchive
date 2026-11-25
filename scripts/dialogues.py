"""Build the public dialogue index from the captured website guide and catalogue."""

from html import escape

from dialogue_guide import guide_capture, guided_dialogues


DESCRIPTION = "Read Museum of One’s published dialogues, with archived texts, original publications and deposited editions."


def dialogue_rows(captures, inventory, records):
    by_id = {row["id"]: row for row in inventory}
    editions = {f'items/{record["id"]}.html': record for record in records}
    if guide_capture(captures) is None:
        # An offline build can still link to the independently deposited texts.
        return [{"title": edition["title"], "summary": edition["summary"],
                 "source": edition["institutional_url"], "edition": edition}
                for edition in records if edition.get("type") == "Research dialogue" and edition.get("institutional_url")]

    rows = []
    seen = set()
    for section, capture in guided_dialogues(captures):
        target = by_id.get(capture["archive_id"])
        if not target:
            continue
        edition_path = target["edition_path"]
        key = edition_path or target["capture_path"]
        if key in seen:
            continue
        seen.add(key)
        pdfs = {asset["archive_path"] for asset in capture["attachments"]
                if (asset.get("archive_path") or "").lower().endswith(".pdf")}
        rows.append({"title": section["title"] or target["title"],
                     "summary": target["summary"], "capture_path": target["capture_path"], "pdf_count": len(pdfs),
                     "source": target["source_url"], "credits": section["credits"],
                     "edition": editions.get(edition_path)})
    return rows


def render_dialogue(row):
    edition = row["edition"]
    links = []
    work = ""
    count = ""
    if edition:
        rid = escape(str(edition["id"]), quote=True)
        if edition["title"] != row["title"]:
            work = f'<p class="dialogue-work">{escape(edition["title"])}</p>'
        if edition.get("reading_copy"):
            links.append((f"read/{rid}.html", "Read deposited edition"))
        links.append((f"items/{rid}.html", "Edition record"))
        if edition.get("doi"):
            links.append(("https://doi.org/" + edition["doi"], "DOI " + edition["doi"]))
    else:
        links.append((row["capture_path"], "Read archived exchange"))
        if row["pdf_count"]:
            noun = "PDF" if row["pdf_count"] == 1 else "PDFs"
            count = f'<p class="dialogue-files">{row["pdf_count"]} archived {noun}</p>'
    links.extend(row.get("credits") or [(row["source"], "Museum of One publication")])
    actions = "".join(
        f'<a class="{"button" if index == 0 else "text-link"}" href="{escape(href, quote=True)}">{escape(label)}</a>'
        for index, (href, label) in enumerate(links)
    )
    return (f'<article class="dialogue-entry"><h2>{escape(row["title"])}</h2>{work}'
            f'<p>{escape(row["summary"] or "")}</p>{count}<div class="actions">{actions}</div></article>')


def build_dialogues(captures, inventory, records, write, layout, pagehead):
    rows = dialogue_rows(captures, inventory, records)
    entries = "".join(render_dialogue(row) for row in rows)
    content = pagehead("Reading room", "Dialogues", DESCRIPTION)
    content += '<div class="dialogue-index">' + (entries or '<p>No dialogue records are available.</p>') + '</div>'
    write("dialogues.html", layout("Dialogues", DESCRIPTION, content, "dialogues.html"))
    return ["dialogues.html"]
