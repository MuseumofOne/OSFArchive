# Maintaining the Digital Archive Library

## Working location and authority

Work from the verified checkout directly at `/Volumes/T7-Shield/Digital Archive Library`. The T7 is mounted at `/Volumes/T7-Shield`; the extracted transfer was byte-verified and the project was moved into this direct root. Keep current Ghost source, release ZIP, checksums and evidence together in the designated Desktop theme folder identified by its verified `CURRENT-RELEASE.json`; use [Open on either Mac](OPEN-ON-EITHER-MAC.md) for explicit path selection and verification. Keep full Ghost backups separately in the selected private backup area outside the public repository. Follow `AGENTS.md` for folder maintenance. Preserve the actual last verified working source/ZIP and its receipt before promoting a replacement; historical package versions are not automatically the right rollback target.

No further Google Drive updates are part of this workflow. Earlier backup evidence remains historical evidence of that earlier copy, not proof that later changes or the T7 are backed up. A T7 working copy is not, by itself, an independent backup.

The editable record authority is `data/catalogue.json`, supplemented by the documented sidecars in [ARCHITECTURE.md](ARCHITECTURE.md). Never edit generated item HTML, citations or search indexes to correct metadata. The next build replaces them. `dist/assets/` contains maintained assets and original PDF copies; **do not delete the whole `dist/` directory as a cleanup step**.

## Add a record

1. Start a branch from the agreed source revision. Obtain a public source record and corroborating institutional page. Keep credentials, unpublished manuscripts and private correspondence outside the repository.
2. Preserve the unmodified source metadata under `data/source/{id}.json`. Add one item in `catalogue.json` with a stable ID, unused accession, unchanged source title, creator statement, source date precision, type, version, repository URL, rights and evidence. Check the current catalogue and reserved or withdrawn assignments, then choose the next number above the highest assigned `MOO-CAT-` accession. Never fill gaps, reuse an accession, or derive one from array positions. Confirm uniqueness before publishing; retain every existing assignment.
3. Add a source-backed local summary, relevant subjects and collection. Use only applicable identifiers. Preserve conflicting statements as qualified evidence rather than silently choosing a more impressive identifier or date.
4. Add verified relationships in the existing entities, contents, vocabulary, programmes or PIRR sidecars as appropriate. An external authority link needs source and scope. Do not assign a formal LCSH/Getty equivalence, institutional affiliation or new PIRR identifier without evidence.
5. If a permitted PDF is included, retain the exact source bytes in `dist/assets/documents/`, record its source URL, filename, MD5 agreement, measured SHA-256/bytes/page count and reader manifest in `data/readers.json`. Confirm file-level rights. Other media may need a tailored viewer; do not label them PDFs or fake page counts.
6. Ensure the item's explicit publication/access status and matching source snapshot satisfy the public integration-feed rule. Do not stage private records in a repository intended to be public, even if they are excluded from the feed.
7. Rebuild, review the visible page and exports, run the checks below, then refresh preservation evidence only for the reviewed additions. Commit the source, generated output and evidence together.

## Correct an existing record

Preserve its accession, ID, published route and verified edition identifiers. Edit the actual source input for a derived field. `enrich_record()` recalculates title variants, date precision, file extent, identifier syntax, serial context and authority links; a one-off edit to their cached copies may disappear.

Record the correction's evidence and local description history. A repository modification timestamp is not the local correction date. Use explicit local lifecycle dates only when known; leave historical creation dates absent rather than retroactively inventing them. Compare the regenerated visible citation, CSL-JSON, BibTeX, RIS, DC and JSON-LD. Unresolved source conflicts should remain visible and qualified.

`data/description-baseline.json` scopes the documented 4 November 2026 description events to the initial 16 records. Never extend that baseline list to backdate a later addition. Add later record-specific events to the record's `description_history`, with the actual date, action, evidence and stable event ID. Unknown records remain undated. The baseline ledger and later description events are explicit source files. Earlier offsite backup evidence covers only its recorded inventory digest; additions require a reviewed new content baseline and recovery test.

## Publish a new edition or repository version

