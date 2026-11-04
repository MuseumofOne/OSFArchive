# Museum of One Digital Archive Library

A portable static digital catalogue generated with Python with static HTML item pages, a searchable catalogue, provenance-qualified metadata and JSON-LD. Zenodo remains the publication source of record; verified reading copies are included. No subscription, database or application backend is required.

This is a custom static implementation, not an installed CollectionBuilder or Wax instance. It can be hosted on GitHub Pages using the included workflow.

## Rebuild

Use Python 3.12 (the CI version) with the pinned dependencies from `requirements-test.txt`: `python -m pip install -r requirements-test.txt`, then run `python scripts/build.py`. The current full build requires PyMuPDF for source-PDF text extraction as well as verification; the requirements filename is retained from the earlier test-only setup. The site lives in `dist/`. Relative internal links support GitHub Pages project sites. Set `SITE_ORIGIN` to your eventual public origin (including a project path when applicable) before rebuilding to update canonical URLs, JSON-LD and the sitemap.

## Source and editorial metadata

`data/catalogue.json` contains the source-qualified catalogue. `data/source/` preserves Zenodo metadata snapshots and corroborating institutional evidence. Original creators, titles, dates, licences, DOI and version are retained. Editorial summaries, local classifications and normalized display fields are separate additions; they do not overwrite Zenodo. These additions are not asserted as Library of Congress subject headings or other formally assigned controlled vocabularies.

The first edition is a selected corpus, not an export or complete reconstruction of the expired Omeka collection. Records must be checked before importing additional works. Institutional web dates are not publication dates for deposited editions.

## Updating

Update the records in `data/catalogue.json`, add source evidence and rebuild. No live account access or automatic Zenodo synchronization is configured. Do not store Zenodo tokens in the website.

## Free GitHub Pages hosting

Upload this project to a GitHub repository. In repository Settings → Pages, select GitHub Actions as the source. The workflow builds and deploys `dist/`. Set the `SITE_ORIGIN` repository variable to the GitHub Pages URL or custom domain to use the correct canonical addresses. GitHub's own current terms and limits apply.

## Rights

Work-specific licences are displayed on item pages. Cover images are credited to Museum of One publication pages and are used to identify the publications. Their display does not assert rights in artwork depicted on those covers. Follow the original record and file notices for reuse.

## Reading room tools

The library includes shelf/list views, bookmark controls, a browser-local reading list, a two- or three-record comparison table, CSV export, publication cover enlargement and an interactive featured shelf. Reading lists stay in the visitor’s browser; they are not transmitted or synchronized to an account. If browser storage is unavailable they last only for the current visit.

The “Inside the record” panel distinguishes title variants, identifier syntax checks, role statements and field-level provenance. Syntax/checksum validity does not establish agency registration or edition applicability. Build-time enrichment is idempotent and preserves source snapshots.

Run `python scripts/build.py`, `python scripts/check.py`, `python -m unittest discover -s tests -p 'test_*.py'`, and `node --test tests/*.test.cjs` before publishing changes. These checks do not replace browser rendering or accessibility checks.

## In-site document reader and archival finding aid

All selected PDF items have in-site reader pages with single/facing-page modes, thumbnails, page-number navigation, zoom, fullscreen and page-text disclosures. The PDF.js 6.5.438 legacy distribution is vendored under assets/vendor/pdfjs with its Apache 2.0 licence, font/CMap/WASM assets, and version information. No Issuu account or external reader service is required.

The complete original PDFs are available under dist/assets/documents. data/readers.json records their source URLs, exact source filenames, source MD5 matches, local SHA-256, byte extent, and measured PDF page counts. These are access copies, not claims of legal deposit, original custody or certified preservation. Work-specific licences and third-party material rights remain attached to the originals.

When adding an item, obtain the permitted source PDF, verify its checksum, and create its reader manifest. The builder generates reader pages and links from data/readers.json. Never replace a different edition’s source bytes under an existing reference without a documented version migration. Use a new version record when needed.

