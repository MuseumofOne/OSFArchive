# Current deployment — 4 November 2026

**Local update:** shared explorer 1.12.1 is prepared in the current Desktop folder and T7 source. It is not published; the live deployment described below remains 1.12.0. See [shared explorer](docs/SHARED-EXPLORER.md).

The archive and its native Ghost entrance are live. This publication was explicitly authorized after the earlier preparation hold.

- Archive: https://archive.museumofone.art/
- Institutional entrance: https://www.museumofone.art/digital-archive-library/
- Public source: https://github.com/MuseumofOne/OSFArchive
- Validated implementation commit: `a97dc24a9c73266c229ab48282e512b600a76c44`.
- Successful build/deployment: https://github.com/MuseumofOne/OSFArchive/actions/runs/41910636492
- Active Ghost theme: `museum-of-one-native-archive-1.12.0-prepared`, version `1.12.0`.

## Domain and publishing

GoDaddy manages DNS for the existing domain. The added record is `CNAME archive → museumofone.github.io`, with a provider-reported one-hour TTL. The existing main website and mail records were retained. GitHub Pages uses GitHub Actions, the custom domain is bound to this repository, the certificate is active, and Enforce HTTPS is enabled. HTTP requests redirect to HTTPS.

Future updates to `main` run the existing validation workflow and deploy `dist/` after success. Use the pinned requirements and review source/rights/eligibility before publishing additions. Theme changes remain a separate Ghost upload; regenerate its bundled feeds from the same reviewed build.

## Executed launch checks

The GitHub-hosted build, 83 Python tests, 27 JavaScript tests and fixity verification passed. These JavaScript checks include all 40 declared retrieval benchmarks. The deployment job subsequently succeeded after repository visibility and Pages administration were configured.

Public HTTPS returns the reviewed archive and its 287-record discovery feed. The separate passage feed contains 729 text pages from 16 documents. CORS permits the actual Ghost origin. Catalogue pages, metadata, reader assets and the checked original PDF match their reviewed files. The CI passage feed records pinned PyMuPDF 1.26.6; the Desktop snapshot records the local extractor 1.27.2.2. All passage text, PDF provenance and destinations agree; the recorded extractor version and consequent content hash differ.

Ghost accepted the uploaded theme and activated version 1.12.0. Live CUA checks verified exact DOI search, 28 unique combined-search destinations for “Threads of Sand,” seven publication-passage results for “lived experience,” and arrival at PDF pages 182–183 with no reader console errors. Independent archive discovery returned eight records for “Hassan Sharif.” The narrow live layout had no horizontal overflow at the browser's measured 487-pixel width; the earlier fixture covered 390 pixels. The native entrance has one canonical, one H1, no iframe and no retired-hostname mention. The main homepage also has no retired-hostname mention in its fetched HTML.

The archive entrance's excerpt, search description and two social descriptions were updated to describe the native collection. Its original CMS body was retained. The broader staged CMS-link replacement manifest was not batch-applied during this publication; its field/revision guards must be reconciled before later use, including the four fields already updated here. No Wikidata changes were made.

The exact existing Ghost server has now rendered and served the new template. The earlier local runtime-installation limitation no longer describes production verification. The full legacy automated Playwright suite remains unexecuted; it is not represented as passed.

## Local records and recovery

The current archive remains directly on T7. The Desktop theme folder contains the matching 1.12.0 source, ZIP, checksums and current publication evidence. The previous 1.11.10 source/ZIP remains in the separate private rollback folder, and that theme remains available in Ghost. Private verification receipts, screenshots and recovery packages are kept outside this public repository.

The published implementation was uploaded as an exact snapshot of the current working files. Its commit is retained in local Git history without changing the active integration branch or replacing working files. Earlier dated preparation reports remain historical evidence; this status supersedes their publication hold.
