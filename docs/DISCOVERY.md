# Connected research discovery

The archive exposes publications, described chapters, contextual entities,
local vocabulary concepts, research programmes, and reviewed public website
pages through one versioned search contract. It keeps the existing v1 archive
feed and browser reading-list contract intact.

## Public outputs

- `metadata/research-discovery.v2.json`: compact bibliographic and contextual
  index. Every record has a stable typed `id`, `kind`, `title`, canonical `url`,
  source evidence, searchable text, and explicit relationships where supported.
- `metadata/research-passages.v2.json`: separately loaded PDF text-layer index
  and extraction manifests. Search loads it only when the reader chooses to
  include source passages. It is not necessary for ordinary title/name search.
- `research-discovery.html`: the shared discovery interface, including a static
  list of every described record as a no-JavaScript browsing fallback.

The initial archive corpus contributes 169 described records: 16 publications,
57 components, 36 entities, 50 vocabulary concepts and ten programmes. A reviewed
Ghost snapshot adds public website destinations without converting web dates
into edition dates. Counts in the generated feed are the release authority.

## Identity and evidence

Record IDs have explicit prefixes: `publication:`, `chapter:`, `entity:`,
`concept:`, `programme:`, `website:` and `passage:`. URLs retain the existing
catalogue, component, authority, vocabulary and programme routes. Website IDs
derive deterministically from the full canonical public URL.

Publication identity is the deposited edition DOI. Concept DOIs group repository
versions; title-level ISBNs remain qualified when they cannot be assigned to the
specific deposited file. Exact-identifier search displays these distinctions.
Chapters receive local analytic references, not invented DOIs. Entity identities
use `entities/{id}.html#entity`, distinct from the describing web page.

Every graph edge retains its relation label and source URL. Chapter containment
comes from reviewed pagination. A passage falls within a chapter only when its
PDF file page is inside that chapter's checked extent. This is structural
containment, not a generated claim about its topics. Entity–publication evidence
that is only known at publication level is not silently promoted to a specific
chapter or passage. Related names enrich retrieval but are not represented as
alternative titles of the publication.

Website-to-publication links require equality with the catalogue's explicit
`institutional_url`. This means a source-qualified website description, not
proof that a web article and a deposited edition are identical texts. Live Ghost
results and a bundled archive snapshot are deduplicated only by exact canonical
URL or identical record ID.

Both directions of the website/publication link carry `institutional_match_scope`
and `evidence_scope`: `exact_edition`, `version_family` or `work`. The reviewed
DOI links determine that scope; the interface displays its meaning and does not
promote a family/work match into an edition match. Entity/publication links use
the same supplied evidence scope in both directions, defaulting to work level.

## Public eligibility

The builder reuses the archive's fail-closed publication gate and checks the
matching public Zenodo source snapshots. Contextual records require source
evidence and a link to an eligible item. Vocabulary records require an editorial
owner, review date and documented corpus warrant. Programmes require a reviewed
public source. Private/draft flags exclude contextual records and their graph
edges; invalid or private publication/component input stops the build.

Optional Ghost inputs require `public: true`, an allowed canonical URL on
`https://www.museumofone.art`, a matching source URL, review date and SHA-256 of the
captured public source. The search feed does not imply that a historically public
snapshot is still current. A release must refresh this snapshot; existing live
Ghost search can supply current published Posts and Pages.

## Full text and rights

The supplied public PDFs are processed as authorized corpus material. Extraction
does not modify the PDF, perform OCR, rewrite text or replace any licence. Each
document manifest records the exact source SHA-256, byte/page extent checks,
repository source, author, per-item licence, extraction method and PyMuPDF
version. The PDF text layer is retained verbatim. Display snippets are literal
slices, with an ellipsis only when truncated; rendering uses text nodes.

