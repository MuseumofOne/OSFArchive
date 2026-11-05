# Website and archive release 1.12.8 — 5 November 2026

The current Ghost theme is **1.12.8**, with ZIP SHA-256 `00234fb6c3a06e7acb171afbe3352e72d739156fe5169ea737a203343f49aefc`. The current page setup and archive design remain in use. See the [comprehensive audit and measured results](docs/RELEASE-AUDIT-2026-11-05.md) and [machine-readable release evidence](docs/AUDIT-2026-11-05.json).

Both sites pass **3/3 Agentic Browsing** on desktop and mobile. The archive scores 100 in all four PageSpeed categories on both modes. Website desktop scores 100 performance, 100 accessibility, 96 Best Practices and 100 SEO; final mobile runs scored 87–88 performance, 100 accessibility, 96 Best Practices and 100 SEO. The remaining website analytics error and mobile timing limits are documented in the audit.

The release audit covers 388 sitemap endpoints, 387 HTML routes at two widths and 1,000 successful first-party destinations. All 118 readable capture pages and original HTML-download hashes were verified, along with 132 public upload destinations, 154 source upload URLs and 22 audio files, with zero failed attachments. All 16 original PDFs and 16 original Zenodo snapshots remain unchanged.

The website and archive share discovery across 287 connected records. Native explorer, standalone explorer and global header search each retrieved nine Encounter Differential results. The scheduled publication gate retains the last live deployment when source reconciliation is incomplete. Complete verified withdrawals still apply on the next successful run. The [synchronization operations](docs/WEBSITE-SYNCHRONIZATION.md) record budgets, recovery and scheduling limits. Existing curated/OSF edition access remains preserved.

Validation: 126 Python tests, 30 JavaScript tests, local link/export checks, stewardship verification, deterministic theme build/unit checks, GScan without errors or warnings, native desktop/mobile/tablet checks and matching live asset hashes. The full legacy automated browser suite was not executed.

Website entrance: https://www.museumofone.art/digital-archive-library/
Archive: https://archive.museumofone.art/
Search Console sitemap: https://archive.museumofone.art/sitemap.xml
Publication workflow: https://github.com/MuseumofOne/OSFArchive/actions/workflows/pages.yml

The current dated Desktop source/ZIP/checksums and T7 working copy carry matching release evidence. Private recovery and complete working-copy backups are retained separately under T7 Ghost Backups. The migration audit and external-access limitations remain documented in docs/MIGRATION.md.
