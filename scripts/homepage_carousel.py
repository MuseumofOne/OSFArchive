"""Capture the public Museum of One homepage panels as static archive evidence."""

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit
import json
import os
import re
import shutil

from archive_design import asset_url
from image_dimensions import dimensions
from website_sync import Fetcher, ORIGIN, ROOT, atomic, digest, encoded, is_upload

HOME = ORIGIN + "/"
PAGE = "homepage-carousel.html"
MANIFEST = "homepage-carousel.json"
MEDIA = "assets/homepage-carousel"
ARCHIVE_PANEL = "panel-digital-archive-library"
STYLESHEET = "homepage-carousel.css"
MIMES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
SAFE_TAGS = {"a", "b", "br", "cite", "em", "i", "p", "small", "strong", "sub", "sup"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
OMIT = {"script", "style", "template", "svg", "button"}
ID = re.compile(r"panel-[a-z0-9-]{1,100}")
SHA = re.compile(r"[a-f0-9]{64}")
MAX_ASSET = 8_000_000
MAX_TOTAL_ASSETS = 32_000_000
MAX_MANIFEST = 256_000


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def has(self, value):
        return value in (self.attrs.get("class") or "").split()

    def elements(self):
        for child in self.children:
            if isinstance(child, Element) and child.tag not in OMIT:
                yield child
                yield from child.elements()


class Homepage(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.stack = [Element("document")]
        self.feed(body)
        self.close()

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag not in VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def one(elements, predicate, label):
    found = [e for e in elements if predicate(e)]
    if len(found) != 1:
        raise ValueError(f"Homepage carousel has {len(found)} matches for {label}")
    return found[0]


def link_url(value):
    url = urljoin(HOME, value)
    parts = urlsplit(url)
    if (not value or not parts.netloc or parts.scheme not in {"https", "http"}
            or parts.username or parts.password or any(ch.isspace() for ch in url)):
        raise ValueError("Invalid homepage carousel link")
    return url


def media_url(value):
    url = link_url(value)
    parts = urlsplit(url)
    theme_asset = parts.netloc == urlsplit(HOME).netloc and parts.path.startswith("/assets/images/museum/")
    if parts.scheme != "https" or parts.fragment or not (theme_asset or is_upload(url)):
        raise ValueError("Carousel image is outside the approved Museum of One media origins")
    return url


def fragment(element):
    """Keep authored text, paragraph breaks and inline links; discard active markup."""
    result = []
    for child in element.children:
        if isinstance(child, str):
            result.append(child)
        elif child.tag not in OMIT and child.tag not in {"img", "iframe", "embed", "object"}:
            children = fragment(child)
            if child.tag in SAFE_TAGS:
                token = {"tag": child.tag, "children": children}
                if child.tag == "a":
                    token["href"] = link_url(child.attrs.get("href") or "")
                result.append(token)
            else:
                result.extend(children)
    return result


def plain(tokens):
    return " ".join("".join(t if isinstance(t, str) else plain(t["children"]) for t in tokens).split())


def render_fragment(tokens, depth=0):
    if not isinstance(tokens, list) or depth > 12:
        raise ValueError("Invalid carousel caption nesting")
    parts = []
    for token in tokens:
        if isinstance(token, str):
            parts.append(escape(token))
            continue
        if not isinstance(token, dict) or token.get("tag") not in SAFE_TAGS:
            raise ValueError("Invalid carousel caption element")
        tag = token["tag"]
        fields = {"tag", "children", "href"} if tag == "a" else {"tag", "children"}
        if set(token) != fields:
            raise ValueError("Invalid carousel caption fields")
        attrs = f' href="{escape(link_url(token["href"]), quote=True)}"' if tag == "a" else ""
        content = render_fragment(token["children"], depth + 1)
        parts.append("<br>" if tag == "br" else f"<{tag}{attrs}>{content}</{tag}>")
    return "".join(parts)


def parse_homepage(body):
    document = Homepage(body).stack[0]
    main = one(document.elements(), lambda e: e.tag == "main" and e.has("site-main"), "main")
    region = one(main.elements(), lambda e: e.attrs.get("id") == "museum-panels", "museum-panels")
    slides = []
    for panel in region.children:
        if not isinstance(panel, Element) or panel.tag != "section" or not panel.has("home-panel"):
            continue
        copy = one(panel.elements(), lambda e: e.has("tag-content"), "panel copy")
        heading = one(copy.elements(), lambda e: e.tag == "h2" and e.has("tag-name"), "panel heading")
        description = one(copy.elements(), lambda e: e.has("tag-description"), "panel description")
        kind = one(copy.elements(), lambda e: e.has("panel-kind"), "panel kind")
        enter = one(copy.elements(), lambda e: e.tag == "a" and e.has("gallery-enter"), "panel link")
        stage = one(panel.elements(), lambda e: e.has("gallery-stage"), "image stage")
        art = one(stage.elements(), lambda e: e.tag == "img" and "data-mo1-original-src" in e.attrs, "original image")
        credit = one(panel.elements(), lambda e: e.tag == "details" and e.has("artwork-credit"), "artwork credit")
        summary = one(credit.elements(), lambda e: e.tag == "summary", "artwork summary")
        credit_children = Element("details", children=[e for e in credit.children if e is not summary])
        slides.append({
            "id": panel.attrs.get("id", ""),
            "label": panel.attrs.get("data-index-label", ""),
            "kind": plain(fragment(kind)),
            "title": plain(fragment(heading)),
            "description": fragment(description),
            "destination": {"href": link_url(enter.attrs.get("href") or ""), "label": plain(fragment(enter))},
            "image": {"source_url": media_url(art.attrs["data-mo1-original-src"]), "alt": art.attrs.get("alt", "")},
            "credit": {"summary": plain(fragment(summary)), "content": fragment(credit_children)},
        })
    identities = [s["id"] for s in slides]
    if not 1 <= len(slides) <= 32 or ARCHIVE_PANEL not in identities or len(set(identities)) != len(identities):
        raise ValueError("Homepage carousel is missing or incomplete")
    return slides


def mime_for(body):
    if body.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Carousel media is not a supported image")


def stable_content(manifest):
    return {k: v for k, v in manifest.items() if k not in {"content_sha256", "website_checked_at"}}


def verify_manifest(manifest):
    expected = {"schema_version", "source_url", "website_checked_at", "content_sha256", "assets", "slides"}
    if (not isinstance(manifest, dict) or set(manifest) != expected
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or manifest["source_url"] != HOME
            or not all(isinstance(manifest[key], list) for key in ("assets", "slides"))):
        raise ValueError("Invalid homepage carousel manifest")
    stamp = datetime.fromisoformat(manifest["website_checked_at"].replace("Z", "+00:00"))
    if stamp.utcoffset() is None or digest(stable_content(manifest)) != manifest["content_sha256"]:
        raise ValueError("Homepage carousel manifest fixity or date is invalid")
    claims = {}
    for asset in manifest["assets"]:
        name, checksum, mime = asset["path"], asset["sha256"], asset["mime_type"]
        if (not SHA.fullmatch(checksum) or mime not in MIMES or name != f"{MEDIA}/{checksum}.{MIMES[mime]}"
                or type(asset["bytes"]) is not int or not 0 < asset["bytes"] <= MAX_ASSET
                or any(type(asset[k]) is not int or not 0 < asset[k] <= 100_000 for k in ("width", "height"))
                or name in claims or media_url(asset["source_url"]) != asset["source_url"]):
            raise ValueError("Invalid homepage carousel asset claim")
        claims[name] = asset
    used, identities = set(), set()
    for slide in manifest["slides"]:
        id_, image, credit, destination = (slide[k] for k in ("id", "image", "credit", "destination"))
        if (not ID.fullmatch(id_) or id_ in identities or image["path"] not in claims
                or media_url(image["source_url"]) != image["source_url"]
                or not isinstance(image["alt"], str) or link_url(destination["href"]) != destination["href"]
                or not all(isinstance(value, str) and value.strip() for value in
                           (slide["label"], slide["kind"], slide["title"], credit["summary"], destination["label"]))):
            raise ValueError("Invalid homepage carousel panel")
        if not render_fragment(slide["description"]).strip() or not render_fragment(credit["content"]).strip():
            raise ValueError("Homepage carousel panel needs its source description and credit")
        used.add(image["path"])
        identities.add(id_)
    if (not 1 <= len(identities) <= 32 or ARCHIVE_PANEL not in identities or used != claims.keys()
            or sum(asset["bytes"] for asset in claims.values()) > MAX_TOTAL_ASSETS):
        raise ValueError("Homepage carousel manifest is incomplete")
    return claims


def capture(work, fetcher):
    report = json.loads((work / "report.json").read_text())
    if report.get("mode") != "apply" or not report.get("checked_at"):
        raise ValueError("A complete website reconciliation is required before carousel capture")
    slides = parse_homepage(fetcher.get(HOME, 2_000_000).decode("utf-8"))
    claims, files = {}, {}
    source_assets = {}
    with TemporaryDirectory() as directory:
        for slide in slides:
            url = slide["image"]["source_url"]
            if url in source_assets:
                slide["image"]["path"] = source_assets[url]
                continue
            data = fetcher.get(url, MAX_ASSET)
            mime, checksum = mime_for(data), digest(data)
            path = f"{MEDIA}/{checksum}.{MIMES[mime]}"
            measured = Path(directory) / Path(path).name
            measured.write_bytes(data)
            size = dimensions(measured)
            if not size:
                raise ValueError("Cannot verify homepage carousel image dimensions")
            source_assets[url] = slide["image"]["path"] = path
            claims.setdefault(path, {
                "path": path, "source_url": url, "mime_type": mime, "sha256": checksum,
                "bytes": len(data), "width": size[0], "height": size[1],
            })
            files[path] = data
            if sum(len(value) for value in files.values()) > MAX_TOTAL_ASSETS:
                raise ValueError("Homepage carousel images exceed the total limit")
        manifest = {"schema_version": 1, "source_url": HOME, "website_checked_at": report["checked_at"],
                    "slides": slides, "assets": list(claims.values())}
        manifest["content_sha256"] = digest(stable_content(manifest))
        verify_manifest(manifest)
        raw = encoded(manifest)
        if len(raw) > MAX_MANIFEST:
            raise ValueError("Homepage carousel manifest exceeds the size limit")
    public = work / "public"
    for path, content in files.items():
        atomic(public / path, content)
    atomic(public / MANIFEST, raw)
    return manifest


def load_manifest(path):
    if path.is_symlink() or path.stat().st_size > MAX_MANIFEST:
        raise ValueError("Homepage carousel manifest path or size is invalid")
    raw = path.read_bytes()
    manifest = json.loads(raw)
    return raw, manifest, verify_manifest(manifest)


def local_image(root, name, asset):
    path = root / name
    if path.resolve() != path or not path.is_file() or path.stat().st_size != asset["bytes"]:
        raise ValueError(f"Missing or invalid carousel image: {name}")
    body = path.read_bytes()
    if digest(body) != asset["sha256"] or mime_for(body) != asset["mime_type"]:
        raise ValueError(f"Carousel image failed fixity: {name}")
    if dimensions(path) != (asset["width"], asset["height"]):
        raise ValueError(f"Carousel image dimensions differ: {name}")
    return path


def render_page(manifest, claims, layout):
    e = lambda value: escape(value, quote=True)
    title = "Museum of One homepage carousel"
    description = "An archived view of the homepage panels, with artwork credits and source links."
    parts = [f'<div class="page-head"><div class="breadcrumb"><a href="website-records.html">Website captures</a>'
             f' / Homepage carousel</div><h1>{title}</h1><p>{description}</p><p><a href="{HOME}">Current Museum of One homepage ↗</a>'
             f' · <a href="metadata/{MANIFEST}">Capture metadata ↓</a></p></div>']
    parts.append('<nav class="homepage-capture-nav" aria-label="Captured homepage panels">'
                 + " · ".join(f'<a href="#{e(slide["id"])}">{e(slide["label"])}</a>' for slide in manifest["slides"])
                 + "</nav>")
    parts.append('<div class="homepage-capture-panels">')
    for slide in manifest["slides"]:
        image, credit, destination = (slide[k] for k in ("image", "credit", "destination"))
        asset = claims[image["path"]]
        parts.append(
            f'<article class="homepage-capture-panel" id="{e(slide["id"])}"><div>'
            f'<span class="eyebrow">{e(slide["kind"])}</span><h2>{e(slide["title"])}</h2>'
            f'<div>{render_fragment(slide["description"])}</div>'
            f'<a class="text-link" href="{e(destination["href"])}">{e(destination["label"])}</a></div>'
            f'<figure><img src="{e(image["path"])}" alt="{e(image["alt"])}" width="{asset["width"]}"'
            f' height="{asset["height"]}" loading="lazy" decoding="async">'
            f'<figcaption><strong>{e(credit["summary"])}</strong>{render_fragment(credit["content"])}</figcaption>'
            '</figure></article>'
        )
    html = layout(title, description, "".join(parts) + "</div>", PAGE)
    style = asset_url(ROOT, STYLESHEET)
    return html.replace("</head>", f'<link rel="stylesheet" href="{style}"></head>')


def build_carousel(work, out, write, layout):
    public = work / "public"
    entry = public / MANIFEST
    if not entry.is_file():
        (out / PAGE).unlink(missing_ok=True)
        (out / "metadata" / MANIFEST).unlink(missing_ok=True)
        if (out / MEDIA).exists():
            shutil.rmtree(out / MEDIA)
        return None
    raw, manifest, claims = load_manifest(entry)
    images = [local_image(public, name, asset) for name, asset in claims.items()]
    html = render_page(manifest, claims, layout)
    if (out / MEDIA).exists():
        shutil.rmtree(out / MEDIA)
    for path in images:
        target = out / path.relative_to(public)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    write(f"metadata/{MANIFEST}", raw.decode())
    write(PAGE, html)
    return manifest["content_sha256"]


if __name__ == "__main__":
    work = Path(os.environ.get("WEBSITE_SYNC_DIR") or ROOT / ".sync-work")
    result = capture(work, Fetcher())
    print(f'Captured {len(result["slides"])} homepage carousel panels and {len(result["assets"])} images', flush=True)