Keep the old edition accessible. Capture the new source record and version-specific DOI separately, verify changed files and identifiers, and assign a new item when describing a different deposited edition. Link previous/new editions and the concept DOI family without transferring a DOI or ISBN merely because the titles resemble one another. A repository version number is not automatically a new book edition. Document an exceptional same-record migration before changing any published identity.

## Build and verify

Run from the repository root with Python 3.12 and a current Node version:

```sh
python -m pip install -r requirements-test.txt
python scripts/build.py
python scripts/check.py
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.cjs
python scripts/stewardship.py --verify
```

The complete build now requires pinned PyMuPDF for literal PDF text-layer indexing as well as source verification. Install `requirements-test.txt` before building; its earlier test-only filename is retained. No application backend is required for serving the generated archive. Internal link, export and code tests do not substitute for browser, keyboard, mobile, screen-reader or live-link checks. Inspect representative book, article, dataset, analytic and programme records; search for titles, identifiers, subjects and PIRR references; exercise PDF reading and unavailable-network fallbacks.

The builder regenerates the catalogue, record pages, metadata, citations, sitemap and integration feed from the same inputs. `metadata/discovery.json` remains the archive reading-list feed. `metadata/search-index.v1.json` remains compatible; the current shared Ghost/archive retrieval contract is `metadata/research-discovery.v2.json`, with lazily loaded `metadata/research-passages.v2.json`. The website snapshot is a reviewed public projection, not a live account connection. Its content version changes with its public payload; no manual timestamp synchronization is required. A bundled Ghost snapshot is a fallback and needs refreshing when a new approved theme package is prepared. Remote refresh is only considered working after the actual deployed feed and CORS behavior have been tested.

## Integrity and recovery

A verification failure is evidence to investigate, not a reason to refresh the baseline immediately. Compare the changed files with the intended edit and source evidence. After legitimate additions/corrections have been reviewed, explicitly refresh the content inventory and create a recovery package **outside the repository**:

```sh
python scripts/stewardship.py --inventory --verify
python scripts/stewardship.py --verify --backup /path/outside/repository/museum-of-one-preservation-backup.tar.gz
python scripts/build.py
python scripts/check.py
```

Use an explicit private destination outside the public repository, for example a dated file in `/Volumes/T7-Shield/Ghost Backups` or another dedicated private recovery folder. Do not rely on the CLI's historical `/workspace` default. The backup command performs a real isolated extraction and hash comparison. Both `--verify` and `--backup` append measured events to `data/stewardship.json`; `--inventory`/`--refresh` explicitly replace the expected content inventory. Preserve the prior report and recovery package before a reviewed refresh. Rebuild after recording evidence so the public register matches it. Its preservation scope is inventoried source/catalogue/PDF content, not a full disk image or every application dependency. Preserve a separate source checkout or release package as well. Never publish private backup receipts or storage URLs in the catalogue.

Before relying on a backup, copy it to the intended storage, compare its SHA-256 with the recorded package digest and test restoration. Recovery to the original production services requires the deployment authorization and rollback procedure in [DEPLOYMENT.md](DEPLOYMENT.md).

## Publishing and indexing routine

Review the branch diff and testing report before requesting deployment. A merge or push to `main` can trigger the existing Pages deployment workflow. Do not use `main` as an unreviewed staging branch. Ghost installation is a separate operation and must preserve the previous working theme.

After an authorized release, verify the public HTTPS homepage, representative item/reader URLs, canonical origin, sitemap, robots directives, downloadable citations and Ghost/archive links. Verify feed CORS and fallback behavior from the actual Ghost origin. Search Console ownership and sitemap submission can help inspect crawl/indexing status when account access is available. Scholar eligibility is assessed per publication and site policy; citation tags alone do not guarantee inclusion.

## Final source preservation check

Before refreshing the preservation baseline, compare the existing inventory with current files and explain every addition/change. Original saved repository snapshots and PDF bytes must retain their earlier digests unless a separately documented source/version migration was authorized. The inventory covers all JSON under `data/` except `data/stewardship.json` and original PDFs under `dist/assets/documents/`; it does not cover scripts, templates, generated HTML, dependencies or covers. Keep a separate complete source/release backup. Existing local/offsite backup events remain evidence of their own inventory digests, not proof that the latest working changes are backed up.
