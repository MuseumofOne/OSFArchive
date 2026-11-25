"""Build the public dialogue index from the captured website guide and catalogue."""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from publication_arrangement import canonical_key


DIALOGUES = "https://www.museumofone.art/the-dialogues/"
DESCRIPTION = "Read Museum of One’s published dialogues, with archived texts, original publications and deposited editions."


class DialogueGuide(HTMLParser):
    """Read the headings, publication credits and standalone links of the guide."""

    def __init__(self, html):
        super().__init__()
        self.sections = []
        self.heading = None
        self.in_heading = False
        self.in_paragraph = False
        self.link = None
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attributes):
        if tag == "h2":
            self.heading = {"title": [], "links": [], "credits": []}
            self.sections.append(self.heading)
            self.in_heading = True
        elif tag == "p":
            self.in_paragraph = True
        elif tag == "a" and self.heading is not None:
            self.link = (dict(attributes).get("href") or "", [])

    def handle_data(self, text):
        if self.in_heading:
            self.heading["title"].append(text)
        if self.link is not None:
            self.link[1].append(text)

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_heading = False
        elif tag == "p":
            self.in_paragraph = False
        elif tag == "a" and self.link is not None:
            href, parts = self.link
            self.link = None
            url = urlsplit(href)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                return
            label = " ".join("".join(parts).split())
            if self.in_paragraph and label.casefold().startswith("originally published"):
                self.heading["credits"].append((href, label))
            elif not self.in_paragraph and not self.in_heading and not url.fragment:
                self.heading["links"].append(href)


def dialogue_rows(captures, inventory, records):
    by_id = {capture["archive_id"]: capture for capture in captures}
    by_source = {canonical_key(row["source_url"]): row for row in inventory}
    editions = {f'items/{record["id"]}.html': record for record in records}
    guide = by_source.pop(canonical_key(DIALOGUES), None)
    if not guide:
        # An offline build can still link to the independently deposited texts.
        return [{"title": edition["title"], "summary": edition["summary"],
                 "source": edition["institutional_url"], "edition": edition}
                for edition in records if edition.get("type") == "Research dialogue" and edition.get("institutional_url")]

    rows = []
    seen = set()
    for section in DialogueGuide(by_id[guide["id"]]["readable_html"]).sections:
        candidates = (by_source.get(canonical_key(href)) for href in section["links"])
        target = next((candidate for candidate in candidates if candidate), None)
        if not target:
            continue
        edition_path = target["edition_path"]
        key = edition_path or target["capture_path"]
        if key in seen:
            continue
        seen.add(key)
        capture = by_id[target["id"]]
        pdfs = {asset["archive_path"] for asset in capture["attachments"]
                if (asset.get("archive_path") or "").lower().endswith(".pdf")}
        rows.append({"title": " ".join("".join(section["title"]).split()) or target["title"],
                     "summary": target["summary"], "capture_path": target["capture_path"], "pdf_count": len(pdfs),
                     "source": target["source_url"], "credits": list(dict.fromkeys(section["credits"])),
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
