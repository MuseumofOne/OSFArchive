# Comprehensive website and archive release — 5 November 2026

The deployed Ghost theme is **1.12.8**. The current page setup, archival design, original artworks and publication bytes are preserved. The release strengthens file metadata, corrects verified source access, stabilizes the native explorer and homepage, and prevents a source outage from replacing the archive with an empty website register.

## Measured results

| Homepage / device | Performance | Accessibility | Best Practices | SEO | Agentic Browsing |
|---|---:|---:|---:|---:|---:|
| [Website · mobile](https://pagespeed.web.dev/analysis/https-www-museumofone-art/vejda7pek2?form_factor=mobile) | 87–88 | 100 | 96 | 100 | 3/3 |
| [Website · desktop](https://pagespeed.web.dev/analysis/https-www-museumofone-art/vejda7pek2?form_factor=desktop) | 100 | 100 | 96 | 100 | 3/3 |
| [Archive · mobile](https://pagespeed.web.dev/analysis/https-archive-museumofone-art/kseodwvuyr?form_factor=mobile) | 100 | 100 | 100 | 100 | 3/3 |
| [Archive · desktop](https://pagespeed.web.dev/analysis/https-archive-museumofone-art/kseodwvuyr?form_factor=desktop) | 100 | 100 | 100 | 100 | 3/3 |

These are PageSpeed Insights homepage Lighthouse lab results. Agentic Browsing values are the actual category results displayed by PageSpeed. The final theme was measured twice; both website runs passed 3/3 on both device modes. The archive passed 3/3 on both modes. PageSpeed reported no real-user field data. Earlier measurements and complete local evidence are retained in the dated audit package.

Website mobile performance remains 87–88 under slow-4G emulation, with LCP around 3.7–3.8 seconds. Ghost's managed analytics request returned HTTP 406 in Lighthouse, leaving website Best Practices at 96. The artwork, navigation, analytics and membership behavior are retained. Archive mobile layout shift fell from 0.447 to 0; website desktop layout shift fell from 0.137 to about 0.03. Website mobile layout shift fell from 0.162 to about 0.083.

## Coverage and repairs

The audit checked **388 sitemap endpoints**: 387 HTML pages and the intentional plaintext research-discovery route. All HTML routes were inspected at 1280px and 390px for geometry, headings, duplicate IDs and loaded-image failures, producing 774 route/viewport checks. Representative screenshots, native interactions and tablet checks at 900, 1024, 1100 and 1440px supplement that coverage. All visible H1 counts were one; no horizontal overflow, duplicate-ID or broken completed-image flags remained. Fourteen generated fragment targets were verified in the rendered site.

All **1,000 first-party link/asset destinations returned HTTP 200**. No HTTP 404 remained among the final destination checks. Ninety-four external destinations could not be automatically confirmed because of authentication, rate limiting, bot restrictions or network responses; their source URLs and responses remain in private audit evidence. External source control is separate from first-party availability. The official Kimsooja bibliography was confirmed by GET after a misleading HEAD response. The unavailable Japanese AICA dialogue access URL now leads to the verified Japanese version on Tomoki Akimaru's note account; the English source, historical publication identity and original dates remain distinct. The doctrine's editorial source label now correctly identifies a dialogue. Original doctrine text and dialogue prose match the pre-audit baseline within the recorded comparison scopes.

The legacy `#public-catalogue` entrance resolves to the shared catalogue view. Native explorer, standalone explorer and global header search each return nine results for “Encounter Differential”; stored-capture access works. The PDF reader rendered page 2 of an 82-page volume and returned to its initial page. The prepared native carousel remains usable without the enhancer, and a preselected panel remains selected after enhancement. Flat native scrolling remains available without JavaScript.

## Metadata and preservation

Capture JSON-LD distinguishes the archival page, source website page and available file encodings. Available files expose MIME type, byte extent, SHA-256 and original source relationships. Image dimensions are measured from local bytes; audio/video roles follow available MIME evidence. Unknown file creators, licences, media durations and upload dates are qualified rather than inferred. Source publication, source modification, first capture, revision capture and verification remain distinct. Bilingual language arrays retain their source values and have readable labels. An accurate archive `llms.txt` guide connects machine readers to the catalogue, website register, provenance, rights, vocabulary, knowledge graph and discovery exports.

All **118 readable capture pages** and **118 original inert HTML downloads** passed SHA-256 verification. All **132 distinct archived upload destinations** passed status/byte-size checks; representative audio, image, PDF, ZIP and JSON files passed full-byte hashes. These cover 154 uploaded source URLs and 22 audio files, with zero failed attachments. All 16 original PDFs and 16 original Zenodo metadata snapshots match the pre-audit fixity baseline. No retired Museum of One archive hostname occurs in the final live HTML or linked destinations checked by this audit.

## Code and operations

The archive passes 126 Python tests, 30 JavaScript tests, static checks of 21,729 local links/fragments and metadata exports, and 50-file stewardship/restoration verification. The theme passes deterministic build/integrity checks, its unit-only gate and GScan with zero errors or warnings. Twenty-three live theme runtime assets match their packaged SHA-256 hashes. Fatal Python-name/syntax checks and targeted unused-import checks pass. The full legacy automated browser suite was not executed; native browser checks and their evidence are recorded separately.

The synchronization publication gate rejects a suspended, missing or malformed report before Pages packaging. A temporary Ghost/API outage leaves the last successful deployment online. A complete verified empty source is accepted so confirmed withdrawals can still apply. Source unavailability can delay withdrawal; an incomplete response is not a confirmed deletion. Half-hourly scheduling remains enabled at minutes 7 and 37 UTC, with push and manual execution also available. GitHub can delay scheduled runs. The implementation and manual reconciliation runs passed; scheduled delivery is not an instantaneous guarantee.

Reader lists remain local to the visitor's browser origin, with no account synchronization. Original software bytes and public uploaded media are preserved within the documented capture budgets; the inert content capture is distinct from a replay of the original executable website environment. See [synchronization operations](WEBSITE-SYNCHRONIZATION.md) and [Search Console handoff](SEARCH-READINESS.md).

The current Desktop folder contains one uploadable theme ZIP and matching source/checksums. The archive working copy remains directly in the T7 Digital Archive Library. Recovery material and complete working-copy backups are stored separately under T7 Ghost Backups. Theme ZIP SHA-256: `00234fb6c3a06e7acb171afbe3352e72d739156fe5169ea737a203343f49aefc`.
