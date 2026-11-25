"""Editorial browsing routes for public website publications and deposited editions."""

from html import escape
from dialogue_guide import guided_dialogues
from identities import institutional_scope
import json
from urllib.parse import quote, urlsplit

METHODOLOGY = "Methodology"
ESSAYS = "Essays & research"
THEORY = "Theory & treatises"
BOOKS = "Books & volumes"

METHOD_WORKS = frozenset({
    "post-interpretive-method-how-to-practice-restraint-in-front-of-a-work-of-art",
    "witnessing-vs-interpreting-a-post-interpretive-comparative-exercise",
    "principles-of-post-interpretive-criticism-a-study-guide",
    "measuring-proximity-a-post-interpretive-diagnostic-experiment-in-art-criticism-post-hermeneutic-phenomenology",
    "a-quantitative-analysis-of-critical-posture-in-art-writing-1980-2025-dataset-20-critical-texts-1980-2025",
    "extending-post-interpretive-criticism-additional-diagnostic-indices-for-enhanced-phenomenological-fidelity-in-art-criticism",
    "quantifying-critical-posture-a-diagnostic-analysis-of-art-writing-1980-2025-formalizing-post-hermeneutic-phenomenology",
    "diagnostics-without-possession-an-operational-manual-for-post-interpretive-criticism-operational-reference-for-inter-rater-reliability",
    "phenomenological-indices-analysis",
    "from-husserls-mathematics-to-dufrennes-aesthetics-toward-a-formalization-of-phenomenological-aesthetics",
    "rai-identity-chronology-korean-experimental-art",
    "rai-documentary-supplement",
    "rai-extended-case-studies",
    "when-documentation-becomes-the-work",
    "titles-dates-and-reconstructed-works",
})

METHOD_RESOURCES = frozenset({
    "relational-archival-investigation", "diagnostic-reading",
    "analytical-diagnostic-tools", "research-methods-instruments",
    "linguistic-diagnostics-analysis", "the-adjacency-contamination-mapper",
    "encounter-differential", "spatiotemporal-comparison", "theory-prism",
    "experimental-curatorial-space-phenomenological-aesthetics-experience-environment-simulator",
    "post-interpretive-curatorial-museum-research",
})

THEORY_WORKS = frozenset({
    "the-theory-of-misplacement", "theory-of-aesthetic-displacement",
    "stillmark-theory-a-treatise-on-presence-vanishing-and-the-discipline-of-the-fleeting-2",
    "art-as-truth-a-treatise",
    "finished-the-viewer-as-evidence-a-treatise-on-witness-residue-and-critical-consequence",
    "finished-message-transfer-theory-mtt-a-treatise-on-the-reversal-of-meaning-the-displacement-of-intent-and-the-object-as-conduit",
    "absential-aesthetics-theory-on-ghosts-absence-and-the-afterlife-of-art",
    "hauntmark-theory-the-lingering-weight-of-words",
    "aesthetic-recursion-theory-recursion-as-residue",
    "formal-defence-of-post-interpretive-criticism", "doctrine",
    "doctrine-reframing-language-and-witnessing",
    "post-interpretive-criticism-a-philosophical-departure-from-post-criticism",
    "post-interpretive-criticism-a-philosophical-departure-from-post-criticism-2",
    "the-living-lexicon", "the-living-lexicon-post-interpretive-criticism-first-edition",
})

BOOK_PAGES = frozenset({
    "post-interpretive-criticism-volume-i-foundational-essays",
    "post-interpretive-criticism-volume-ii-essays-from-the-field",
})

RAI_SERIES = frozenset({
    "relational-archival-investigation", "rai-identity-chronology-korean-experimental-art",
    "rai-documentary-supplement", "rai-extended-case-studies",
})
ENCOUNTER_LINKS = {
    "research-encounter-differential": ("encounter-differential", "Open the archived Encounter Differential tool"),
    "encounter-differential": ("research-encounter-differential", "Read the archived Encounter Differential programme"),
}