The finding aid records the catalogue’s scope, explicitly editorial arrangement, conditions of access and use, and a downloadable CSV item inventory. It does not claim a recovered fonds or physical holdings.

## Institutional research catalogue

The source includes 36 locally maintained, source-qualified people/organisation/artwork/exhibition records, 57 verified analytic descriptions within the four book editions, a versioned local subject/genre vocabulary, and a PIRR research crosswalk. Individual publication DOIs remain edition identifiers; PIRR project IDs and programme references identify research records. Chapter descriptions inherit their parent’s publication context without receiving a fabricated DOI or PIRR work identifier.

Policies, description responsibility/history, source acquisition context, research enquiries and a persistent collection tree are built into the archive. `data/policies.json` records adopted current operating rules. `data/stewardship.json` contains measured verification and restoration events; the report is deliberately outside its own content inventory.

## Hosting target

Target repository: MuseumofOne/OSFArchive. Hosting: public GitHub Pages. Custom hostname: archive.museumofone.art. The generated CNAME file and canonical URLs use that hostname. Add the DNS CNAME described in DOMAIN_SETUP.md and enable Pages with GitHub Actions. This source package excludes the old Sites deployment identity.


## Consolidation branch and Ghost integration

The `integration/ghost-archive-consolidation` branch prepares the independent archive and its public integration contract. See [architecture](docs/ARCHITECTURE.md), [Ghost integration](docs/GHOST_INTEGRATION.md), [metadata validation](docs/METADATA_VALIDATION.md), [legacy migration](docs/MIGRATION.md), [deployment and rollback](docs/DEPLOYMENT.md), and [maintenance](docs/MAINTENANCE.md).

The current archive working copy is directly in `/Volumes/T7-Shield/Digital Archive Library` on the mounted T7. The latest functioning Desktop theme, version 1.11.10, was inspected and verified against its ZIP. The prepared 1.12.0 theme adds a native entrance at the existing `/digital-archive-library/` address and replaces public legacy destinations. The source, ZIP, checksums and current evidence belong together in the existing Desktop theme folder; full Ghost backups remain separately outside this public repository. Final package/browser results are recorded in release evidence. No further Google Drive updates, Ghost installation, deployment or DNS changes are part of this local preparation.

The existing `metadata/discovery.json` reading-list feed and `metadata/search-index.v1.json` integration feed remain compatible. The current shared retrieval contract is `metadata/research-discovery.v2.json`, covering publications, described chapters, entities, concepts, programmes and a reviewed snapshot of published public Ghost records. `metadata/research-passages.v2.json` separately provides literal PDF text-layer passages and source-page links. Both are generated from reviewed inputs and include deterministic content versions. Ghost bundles matching snapshots; remote refresh remains disabled until public HTTPS/CORS are verified. See [connected discovery](docs/DISCOVERY.md) and the [metadata profile](docs/METADATA_PROFILE.md).

This repository accepts public, source-evidenced catalogue items only. The build stops before writing artifacts if a future item is marked private, draft or hidden, or lacks the required public Zenodo snapshot. Keep unpublished institutional material outside this public catalogue. Other repositories and descriptive levels need an explicit publication policy before export.

The handoff inspection recorded the target GitHub repository as private with Pages disabled; that administration state has not been reverified by this local build. A hosting target, generated CNAME file or successful local build is not evidence of a public deployment. Production installation, deployment and DNS changes require explicit authorization under the current implementation instructions.

## Current validation and exports

The build applies the local metadata application profile before publication and validates the generated outputs again. Item CSL-JSON, BibTeX, RIS, visible citations, applicable Scholar tags, qualified Dublin Core and JSON-LD derive from shared models. Typed relationship assertions, the relation register, combined graph, profile and machine-readable quality report are generated under `dist/metadata/`; the visible quality report is `metadata-quality.html`. Passing local gates establish the stated consistency and source checks, not external standards certification or guaranteed indexing.
