# Archive and native explorer release 1.12.2 — 5 November 2026

The current release preserves the Museum of One website page setup and archive design, automatically captures 118 public Ghost posts/pages and refreshes native and global discovery against 287 connected records. Current code and its release evidence are documented in [the automatic preservation release](docs/RELEASE-WEBSITE-SYNC-2026-11-05.md); [operations and limits](docs/WEBSITE-SYNCHRONIZATION.md) describe the half-hourly workflow. Existing curated deposit and OSF access-copy integrations were preserved; this synchronization makes no OSF service requests.

Verified current publication: https://github.com/MuseumofOne/OSFArchive/actions/runs/41945708776 . The deployed theme is 1.12.2 with two integration-file changes and ZIP SHA-256 `3a54575b7e31af51dc0ed2b62054acfec53c3cb7f0f91b6a8e08d044cbca07be`. Website register: https://archive.museumofone.art/website-records.html . There are 154 captured upload URLs, 132 distinct preserved public file destinations and 22 audio files, with zero failed attachments. An uploaded citation file receives a labelled access derivative replacing two obsolete item links by exact DOI/title matches; original bytes remain in encrypted recovery.

The prior page-level migration audit (4 November 2026) recorded: 125 sitemap pages and all fields in the 118 public content records were checked without retired service references. Six current private Scriptorium template/metadata files were updated. All 24 known Wikidata entities were already clear. The external audit and its access limits are documented in docs/MIGRATION.md.

The explorer catalogue filter uses the same search fields as the public index, including ISBNs, source keywords, title variants and contextual entity labels.

Search metadata now includes consistent root canonicals, visible source repository descriptions, source-backed Dataset descriptions and real PDF DataDownload distributions, supported article headlines and publication-cover social metadata, byte-identical sibling citation PDFs, and dated local description events. Repository publication dates, edition identity, original metadata and attribution remain separate. See docs/SEARCH-READINESS.md for the Search Console handoff.

The archive contains 16 selected publications; broader discovery connects their chapters, people, artworks, local concepts, research programmes, public website pages and verified PDF passages. This is a selected catalogue, not a complete recovery of the previous service.

Current validation: 117 Python tests, 30 JavaScript tests, static URL/export/canonical checks and the theme unit/build/integrity gate pass. GScan reports zero errors and one inherited asset-helper warning. All 16 original PDFs and 16 original Zenodo snapshots match the earlier fixity baseline. All 16 OSF access copies were independently downloaded and SHA-256 verified against those original editions. Current live checks verified all 118 record pages and original HTML-download hashes, all 132 upload destinations, representative public file hashes, native and archive desktop/mobile search, and global unified retrieval. Encounter Differential returns nine results on each discovery surface, with working stored-capture links. The full legacy automated browser suite is not represented as executed.

Website entrance: https://www.museumofone.art/digital-archive-library/
Archive: https://archive.museumofone.art/
Search Console sitemap: https://archive.museumofone.art/sitemap.xml

The matching Desktop source/ZIP/checksums and final publication/desktop/mobile receipts are maintained together in the current theme folder; complete recovery and historical evidence are retained separately under T7 Ghost Backups. A deployment receipt, rather than this implementation description, establishes the final installed theme and workflow result.
