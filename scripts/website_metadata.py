"""Source-declared descriptive fields, with explicit identifier evidence scope.
No date, subtitle, affiliation, review status or edition is inferred from prose.
"""

import json, re


def describe(source, language, summary, curated):
    if isinstance(curated, dict):
        curated = curated.get("records", [])
    declared = source["source_declared_metadata"]
    fields = {}
    for row in declared:
        fields.setdefault(row["name"].lower(), []).append(row["content"])

    def values(*names):
        result = []
        for name in names:
            for value in fields.get(name, []):
                if name.startswith("json-ld "):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                result.append(value)
        return result

    known = {r.get("doi"): str(r["id"]) for r in curated if r.get("doi")}
    concepts = {
        r.get("conceptdoi"): str(r["id"]) for r in curated if r.get("conceptdoi")
    }
    identifiers = []
    for name in (
        "citation_doi",
        "dc.identifier",
        "citation_isbn",
        "citation_issn",
        "citation_author_orcid",
    ):
        for raw in fields.get(name, []):
            value = raw.strip()
            kind = {
                "citation_doi": "DOI",
                "citation_isbn": "ISBN",
                "citation_issn": "ISSN",
                "citation_author_orcid": "ORCID",
            }.get(name, "Source identifier")
            doi = re.sub(
                r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I
            )
            evidence = "source_declared_not_independently_verified"
            scope = "Declaration in website metadata; not automatically an identifier of this web capture"
            if doi in known:
                kind = "DOI"
                value = doi
                evidence = "agrees_with_preserved_curated_deposit_metadata"
                scope = (
                    "Selected deposited edition "
                    + known[doi]
                    + "; web page remains distinct"
                )
            elif doi in concepts:
                kind = "DOI"
                value = doi
                evidence = "agrees_with_preserved_curated_deposit_metadata"
                scope = "Repository version family; no exact edition inference"
            identifiers.append(
                {
                    "type": kind,
                    "value": value,
                    "evidence": evidence,
                    "scope": scope,
                    "source_field": name,
                    "source_url": source["url"],
                }
            )
    result = {
        "exact_title": source["title"],
        "resource_type": "WebPage",
        "website_content_type": source["kind"],
        "description": summary,
        "description_source": "Authored custom excerpt"
        if source.get("custom_excerpt")
        else "Source SEO description"
        if source.get("meta_description")
        else "Ghost-derived public excerpt",
        "credited_creators": source["creators"],
        "subjects_from_public_tags": source["subjects"],
        "source_declared_identifiers": identifiers,
        "source_declared_publishers": values(
            "dc.publisher", "citation_publisher", "json-ld publisher"
        ),
        "source_declared_rights": values("dc.rights", "json-ld copyrightnotice"),
        "source_declared_licences": values(
            "dc.license", "dc.rights.license", "json-ld license"
        ),
        "source_declared_version_statements": values(
            "citation_version", "dc.hasversion", "json-ld version"
        ),
        "source_declared_contributors": values("json-ld contributor"),
        "source_declared_programme_or_container_relations": values(
            "dc.relation", "json-ld ispartof"
        ),
    }
    if language:
        result["source_declared_language"] = language
    # A separately supplied subtitle is retained; colons in titles are not split.
    subtitle = values("citation_subtitle", "dc.subtitle")
    if subtitle:
        result["source_declared_subtitles"] = subtitle
    return result


def capture_schema(record, assets, original_html, url, origin):
    """Describe the archive copy, its declared source, and available file bytes.

    Authorship belongs to the source page. Embedded file authorship, licences,
    media duration and creation dates are not inferred from the surrounding page.
    """
    source = record["source"]
    based_on = {
        "@type": "WebPage",
        "@id": source["url"],
        "url": source["url"],
        "name": source["title"],
        "datePublished": source["published_at"],
    }
    if source.get("updated_at"):
        based_on["dateModified"] = source["updated_at"]
    document_language = (record.get("document_language") or {}).get("language")
    if document_language:
        based_on["inLanguage"] = document_language
    if record.get("language"):
        based_on["mainEntity"] = {
            "@type": "CreativeWork",
            "name": source["title"],
            "inLanguage": record["language"],
        }
    if source["creators"]:
        based_on["author"] = [
            {
                "name": author["name"],
                **({"url": author["url"]} if author.get("url") else {}),
            }
            for author in source["creators"]
        ]
    based_on["archivedAt"] = url
    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": url + "#record",
        "url": url,
        "name": source["title"],
        "description": record["summary"],
        "inLanguage": "en",
        "dateCreated": record["first_captured_at"],
        "dateModified": record["capture"]["captured_at"],
        "isAccessibleForFree": True,
        "isBasedOn": based_on,
        "isPartOf": {"@id": origin + "/#website"},
    }
    graph["encoding"] = {
        "@type": "MediaObject",
        "name": "Original published content HTML (inert text download)",
        "contentUrl": origin + "/" + original_html["path"],
        "encodingFormat": "text/plain",
        "contentSize": str(original_html["bytes"]) + " bytes",
        "sha256": original_html["sha256"],
        "description": "Original published content HTML served as inert text; not an executable website environment.",
    }
    media = []
    for asset in assets:
        if (
            not asset.get("archive_path")
            or not asset.get("sha256")
            or asset.get("availability") != "available"
        ):
            continue
        mime = asset.get("mime_type") or "application/octet-stream"
        kind = next(
            (
                name
                for prefix, name in [
                    ("image/", "ImageObject"),
                    ("audio/", "AudioObject"),
                    ("video/", "VideoObject"),
                ]
                if mime.startswith(prefix)
            ),
            "MediaObject",
        )
        item = {
            "@type": kind,
            "name": asset.get("label") or asset["url"].rsplit("/", 1)[-1],
            "contentUrl": origin + "/" + asset["archive_path"],
            "encodingFormat": mime,
            "contentSize": str(asset["bytes"]) + " bytes",
            "sha256": asset["sha256"],
            "isBasedOn": asset["url"],
            "isPartOf": {"@id": url + "#record"},
            "description": asset["reason"],
        }
        if asset.get("pixel_dimensions"):
            for dimension in ("width", "height"):
                item[dimension] = {
                    "@type": "QuantitativeValue",
                    "value": asset["pixel_dimensions"][dimension],
                    "unitText": "pixels",
                }
        media.append(item)
    if media:
        graph["hasPart"] = media
    return graph
