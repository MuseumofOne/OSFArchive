# Museum of One Digital Archive Library

Live at [archive.museumofone.art](https://archive.museumofone.art/), with a [native Ghost entrance](https://www.museumofone.art/digital-archive-library/). See [current deployment and verification](DEPLOYMENT-STATUS.md). The current theme is 1.12.8; the [5 November comprehensive audit](docs/RELEASE-AUDIT-2026-11-05.md) records live metadata, preservation, discovery, visual and PageSpeed verification.

A portable static digital catalogue generated with Python with static HTML item pages, a searchable catalogue, provenance-qualified metadata and JSON-LD. Zenodo remains the publication source of record for curated editions; public Ghost content is the source for automatically captured website records. Verified reading copies are included. No subscription, database or application backend is required.

This is a custom static implementation, not an installed CollectionBuilder or Wax instance. It can be hosted on GitHub Pages using the included workflow.

## Rebuild

Use Python 3.12 (the CI version) with the pinned dependencies: `python -m pip install -r requirements-test.txt -r requirements-sync.txt`. For a current website-inclusive build, run `python scripts/website_state.py pull`, `python scripts/website_sync.py`, `python scripts/check_website_sync.py`, then `python scripts/build.py`. A build without a reconciled runtime checkpoint includes the independently curated catalogue and an empty website register. The current full build requires PyMuPDF for source-PDF text extraction as well as verification; the requirements filename is retained from the earlier test-only setup. The site lives in `dist/`. Relative internal links support GitHub Pages project sites. Set `SITE_ORIGIN` to your eventual public origin (including a project path when applicable) before rebuilding to update canonical URLs, JSON-LD and the sitemap.

## Source and editorial metadata

`data/catalogue.json` contains the source-qualified catalogue. `data/source/` preserves Zenodo metadata snapshots and corroborating institutional evidence. Original creators, titles, dates, licences, DOI and version are retained. Editorial summaries, local classifications and normalized display fields are separate additions; they do not overwrite Zenodo. These additions are not asserted as Library of Congress subject headings or other formally assigned controlled vocabularies.

The first edition is a selected corpus, not an export or complete reconstruction of the expired Omeka collection. Records must be checked before importing additional works. Institutional web dates are not publication dates for deposited editions.

## Updating

Curated editions remain editorially maintained in `data/catalogue.json`; add source evidence and rebuild when changing them. Public Ghost posts/pages and uploaded assets synchronize automatically through the existing Pages workflow every half-hour, on main-branch publication, or on manual Run workflow. Stable IDs, encrypted revision recovery, withdrawal behavior, metadata ownership and resource limits are described in [website synchronization](docs/WEBSITE-SYNCHRONIZATION.md). No automatic Zenodo account synchronization is configured. Do not store Zenodo or Ghost admin tokens in the website.

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

Current repository: MuseumofOne/OSFArchive. Hosting: public GitHub Pages, with HTTPS at archive.museumofone.art. The generated CNAME file and canonical URLs use that hostname. DOMAIN_SETUP.md documents reconfiguration if a hosting migration becomes necessary. This source package excludes the old Sites deployment identity.


## Consolidation branch and Ghost integration

The deployed `main` branch holds the independent archive and its public integration contract. The local consolidation working branch and its existing history are retained. See [architecture](docs/ARCHITECTURE.md), [Ghost integration](docs/GHOST_INTEGRATION.md), [metadata validation](docs/METADATA_VALIDATION.md), [legacy migration](docs/MIGRATION.md), [deployment and rollback](docs/DEPLOYMENT.md), and [maintenance](docs/MAINTENANCE.md).

The current archive working copy is directly in `/Volumes/T7-Shield/Digital Archive Library` on the mounted T7. Theme 1.12.2 is active in Ghost, with the verified automatic-archive discovery configuration. It supplies the native entrance at the existing `/digital-archive-library/` address. The source, ZIP, checksums and current evidence remain together in the existing Desktop theme folder; full Ghost backups and rollback evidence remain separately outside this public repository. See the current deployment status for the exact publication scope and browser checks.

The existing `metadata/discovery.json` reading-list feed and `metadata/search-index.v1.json` integration feed remain compatible. The current shared retrieval contract is `metadata/research-discovery.v2.json`, covering publications, described chapters, entities, concepts, programmes and a live reconciled projection of current published public Ghost records. `metadata/research-passages.v2.json` separately provides literal PDF text-layer passages and source-page links. Both are generated from reviewed inputs and include deterministic content versions. Ghost bundles a curated-only fallback and refreshes from the verified public HTTPS archive feed. Website text is not frozen into new theme packages; it is served from the currently reconciled archive index. See [connected discovery](docs/DISCOVERY.md) and the [metadata profile](docs/METADATA_PROFILE.md).

This repository accepts public, source-evidenced catalogue items only. The build stops before writing artifacts if a future item is marked private, draft or hidden, or lacks the required public Zenodo snapshot. Keep unpublished institutional material outside this public catalogue. Website records use the separate documented public-source policy and never overwrite curated edition identities. Other repositories and descriptive levels need an explicit publication policy before export.

The repository was made public and Pages enabled on 4 November 2026 under explicit publication authorization. DNS, certificate, HTTPS enforcement, deployment and live integration were verified separately from the local build. The current deployment status records that evidence and remaining migration limits.

## Current validation and exports

The build applies the local metadata application profile before publication and validates the generated outputs again. Item CSL-JSON, BibTeX, RIS, visible citations, applicable Scholar tags, qualified Dublin Core and JSON-LD derive from shared models. Typed relationship assertions, the relation register, combined graph, profile and machine-readable quality report are generated under `dist/metadata/`; the visible quality report is `metadata-quality.html`. Passing local gates establish the stated consistency and source checks, not external standards certification or guaranteed indexing.

Current deployed update: [automatic website preservation and native discovery](docs/RELEASE-WEBSITE-SYNC-2026-11-05.md), using theme 1.12.2. The Desktop source, one current ZIP, checksums and evidence match the installed configuration. See [current synchronization checkpoint](docs/WEBSITE-SYNC-CHECKPOINT.md).

## Local portability (no deployment)

See [Open on either Mac](docs/OPEN-ON-EITHER-MAC.md) for explicit root selection, independently verified mirrors, recreated environments and verified Desktop theme recovery. Current machine paths in historical release notes are evidence, not required locations.
