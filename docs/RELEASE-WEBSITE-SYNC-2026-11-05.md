# Automatic website preservation — 5 November 2026

Museum of One's public Ghost posts and pages now synchronize into the independent archive. The existing GitHub Pages infrastructure reconciles on publication of archive code, manual Run workflow, and half-hourly scheduled runs. Expected delivery is about 30 minutes plus capture/build/deployment time; GitHub can delay scheduled jobs.

## Current publication

- Website register: https://archive.museumofone.art/website-records.html
- Shared native explorer: https://www.museumofone.art/digital-archive-library/
- Encounter Differential capture: https://archive.museumofone.art/website/web-69779e1f63b4d4000180c24b.html
- Public reconciliation report: https://archive.museumofone.art/metadata/website-sync.json
- Capture metadata: https://archive.museumofone.art/metadata/website-captures.json
- Deployed code: c0f2fcefeeea376bad9c33f7ac2ec42d92fb2a1d
- Successful publication: https://github.com/MuseumofOne/OSFArchive/actions/runs/41944734877

The 118 captured public posts/pages include essays, research programmes, book descriptions, public research-tool guides and resources. Their IDs are based on persistent Ghost IDs, so title or URL changes do not create duplicate records. Website updates do not mint book editions. The 16 curated deposit records, their 16 original PDF reading copies and 16 repository metadata snapshots were preserved unchanged.

All 154 current first-party upload URLs were accounted for, comprising 132 distinct preserved public file destinations after checksum deduplication, including 22 audio files. Two URLs reuse existing byte-identical curated PDF copies; 152 URLs can reuse the encrypted media cache. No attachment failures were reported. Third-party providers and embeds remain clearly identified source links.

An older source citation upload contains two obsolete archive destinations. The public archive supplies an access derivative, reconciling those two destinations by the citation's exact DOI and title match to a curated item. The original upload is retained unchanged in encrypted recovery; original-source and access-copy hashes are distinct. The obsolete resource is not linked from the currently rendered Ghost archive page or its theme. Historical source data, already-downloaded copies and third-party caches cannot be recalled.

## Metadata, preservation and access

Source title, credited authors, repeated metadata declarations, source identifiers, subjects, rights/credits and available dates are retained without invented values. Source publication, source modification, first capture, selected revision and verification times have different roles. Raw source content and uploaded bytes have hashes; transformed presentation and qualified citation derivatives have separate hashes. Missing declarations and unverified identifier scope remain visible qualifications.

Public readable pages and inert original content-HTML downloads are rebuilt from the current eligible public set. Earlier revisions and original uploaded files are encrypted for recovery on a separate checkpoint branch. The offline recovery key is unavailable to Actions; the approved asset-cache secret decrypts asset caches only. Source-wide verification failure withholds website captures for that publication while leaving curated editions available. Withdrawals take effect at the next successful deployment; prior downloads, deployment artifacts and historical caches cannot be revoked.

The integration uses the public Content API only, checks publication status/visibility/time, paginates posts and pages, and excludes private/member/draft/future content, internal tags, subscriber data and author account details. It does not edit Ghost publications, republish them or send newsletters. No OSF service, paid hosting or LLM-generated metadata is involved.

The current website theme remains 1.12.2. Only its discovery fallback projection and shared discovery loader changed. All other 721 packaged source files remain byte-identical to the prior theme package. Current ZIP SHA-256: `3a54575b7e31af51dc0ed2b62054acfec53c3cb7f0f91b6a8e08d044cbca07be`. The live loader hash and curated-only fallback were checked against the Desktop package. Global search and the native explorer refresh against the live reconciled archive index.

## Verification

- Successful complete backfill and subsequent reconciliations; 152 encrypted asset reuses; no duplicate revisions in all 118 current records.
- 117 Python tests and 30 JavaScript tests passed, including publication/withdrawal, pagination, retry, resumability, encryption/authentication, stable IDs, source/curated ownership, MIME portability, access derivatives and live-refresh configuration.
- Static validation: 264 HTML files, including the error page, and more than 21,000 local links/fragments; metadata JSON/JSON-LD/XML and original-source fixity passed.
- Live HTTP: 118 record pages, all 118 original HTML-download checksums, all 132 public upload destinations and sample audio/image/ZIP/JSON checksums verified. Both replacement item destinations returned HTTP 200.
- Native desktop/mobile query Encounter Differential: nine connected results, with a functioning stored-capture destination. Archive-side shared discovery also returns nine results. Public archive record and native explorer mobile checks used a 390-pixel viewport and showed no horizontal overflow.

Current implementation, generated archive, tests, documentation and ignored runtime checkpoint are directly on T7 in Digital Archive Library. The current Desktop theme source, one ZIP, checksums, latest pointer and evidence are maintained together. Complete recovery storage is outside the public repository in T7 Ghost Backups. The pre-change 1,966-file recovery was fully hash verified and retained before work began. The current full recovery has a separate inventory and verification receipt in that private backup folder.

## Operating limits

This preserves public content and uploaded bytes, not a guaranteed runnable copy of every interactive environment. Public Encounter Differential instructions, screenshots and demo resources are captured; private or unpublished software is not inferred. External services remain links. Per-file capture is limited to 64 MB; the run budget is 768 MB of captured upload bytes and 5,000 source records. Oversized, unavailable or unsupported material is labelled for review instead of falsely reported as preserved. Larger future audiovisual collections require a capacity review. See WEBSITE-SYNCHRONIZATION.md for maintenance and offline restoration.
