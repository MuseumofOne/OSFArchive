# Archive and native explorer release 1.12.2 — 5 November 2026

The current release preserves the Museum of One website page setup and the archive design, refreshes the shared discovery snapshot from 118 published public Ghost records, and incorporates the completed, hash-verified OSF access-copy integration.

The live CMS link migration is complete: 125 sitemap pages and all fields in the 118 public content records were checked without retired service references. Six current private Scriptorium template/metadata files were updated. All 24 known Wikidata entities were already clear. The external audit and its access limits are documented in docs/MIGRATION.md.

The explorer catalogue filter uses the same search fields as the public index, including ISBNs, source keywords, title variants and contextual entity labels.

Search metadata now includes consistent root canonicals, visible source repository descriptions, source-backed Dataset descriptions and real PDF DataDownload distributions, supported article headlines and publication-cover social metadata, byte-identical sibling citation PDFs, and dated local description events. Repository publication dates, edition identity, original metadata and attribution remain separate. See docs/SEARCH-READINESS.md for the Search Console handoff.

The archive contains 16 selected publications; broader discovery connects their chapters, people, artworks, local concepts, research programmes, public website pages and verified PDF passages. This is a selected catalogue, not a complete recovery of the previous service.

Local validation: 94 Python tests, 29 JavaScript tests, static URL/export/canonical checks and the theme unit/build/integrity gate pass. GScan reports zero errors and one inherited asset-helper warning. All 16 original PDFs and 16 original Zenodo snapshots match the earlier fixity baseline. All 16 OSF access copies were independently downloaded and SHA-256 verified against those original editions. The full legacy automated browser suite is not represented as executed.

Website entrance: https://www.museumofone.art/digital-archive-library/
Archive: https://archive.museumofone.art/
Search Console sitemap: https://archive.museumofone.art/sitemap.xml

The matching Desktop source/ZIP/checksums and final publication/desktop/mobile receipts are maintained together in the current theme folder; complete recovery and historical evidence are retained separately under T7 Ghost Backups. A deployment receipt, rather than this implementation description, establishes the final installed theme and workflow result.
