"""Render source web records separately from the curated publication catalogue."""

from datetime import datetime, timezone
from pathlib import Path
from archive_design import asset_url
from html import escape, unescape
import json, shutil, re
from urllib.parse import urlsplit
from website_sync import digest
from website_metadata import capture_schema
from publication_arrangement import ENCOUNTER_LINKS, RAI_SERIES, canonical_key, mirror_quality
from image_dimensions import dimensions
from publication_arrangement import (BOOKS, ESSAYS, THEORY, METHODOLOGY,
                                     collection_anchor, load_publication_captures, publication_grid, publication_inventory)


def access_asset(asset, file, out, origin, catalogue):
    """Keep original fixity in recovery; reconcile obsolete links in access JSON."""
    a = dict(asset)
    original = file.read_bytes()
    if digest(original) != a["sha256"]:
        raise ValueError("Capture asset checksum mismatch")
    retired = "museumofone." + "omeka.net"
    if (
        file.suffix.lower() not in (".json", ".txt", ".csv")
        or retired not in original.decode("utf-8", errors="replace").lower()
    ):
        target = out / a["archive_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        return a, 0
    changes = []

    def walk(value, context=None):
        if isinstance(value, dict):
            doi = value.get("DOI") or value.get("doi")
            title = value.get("title")
            matches = [
                r
                for r in catalogue
                if doi and r.get("doi") == doi and title == r.get("title")
            ]
            if len(matches) == 1:
                context = matches[0]["id"]
            return {k: walk(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, context) for v in value]
        if isinstance(value, str) and retired in value.lower():
            u = urlsplit(value)
            if u.hostname != retired:
                raise ValueError("Unresolved retired reference in uploaded text")
            if u.path in ("", "/") and not u.query and not u.fragment:
                target = origin + "/"
            elif context:
                target = origin + "/items/" + str(context) + ".html"
            else:
                raise ValueError("No evidence-backed item destination")
            changes.append(target)
            return target
        return value

    try:
        if file.suffix.lower() != ".json":
            raise ValueError("Not structured citation JSON")
        updated = walk(json.loads(original))
        body = (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode()
        if not changes or retired in body.decode().lower():
            raise ValueError("Unresolved retired reference")
    except (ValueError, TypeError):
        a.pop("archive_path", None)
        a.update(
            storage="encrypted_recovery_only",
            availability="withheld",
            reason="Original bytes retained in encrypted recovery. Public file withheld because obsolete archive references have no verified replacement.",
        )
        return a, 0
    source_hash = a["sha256"]
    source_bytes = a["bytes"]
    h = digest(body)
    path = "assets/website-captures/" + h + ".json"
    target = out / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    a.update(
        storage="local_access_derivative",
        archive_path=path,
        sha256=h,
        bytes=len(body),
        source_sha256=source_hash,
        source_bytes=source_bytes,
        access_derivative=True,
        reason=f"Access derivative: {len(changes)} obsolete archive links replaced using the citation’s exact DOI and title match to a curated item. Original uploaded bytes remain unchanged in encrypted recovery; source and access-copy checksums are recorded separately.",
    )
    return a, len(changes)


def capture_publication_date(capture):
    try:
        date = datetime.fromisoformat(capture["original_published_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)
    return date if date.tzinfo else date.replace(tzinfo=timezone.utc)


def build_website_pages(work, out, write, layout, origin, *, methodology=None, methodology_desc=None, captures=None, inventory=None):
    work = Path(work)
    out = Path(out)
    # A fresh whitelist is rebuilt each time, never leave a withdrawn readable file.
    for p in [out / "website", out / "assets/website-captures"]:
        if p.exists():
            shutil.rmtree(p)
    current = load_publication_captures(work) if captures is None else captures
    source_map = {
        p["source"]["url"]: origin + "/website/" + p["archive_id"] + ".html"
        for p in current
    }
    fragment_map = {
        p["source"]["url"]: set(re.findall(r'id="([^"]+)"', p["readable_html"]))
        for p in current
    }
    report = (
        json.loads((work / "report.json").read_text())
        if (work / "report.json").exists()
        else {"mode": "not_reconciled", "eligible_records": 0}
    )
    catalogue = json.loads(
        (Path(__file__).resolve().parents[1] / "data/catalogue.json").read_text()
    )
    e = lambda x: escape(str(x or ""), quote=True)
    paths = []
    metadata = []
    derivatives = set()
    link_changes = 0
    if isinstance(catalogue, dict):
        catalogue = catalogue["records"]
    inventory = publication_inventory(current, catalogue) if inventory is None else inventory
    by_id = {row["id"]: row for row in inventory}
    groups = (BOOKS, ESSAYS, THEORY, METHODOLOGY)
    arranged = {group: [row for row in inventory if row["collection"] == group] for group in groups}
    references = [row for row in inventory if row["collection"] is None]
    assert sum(map(len, arranged.values())) + len(references) == len(current)
    e = lambda x: escape(str(x or ""), quote=True)
    intro = '<div class="page-head"><div class="eyebrow">Website captures</div><h1>Published website records</h1><p>Browse public Museum of One writing, research and tools by collection. Each card links to its preserved website capture and to a deposited edition where the source match is established.</p></div>'
    intro += (
        f'<p>{len(current)} public captures · Last reconciliation {e(report.get("checked_at", "Not yet run"))}</p>'
        '<p><a href="metadata/website-sync.json">Reconciliation report</a> · '
        '<a href="metadata/publication-arrangement.json">Classification inventory</a></p>'
        '<nav aria-label="Website publication collections">'
        + " · ".join(f'<a href="#{collection_anchor(group)}">{e(group)}</a>' for group in groups)
        + ' · <a href="#website-reference">Website reference pages</a></nav>'
    )
    captures_by_slug = {canonical_key(row["source_url"])[1].rsplit("/", 1)[-1]: row for row in inventory}
    for group, rows in arranged.items():
        anchor = collection_anchor(group)
        intro += f'<section class="section" id="{anchor}"><div class="section-head"><h2>{e(group)}</h2><span>{len(rows)} website records</span></div>'
        intro += publication_grid(rows) + "</section>"
    intro += '<section class="section" id="website-reference"><h2>Website reference pages</h2><p>Programme pages, directories and institutional information.</p>'
    intro += publication_grid(references) + "</section>"

    if methodology is not None:
        methods = arranged[METHODOLOGY]
        rai = [row for slug, row in captures_by_slug.items() if slug in RAI_SERIES and not row["edition_path"]]
        papers = [row for row in methods if row not in rai and not row["edition_path"] and row["role"] != "Research tool or guide"]
        tools = [row for row in methods if row not in rai and row["role"] == "Research tool or guide"]
        sections = '<section class="section"><h2>Website publications and research demonstrations</h2>' + publication_grid(papers) + "</section>"
        sections += '<section class="section"><h2>Research tools and guides</h2>' + publication_grid(tools) + "</section>"
        encounter = captures_by_slug.get("research-encounter-differential")
        if encounter:
            sections += '<p><a href="' + e(encounter["capture_path"]) + '">Encounter Differential programme ↗</a></p>'
        methodology = methodology.replace('<div data-methodology-rai></div>', publication_grid(rai) if rai else '')
        write("methodology.html", layout("Methodology", methodology_desc,
              methodology.replace('<div data-methodology-website></div>', sections),
              "methodology.html", active="methodology"))
        paths.append("methodology.html")

    write("metadata/publication-arrangement.json", json.dumps({
        "website_capture_count": len(inventory),
        "deposited_edition_count": len(catalogue),
        "collections": {group: len(rows) for group, rows in arranged.items()},
        "reference_count": len(references),
        "records": inventory,
    }, ensure_ascii=False, indent=2))
    for p in current:
        r = p["source"]
        rid = p["archive_id"]
        arrangement = by_id[rid]
        page = "website/" + rid + ".html"
        url = origin + "/" + page
        assets = []
        replacements = {}
        for a in p["attachments"]:
            a = dict(a)
            path = a.get("archive_path")
            if a["storage"] == "local_archival_file":
                file = work / "public" / path
                if not file.is_file():
                    raise ValueError("Capture asset missing")
                a, count = access_asset(a, file, out, origin, catalogue)
                path = a.get("archive_path")
                if a.get("access_derivative") and path not in derivatives:
                    derivatives.add(path)
                    link_changes += count
            if path:
                if a.get("mime_type", "").startswith("image/"):
                    pixels = dimensions(str(out / path))
                    if pixels:
                        a["pixel_dimensions"] = {
                            "width": pixels[0],
                            "height": pixels[1],
                            "basis": "oriented stored image header",
                        }
                elif a["storage"] == "existing_verified_archive_file" and path.endswith(
                    ".pdf"
                ):
                    a["mime_type"] = "application/pdf"
                replacements[a["url"]] = origin + "/" + path
            assets.append(a)
        body = p["readable_html"]
        for source, target in {**source_map, **replacements}.items():
            body = body.replace('href="' + e(source) + '"', 'href="' + e(target) + '"')
        for source, target in source_map.items():
            body = re.sub(
                'href="' + re.escape(e(source)) + '#([^"]+)"',
                lambda m: (
                    'href="' + e(target) + "#" + m[1] + '"'
                    if unescape(m[1]) in fragment_map[source]
                    else m[0]
                ),
                body,
            )
        raw = (r["html"] or "").encode()
        capture_files = [
            {
                "path": page,
                "role": "Readable web capture",
            },
            {
                "path": "website/" + rid + ".source.html.txt",
                "role": "Original published content HTML, inert source download",
                "bytes": len(raw),
                "sha256": digest(raw),
            },
        ]
        rawpath = out / capture_files[1]["path"]
        rawpath.parent.mkdir(exist_ok=True, parents=True)
        rawpath.write_bytes(raw)
        # Self-canonical wrapper is the catalogue record; inert text download avoids
        # executing authored app code or third-party widgets in the archive origin.
        fields = [
            ("Source publication", p["original_published_at"]),
            ("Current source publication field", r["published_at"]),
            ("Source modified", r["updated_at"]),
            ("First archive capture", p["first_captured_at"]),
            ("Selected capture", p["capture"]["captured_at"]),
            ("Revision count", p["revision_count"]),
            (
                "Work language supplied in publication metadata",
                " · ".join(p["language"])
                if isinstance(p.get("language"), list)
                else p.get("language") or "Not explicitly supplied",
            ),
            (
                "Source role",
                r["kind"] + " on the website; no book/edition identity inferred",
            ),
        ]
        fields.extend([
            ("Source HTML document language", arrangement["source_document_language"] or "Unverified"),
            ("Subjects from public website tags", " · ".join(arrangement["source_subjects"]) or "None supplied"),
            ("Subjects added by the archive", " · ".join(arrangement["editorial_subjects"]) or "None added"),
        ])
        if arrangement["edition_path"]:
            fields.append(("Relationship to deposited edition", {
                "exact_edition": "Source identifies the deposited edition",
                "version_family": "Source identifies the version family",
                "work": "Source describes the work",
            }[arrangement["edition_relationship"]]))
        content = (
            '<div class="website-record"><div class="page-head"><div class="eyebrow">Website capture / '
            + e(rid)
            + "</div><h1>"
            + e(r["title"])
            + "</h1><p>"
            + e(p["summary"])
            + '</p><p><a href="'
            + e(r["url"])
            + '">Canonical website source ↗</a> · <a href="../website-records.html">All website captures</a> · <a href="'
            + rid
            + '.source.html.txt" download>Original content HTML ↓</a></p></div><div class="reading"><dl class="metadata">'
        )
        content += (
            "".join(
                "<div><dt>" + e(k) + "</dt><dd>" + e(v) + "</dd></div>"
                for k, v in fields
            )
            + "</dl>"
        )
        content += (
            "<h2>Credited website creators</h2><p>"
            + e(
                "; ".join(x["name"] + " (" + x["role"] + ")" for x in r["creators"])
                or "Not supplied"
            )
            + "</p>"
        )
        content += "<h2>Rights and access</h2><p>This is a stored copy of a public website publication, captured under the website owner’s archive instruction. Original source rights, image credits, citations and third-party exclusions remain applicable. Public access does not grant a new licence. External embeds and unpreserved files are explicitly identified below. Interactive source is retained as an inert HTML download; a live software environment is not guaranteed.</p>"
        if r.get("feature_image_caption"):
            from website_sync import Readable

            content += "<h2>Source feature-image credit</h2>" + "".join(
                Readable(r["feature_image_caption"]).parts
            )
        content += (
            '<h2>Published content</h2><section class="website-captured-content">'
            + body
            + "</section>"
        )
        content += '<h2>Files, images and media</h2><ul class="source-list">'
        for a in assets:
            target = (
                origin + "/" + a["archive_path"] if a.get("archive_path") else a["url"]
            )
            label = a.get("label") or a["url"].split("/")[-1]
            content += (
                '<li><a href="'
                + e(target)
                + '">'
                + e(label)
                + "</a><small>"
                + e(a["storage"].replace("_", " "))
                + " · "
                + e(a["availability"])
                + "</small><small>"
                + e(a["reason"])
                + "</small>"
            )
            if a.get("sha256"):
                content += (
                    "<small>"
                    + e(a.get("bytes"))
                    + " bytes · SHA-256 "
                    + e(a["sha256"])
                    + "</small>"
                )
            if a.get("source_sha256"):
                content += (
                    "<small>Original uploaded source: "
                    + e(a["source_bytes"])
                    + " bytes · SHA-256 "
                    + e(a["source_sha256"])
                    + " · encrypted recovery only</small>"
                )
            if a.get("archive_path") and (a.get("mime_type") or "").startswith(
                "image/"
            ):
                content += (
                    '<img loading="lazy" style="max-width:100%;height:auto" src="'
                    + e(target)
                    + '" alt="'
                    + e(label)
                    + '">'
                )
            if a.get("archive_path") and (a.get("mime_type") or "").startswith(
                ("audio/", "video/")
            ):
                tag = "audio" if a["mime_type"].startswith("audio/") else "video"
                content += (
                    "<"
                    + tag
                    + ' controls preload="none" src="'
                    + e(target)
                    + '">'
                    + e(label)
                    + "</"
                    + tag
                    + ">"
                )
            content += "</li>"
        content += '</ul><h2>Source-declared metadata</h2><p>Transcribed declarations retain their source scope. Identifiers are not promoted to independently verified edition assignments.</p><dl class="metadata">'
        content += (
            "".join(
                "<div><dt>"
                + e(v["name"])
                + "</dt><dd>"
                + e(v["content"])
                + "</dd></div>"
                for v in r["source_declared_metadata"]
            )
            + "</dl>"
        )
        content += (
            "<p>Source content SHA-256: <code>"
            + e(p["capture"]["content_hash"])
            + "</code></p>"
        )
        if p["validation_issues"]:
            content += (
                "<h2>Fields requiring qualification</h2><ul>"
                + "".join("<li>" + e(v) + "</li>" for v in p["validation_issues"])
                + "</ul>"
            )
        entities = json.loads((Path(__file__).resolve().parents[1] / 'data/entities.json').read_text())
        linked = [(entity, link) for entity in entities for link in entity.get('web_links', []) if link['url'] == r['url']]
        if linked:
            content += '<section class="item-section"><h2>People in this exchange</h2><ul class="source-list">'
            for entity, link in linked:
                content += ('<li><a href="../entities/' + e(entity['id']) + '.html">' + e(entity['label']) + '</a><p>' + e(link['note']) + '</p><small>' + e(link['relation']) + ' · ' + e(link['status']) + '</small></li>')
            content += '</ul></section>'
        content += "</div></div>"
        schema = capture_schema(p, assets, capture_files[1], url, origin)
        if arrangement["edition_path"]:
            content = content.replace("</h1>", '</h1><p><a href="../' + e(arrangement["edition_path"]) + '">View the linked deposited edition ↗</a></p>', 1)
        slug = canonical_key(r["url"])[1].rsplit("/", 1)[-1]
        if slug in ENCOUNTER_LINKS:
            target_slug, label = ENCOUNTER_LINKS[slug]
            target = captures_by_slug.get(target_slug)
            if target:
                content = content.replace("</h1>", '</h1><p><a href="../' + e(target["capture_path"]) + '">' + e(label) + ' ↗</a></p>', 1)
        html = layout(
            r["title"] + " — Website capture (" + (r.get("published_at") or "undated")[:10] + ")",
            p["summary"] or "Stored public website record and its source metadata.",
            content,
            page,
            base="../",
            schema=schema,
        )
        style = asset_url(Path(__file__).resolve().parents[1], "website-captures.css")
        html = html.replace(
            "</head>",
            f'<link rel="stylesheet" href="../{style}"></head>',
        )
        write(page, html)
        paths.append(page)
        # Hash final generated presentation and original inert source separately.
        capture_files[0].update(
            bytes=(out / page).stat().st_size, sha256=digest((out / page).read_bytes())
        )
        metadata.append(
            {k: v for k, v in p.items() if k not in ("readable_html", "text")}
            | {
                "source": {k: v for k, v in r.items() if k != "html"},
                "attachments": assets,
                "files": capture_files,
                "arrangement": arrangement,
                "url": url,
            }
        )
    write(
        "website-records.html",
        layout(
            "Website captures",
            "Automatically captured public Museum of One website records and uploaded files.",
            intro,
            "website-records.html",
        ),
    )
    paths.append("website-records.html")
    report.update(
        public_access_derivative_files=len(derivatives),
        retired_link_replacements=link_changes,
        website_mirror_quality=mirror_quality(inventory),
    )
    write(
        "metadata/website-captures.json",
        json.dumps(metadata, ensure_ascii=False, indent=2),
    )
    write(
        "metadata/website-sync.json", json.dumps(report, ensure_ascii=False, indent=2)
    )
    return paths
