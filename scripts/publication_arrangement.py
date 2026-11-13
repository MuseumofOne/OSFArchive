"""Editorial browsing routes for public website publications and deposited editions."""

from html import escape
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

ESSAY_PAGES = frozenset({"dong-yeon-koh", "tomoki-akimaru"})


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


def classify_capture(source, deposited):
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
    if source["kind"] == "post" or slug in ESSAY_PAGES:
        return ESSAYS, "Website publication"
    return None, "Website reference"


def publication_inventory(captures, editions):
    deposited = {canonical_key(r["institutional_url"]): r for r in editions if r.get("institutional_url")}
    rows = []
    for capture in captures:
        source = capture["source"]
        group, role = classify_capture(source, deposited)
        edition = deposited.get(canonical_key(source["url"]))
        rows.append({
            "id": capture["archive_id"],
            "title": source["title"],
            "collection": group,
            "role": role,
            "date": capture["original_published_at"],
            "summary": capture["summary"],
            "creators": [creator["name"] for creator in source.get("creators", [])],
            "source_url": source["url"],
            "capture_path": f'website/{capture["archive_id"]}.html',
            "edition_path": f'items/{edition["id"]}.html' if edition else None,
        })
    return sorted(rows, key=lambda row: row["date"] or "", reverse=True)


def publication_card(row):
    title = escape(row["title"])
    authors = " · ".join(escape(author) for author in row["creators"])
    date = escape((row["date"] or "")[:10])
    details = " · ".join(filter(None, [escape(row["role"]), authors, date]))
    summary = escape(" ".join((row["summary"] or "").split()) or "Description available in the source record.")
    capture = escape(row["capture_path"], quote=True)
    edition = row["edition_path"]
    edition_link = f'<a href="{escape(edition, quote=True)}">Deposited edition ↗</a>' if edition else ""
    return (
        f'<article class="route-card publication-card" id="{escape(row["id"], quote=True)}">'
        f'<p class="eyebrow">{details}</p><h3><a href="{capture}">{title}</a></h3>'
        f'<p>{summary}</p>{edition_link}</article>'
    )


def publication_grid(rows):
    return '<div class="route-grid publication-grid">' + "".join(map(publication_card, rows)) + "</div>"