TITLE_ALIASES = {
    "theory-of-aesthetic-displacement": ["Theory of Displacement"],
    "stillmark-theory-a-treatise-on-presence-vanishing-and-the-discipline-of-the-fleeting-2": ["Stillmark Theory", "Still Make Theory"],
    "finished-message-transfer-theory-mtt-a-treatise-on-the-reversal-of-meaning-the-displacement-of-intent-and-the-object-as-conduit": ["Message Transfer Theory", "MTT"],
    "relational-archival-investigation": ["RAI", "Relational Archival Investigation"],
    "rai-identity-chronology-korean-experimental-art": ["RAI", "RAI working paper"],
    "rai-documentary-supplement": ["RAI Supplement 1"],
    "rai-extended-case-studies": ["RAI Supplement 2"],
    "extending-post-interpretive-criticism-additional-diagnostic-indices-for-enhanced-phenomenological-fidelity-in-art-criticism": ["Additional Diagnostic Indices", "Indices paper"],
    "encounter-differential": ["Encounter Differential Tool"],
    "post-interpretive-criticism-a-philosophical-departure-from-post-criticism": ["Post-Interpretive Criticism", "PIC"],
}

ESSAY_PAGES = frozenset({"dong-yeon-koh", "lu-peng", "tomoki-akimaru"})


# Editorial access terms supplement absent Ghost tags.
EDITORIAL_SUBJECTS = {
    "research-methods-instruments": ["Research methodology", "Diagnostic instruments"],
    "post-interpretive-curatorial-museum-research": ["Curatorial research", "Museum studies", "Post-Interpretive Criticism"],
    "post-interpretive-criticism-volume-ii-essays-from-the-field": ["Art criticism", "Post-Interpretive Criticism"],
    "post-interpretive-criticism-volume-i-foundational-essays": ["Aesthetics", "Post-Interpretive Criticism"],
    "tomoki-akimaru": ["Post-Interpretive Criticism", "Research dialogue"],
    "dong-yeon-koh": ["Korean art history", "Research dialogue"],
    "lu-peng": ["Chinese art historiography", "Post-Interpretive Criticism", "Research dialogue"],
    "phenomenological-indices-analysis": ["Phenomenology", "Diagnostic indices"],
    "linguistic-diagnostics-analysis": ["Critical language", "Diagnostic instruments"],
    "quantifying-critical-posture-a-diagnostic-analysis-of-art-writing-1980-2025-formalizing-post-hermeneutic-phenomenology": ["Art criticism", "Critical posture", "Diagnostic indices"],
    "experimental-curatorial-space-phenomenological-aesthetics-experience-environment-simulator": ["Phenomenological aesthetics", "Curatorial research"],
    "spatiotemporal-comparison": ["Comparative analysis", "Space and time"],
    "theory-prism": ["Critical theory", "Diagnostic instruments"],
    "encounter-differential": ["Attention", "Encounter Differential", "Diagnostic instruments"],
    "the-adjacency-contamination-mapper": ["Structural relationships", "Diagnostic instruments"],
    "analytical-diagnostic-tools": ["Diagnostic instruments", "Research methodology"],
    "diagnostic-reading": ["Diagnostic reading", "Research methodology"],
    "the-living-lexicon": ["Critical vocabulary", "Post-Interpretive Criticism"],
}

PUBLICATION_DOI_SCOPE_LABELS = {
    "version_family": "Related publication’s version-family DOI",
    "deposited_version": "Related publication’s deposited version DOI",
}


# Original citation_doi meta tags, checked against their DataCite registrations.
# These search associations leave the web captures' identities and source fields intact.
REVIEWED_PUBLICATION_DOIS = {
    "https://www.museumofone.art/"
    "nomadic-aesthetics-travelling-installations-as-moral-geography/":
        ("10.5281/zenodo.17478280", "version_family", "2026-11-25"),
    "https://www.museumofone.art/"
    "a-museum-of-breath-designing-spaces-for-attention-not-spectacle/":
        ("10.5281/zenodo.18349238", "version_family", "2026-11-25"),
    "https://www.museumofone.art/formal-defence-of-post-interpretive-criticism/":
        ("10.5281/zenodo.16934437", "deposited_version", "2026-11-25"),
    "https://www.museumofone.art/duchamp/":
        ("10.5281/zenodo.17056223", "deposited_version", "2026-11-25"),
}


