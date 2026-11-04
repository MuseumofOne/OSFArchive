# Museum of One Digital Archive Library

A portable, buildless digital catalogue with static HTML item pages, a searchable catalogue, provenance-qualified metadata and JSON-LD. Zenodo remains the publication source of record; verified reading copies are included. No subscription, database or application backend is required.

This is a custom static implementation, not an installed CollectionBuilder or Wax instance. It can be hosted on GitHub Pages using the included workflow.

## Rebuild

Run `python scripts/build.py`. The site lives in `dist/`. Relative internal links support GitHub Pages project sites. Set `SITE_ORIGIN` to your eventual public origin (including a project path when applicable) before rebuilding to update canonical URLs, JSON-LD and the sitemap.

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
