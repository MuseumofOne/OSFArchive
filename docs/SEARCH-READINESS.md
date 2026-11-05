# Search discovery implementation — 5 November 2026

The archive publishes static, crawlable descriptions with one self-canonical URL per HTML page, a consistent root homepage, a robots sitemap declaration and an XML sitemap excluding the noindex 404 page. Catalogue revision dates come from explicit local description-history events; repository modification, work publication and file verification remain separate.

Every item retains source-qualified identity, version DOI, source title, documented creator/contributor roles, date precision, rights, language, subjects and provenance. Work, edition, repository family, website page and local catalogue description remain distinct nodes. Linked entities, chapters, concepts and research programmes support unified discovery without turning references into endorsements or identity claims.

Repository descriptions are exposed visibly as source transcriptions, separately from editorial summaries. Structured data uses that description without claiming every deposit description is an author-written abstract. Scholarly citation tags retain the deposited edition's supported bibliographic fields. Citation PDF URLs are byte-identical `/items/{id}.pdf` siblings of item HTML pages; original `/assets/documents/{id}.pdf` files and reader routes remain available. Google Scholar decides content eligibility and inclusion.

Dataset nodes include source-backed descriptions and DataDownload distributions for actual deposited PDF files; no CSV or empirical data file is invented. Item social metadata includes available publication covers and accessible cover descriptions. Unknown author, identifier scope, custody, review status and date information remain qualified.

The shared explorer uses the refreshed 118-page public Ghost snapshot alongside publications, chapters, entities, concepts, programmes and verified PDF passage text. No private/member-only CMS records are exported. Original PDFs and the 16 original Zenodo snapshots remain unchanged.

## Search Console handoff

Property: `https://archive.museumofone.art/` (or a verified parent Domain property covering this subdomain).

Submit: `https://archive.museumofone.art/sitemap.xml`.

Inspect the root, one item, one dataset, one entity and a citation PDF. Use Live Test and request indexing after the published versions are confirmed. Review Page indexing, selected canonical, sitemap processing and crawl errors after Google recrawls. Structured data validation is an implementation check, not evidence of search inclusion or ranking.

Primary guidance consulted:
- https://developers.google.com/search/docs/essentials
- https://developers.google.com/search/docs/appearance/structured-data/dataset
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://scholar.google.com/intl/en/scholar/inclusion.html

## Comprehensive audit additions — 5 November 2026

Current capture records expose source-qualified file encodings with MIME types, byte sizes, SHA-256 and measured image dimensions. Source authorship remains on the source page; unknown embedded-file roles, licences, dates and media duration remain qualified. Raw original content is delivered as inert text, separately from the readable archival record. The archive publishes a truthful root `llms.txt` guide linked from its HTML pages. Its homepage scored 100 accessibility/SEO/Best Practices/performance and 3/3 Agentic Browsing in both PageSpeed device modes; full coverage and measured limitations are in [the comprehensive audit](RELEASE-AUDIT-2026-11-05.md).