def canonical_key(url):
    parts = urlsplit(url)
    return parts.hostname.removeprefix("www."), parts.path.rstrip("/")


def collection_anchor(group):
    return {
        BOOKS: "books-and-volumes",
        ESSAYS: "essays-and-research",
        THEORY: "theory-and-treatises",
        METHODOLOGY: "methodology",
    }[group]


def collection_link(group):
    if group == METHODOLOGY:
        return "methodology.html"
    return "catalogue.html?collection=" + quote(group)


def classify_capture(source, deposited, *, dialogue=False):
    """Return an editorial route and display role for each captured public record."""
    key = canonical_key(source["url"])
    slug = key[1].rsplit("/", 1)[-1]
    if key in deposited:
        return deposited[key]["collection"], "Website version"
    if slug in METHOD_RESOURCES:
        return METHODOLOGY, "Research tool or guide"
    if slug in METHOD_WORKS or (source["kind"] == "post" and METHODOLOGY in source.get("subjects", [])):
        return METHODOLOGY, "Website publication"
    if slug in THEORY_WORKS:
        return THEORY, "Website publication"
    if slug in BOOK_PAGES:
        return BOOKS, "Website description"
    declared = {tag.strip().casefold() for tag in source.get("subjects", [])}
    for group in (METHODOLOGY, BOOKS, THEORY, ESSAYS):
        if group.casefold() in declared:
            return group, "Website publication"
    if source["kind"] == "post" or slug in ESSAY_PAGES or dialogue:
        return ESSAYS, "Website publication"
    return None, "Website reference"


def load_publication_captures(work):
    path = work / "public/current.json"
    return json.loads(path.read_text()) if path.is_file() else []


def publication_inventory(captures, editions):
    deposited = {canonical_key(r["institutional_url"]): r for r in editions if r.get("institutional_url")}
    dialogue_ids = {capture["archive_id"] for _, capture in guided_dialogues(captures)}
    rows = []
    for capture in captures:
        source = capture["source"]
        dialogue = capture["archive_id"] in dialogue_ids
        group, role = classify_capture(source, deposited, dialogue=dialogue)
        edition = deposited.get(canonical_key(source["url"]))
        slug = canonical_key(source["url"])[1].rsplit("/", 1)[-1]
        editorial_subjects = []
        if not source.get("subjects") and group:
            editorial_subjects = list(EDITORIAL_SUBJECTS.get(slug, ()))
            if edition and not editorial_subjects:
                editorial_subjects = edition.get("subjects", [])
            if dialogue and not editorial_subjects:
                editorial_subjects = ["Research dialogue"]
        document_language = capture.get("document_language") or {}
        row = {
            "id": capture["archive_id"],
            "title": source["title"],
            "aliases": TITLE_ALIASES.get(slug, []),
            "collection": group,
            "role": role,
            "date": capture["original_published_at"],
            "summary": capture["summary"],
            "subjects": source.get("subjects", []) or editorial_subjects,
            "source_subjects": source.get("subjects", []),
            "editorial_subjects": editorial_subjects,
            "subject_basis": ("Public Ghost tags" if source.get("subjects") else
                              ("Linked deposited edition catalogue subjects" if edition else "Editorial access terms") if editorial_subjects else None),
            "source_declared_language": capture.get("language"),
            "source_document_language": document_language.get("language"),
            "document_language_checked": document_language.get("checked_at"),
            "source_publication_date": capture["original_published_at"],
            "current_source_publication_date": source["published_at"],
            "source_modified": source["updated_at"],
            "first_captured_at": capture["first_captured_at"],
            "selected_captured_at": capture["capture"]["captured_at"],
            "edition_relationship": (edition.get("institutional_match_scope") or institutional_scope(edition)) if edition else None,
            "creators": [creator["name"] for creator in source.get("creators", [])],
            "source_url": source["url"],
            "capture_path": f'website/{capture["archive_id"]}.html',
            "edition_path": f'items/{edition["id"]}.html' if edition else None,
        }
        if source["url"] in REVIEWED_PUBLICATION_DOIS:
            doi, scope, reviewed = REVIEWED_PUBLICATION_DOIS[source["url"]]
            row["related_publication_doi"] = {
                "doi": doi, "scope": scope, "scope_label": PUBLICATION_DOI_SCOPE_LABELS[scope],
                "reviewed": reviewed, "source_url": source["url"], "source_field": "citation_doi",
                "registry_url": "https://api.datacite.org/dois/" + doi,
            }
        rows.append(row)
    return sorted(rows, key=lambda row: row["date"] or "", reverse=True)


