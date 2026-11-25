"""Resolve the public Ghost dialogue guide to its current captured records."""

from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit


GUIDE_SOURCE_ID = "6aad4063ee54740001bdd0d9"
GUIDE_PATH = "/the-dialogues"
PUBLIC_HOSTS = {"www.museumofone.art", "museumofone.art", "the-museum-of-one.ghost.io"}
READ_ACTION = re.compile(r"^(?:read|open|view|enter|continue(?: to)?|go to)\b", re.I)
SOURCE_CREDIT = ("originally published", "original publication")


def _https_parts(href):
    try:
        url = urlsplit(href)
        if (url.scheme == "https" and url.hostname and not url.username and not url.password
                and url.port in (None, 443)):
            return url
    except ValueError:
        pass
    return None


def _publication_path(href):
    url = _https_parts(href)
    if url and url.hostname in PUBLIC_HOSTS:
        return url.path.rstrip("/") or "/"
    return None


def guide_capture(captures):
    """Prefer the known Ghost ID, which survives edits to the guide's URL."""
    fallback = None
    for capture in captures:
        source = capture["source"]
        if source.get("id") == GUIDE_SOURCE_ID or capture["archive_id"] == f"web-{GUIDE_SOURCE_ID}":
            return capture
        if _publication_path(source["url"]) == GUIDE_PATH:
            fallback = capture
    return fallback


class _GuideParser(HTMLParser):
    def __init__(self, html, base):
        super().__init__()
        self.base = base
        self.sections = []
        self.section = None
        self.heading = None
        self.paragraph = None
        self.link = None
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attributes):
        if tag in ("h2", "h3"):
            self.section = {"title": [], "links": [], "credits": []}
            self.sections.append(self.section)
            self.heading = tag
            self.paragraph = None
        elif tag == "p" and self.section is not None:
            self.paragraph = {"text": [], "actions": []}
        elif tag == "a" and self.section is not None:
            self.link = (dict(attributes).get("href") or "", [])

    def handle_data(self, text):
        if self.heading:
            self.section["title"].append(text)
        if self.paragraph is not None:
            self.paragraph["text"].append(text)
        if self.link is not None:
            self.link[1].append(text)

    def handle_endtag(self, tag):
        if tag == self.heading:
            self.heading = None
        elif tag == "p" and self.paragraph is not None:
            # Recognize a Ghost paragraph used as a button without mistaking a
            # link in its descriptive prose for the destination of the card.
            paragraph = " ".join("".join(self.paragraph["text"]).split()).rstrip(" ↗→")
            for destination, label in self.paragraph["actions"]:
                if label.rstrip(" ↗→") == paragraph:
                    self.section["links"].append((2, destination))
            self.paragraph = None
        elif tag == "a" and self.link is not None:
            href, text = self.link
            self.link = None
            if not href:
                return
            try:
                destination = urljoin(self.base, href)
            except ValueError:
                return
            if not _https_parts(destination):
                return
            label = " ".join("".join(text).split())
            if label.casefold().startswith(SOURCE_CREDIT):
                self.section["credits"].append((destination, label))
            elif _publication_path(destination):
                if self.heading:
                    self.section["links"].append((0, destination))
                elif READ_ACTION.match(label):
                    if self.paragraph is None:
                        self.section["links"].append((1, destination))
                    else:
                        self.paragraph["actions"].append((destination, label))


def guide_sections(capture):
    """Yield titles, candidate public addresses and original credit links in guide order."""
    parser = _GuideParser(capture["readable_html"], capture["source"]["url"])
    for section in parser.sections:
        yield {"title": " ".join("".join(section["title"]).split()),
               "links": list(dict.fromkeys(href for _, href in sorted(section["links"], key=lambda link: link[0]))),
               "credits": list(dict.fromkeys(section["credits"]))}


def guided_dialogues(captures):
    """Yield one currently captured target per guide section, deduplicated by archive ID."""
    guide = guide_capture(captures)
    if guide is None:
        return
    by_path = {_publication_path(capture["source"]["url"]): capture for capture in captures if capture is not guide}
    by_path.pop(None, None)
    seen = set()
    for section in guide_sections(guide):
        candidates = (by_path.get(_publication_path(href)) for href in section["links"])
        target = next((candidate for candidate in candidates if candidate is not None), None)
        if target and target["archive_id"] not in seen:
            seen.add(target["archive_id"])
            yield section, target