All 16 supplied PDFs currently contain 743 file pages, of which 729 contain
extractable text. Empty/sparse pages and replacement-character counts are
reported. Reading order has not been reviewed page by page and is not claimed
to reproduce visual layout. Passage results link directly to the corresponding
PDF file page and retain the original item attribution/licence. The full PDF is
the authority for page layout and wording. Rebuilding fails if source fixity or
measured page counts disagree with the reading-copy manifest.

## Retrieval behavior

Exact identifiers, titles and verified aliases rank above title-term matches,
descriptions, source passages and general metadata matches. DOI URLs, `doi:`
prefixes, ORCID URLs, case, diacritics and common typographic apostrophes/dashes
are normalized for matching. Quoted phrases must occur within one indexed field.
Unquoted terms use conjunctive matching. Type, collection, year and subject
filters are available through the shared API; the current page exposes type.

With passage search enabled, Publications includes passages belonging to an
edition, and Chapters includes passages inside a checked chapter extent.
The API enables this through `filters.includePassages=true`. Source passages
only selects the passage results and automatically enables their index. Other
types exclude passages; the page disables the passage checkbox and explains
the scope if it had been selected. These filters do not infer that a passage is
about a person or concept merely because its parent publication has that link.

Each result explains the matching field and offers its evidence-bearing
connections. Ranking is deterministic and has no hidden popularity metric,
generated relationship, third-party tracking or remote language-model request.
It does not currently provide typo correction, translation, semantic embeddings
or inference across multiple graph edges.

`data/discovery-benchmark.json` defines 40 actual-corpus known-item retrieval
tasks: identifier forms, titles, chapters, entity variants, concept aliases,
programme identifiers and verbatim passages. Tests assert the declared target
rank. This is a regression benchmark, not a claim that all research questions
are answerable or that the system outperforms another institution. Extend it
with failed real reader tasks rather than adjusting expectations to hide a
regression.

## Shared browser API and failure behavior

`MuseumResearchDiscovery` exports `validateIndex(payload, origin)`,
`rankRecords(records, query, filters)`, `mergeIndexes(groups)`,
`loadIndexes(config, onIndex, fetcher)`, and `mount(container)`. Rank results are
record objects with `score`, `match_reason`, and a verbatim `snippet` for passages.

`loadIndexes` accepts `{origin, snapshot, remote, pageURL}`. A bundled snapshot
must be on the page's own origin. An optional remote refresh must be exactly the
archive's v2 index endpoint. Both requests omit credentials and have time/size
limits. Failed remote requests or invalid data retain the validated snapshot.
If neither index loads, the form keeps its ordinary navigation behavior and
static browse links remain available. Deployment must verify actual cross-origin
headers before enabling remote refresh from Ghost.

The mount contract uses `[data-research-discovery]`, `data-archive-origin`,
`data-index-snapshot`, optional `data-index-url` and `data-passages-url`, a form
`[data-discovery-form]`, input `name=q`, and result/status elements
`[data-discovery-results]` / `[data-discovery-status]`. The status region should
use `role=status`. `data-search-only=true` keeps a curated Ghost entrance quiet
until a query/filter is entered. `data-sync-url=true` enables shareable query
URLs on the standalone page. Only a successfully loaded index intercepts form
submission. The public source URLs are never rendered as HTML.

The standalone page alone sets `data-local-results=true`. The shared `resultURL`
helper maps archive destinations, chapter-reader links and archive evidence
links onto the current page's directory. Consequently the same files work at
localhost, a GitHub project path or the custom archive hostname. Canonical feed
URLs remain absolute and unchanged; public Ghost/Zenodo links remain external.
The native Ghost entrance does not set this option and keeps its absolute
archive destinations. Static browse links also use relative archive paths.

## Release checks

Run the ordinary archive build and checks, Python discovery tests and
`node --test tests/research-discovery.test.cjs`. The latter runs the real feed
benchmark and failure/validation tests. Browser review remains necessary for
keyboard interaction, mobile layout, meaningful relation labels, no-JavaScript
browse access, both source failures, and direct arrival at a cited source page.