def mirror_quality(inventory):
    from datetime import datetime

    def valid(value):
        try:
            return bool(datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo)
        except (ValueError, AttributeError):
            return False

    date_issues = []
    relationship_issues = []
    for row in inventory:
        dates = [row[key] for key in ("source_publication_date", "current_source_publication_date",
                                    "source_modified", "first_captured_at", "selected_captured_at")]
        if not all(map(valid, dates)):
            date_issues.append(row["id"])
        elif datetime.fromisoformat(dates[3]) > datetime.fromisoformat(dates[4]):
            date_issues.append(row["id"])
        if row["edition_path"] and row["edition_relationship"] not in {"exact_edition", "version_family", "work"}:
            relationship_issues.append(row["id"])
    classified = [row for row in inventory if row["collection"]]
    return {
        "records_checked": len(inventory),
        "classified_website_records": len(classified),
        "source_declared_work_languages": sum(bool(row["source_declared_language"]) for row in inventory),
        "source_declared_document_languages": sum(bool(row["source_document_language"]) for row in inventory),
        "language_unresolved": [row["id"] for row in inventory if not (row["source_declared_language"] or row["source_document_language"])],
        "classified_without_subjects": [row["id"] for row in classified if not row["subjects"]],
        "classified_with_editorial_subjects": sum(bool(row["editorial_subjects"]) for row in classified),
        "date_issues": date_issues,
        "edition_relationship_issues": relationship_issues,
        "edition_relationship_counts": {scope: sum(row["edition_relationship"] == scope for row in inventory)
                                        for scope in ("exact_edition", "version_family", "work")},
    }


def publication_card(row, *, catalogue=False):
    attrs = ""
    css = "route-card publication-card"
    if catalogue:
        css += " catalogue-website-card"
        date = row["date"] or ""
        fields = {
            "group": row["collection"], "type": row["role"], "year": date[:4],
            "date": date, "title": row["title"], "format": "website",
            "subjects": json.dumps(row["subjects"]),
            "search": " ".join([row["title"], row["summary"] or "",
                                *row["creators"], *row["subjects"], *row["aliases"]]),
        }
        attrs = " data-record" + "".join(
            f' data-{key}="{escape(value, quote=True)}"' for key, value in fields.items()
        )

    title = escape(row["title"])
    authors = " · ".join(escape(author) for author in row["creators"])
    date = escape((row["date"] or "")[:10])
    details = " · ".join(filter(None, [escape(row["role"]), authors, date]))
    summary = escape(" ".join((row["summary"] or "").split()) or "Description available in the source record.")
    capture = escape(row["capture_path"], quote=True)
    edition = row["edition_path"]
    edition_link = f'<a href="{escape(edition, quote=True)}">Deposited edition ↗</a>' if edition else ""
    return (
        f'<article class="{css}" id="{escape(row["id"], quote=True)}"{attrs}>'
        f'<p class="eyebrow">{details}</p><h3><a href="{capture}">{title}</a></h3>'
        f'<p>{summary}</p>{edition_link}</article>'
    )


def publication_grid(rows):
    return '<div class="route-grid publication-grid">' + "".join(map(publication_card, rows)) + "</div>"
