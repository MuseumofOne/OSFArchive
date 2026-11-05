# One-way website archive synchronization

Source: Museum of One, using its supported public Ghost Content API at `https://the-museum-of-one.ghost.io/ghost/api/content/`. The website origin is `https://www.museumofone.art`. The verified site-upload storage tenant is recorded in `config/website-sync.json`. No Admin API, subscriber endpoint, OSF service or inactive archive is used by this integration.

## Operation and coverage

The existing GitHub Pages workflow runs on main-branch publication, manual **Run workflow**, and every half-hour at minutes 7 and 37 UTC. GitHub may delay scheduled runs; the expected update window is about 30 minutes plus capture/build/deployment time, not an immediate delivery guarantee. The workflow has a 25-minute job budget, four bounded source-request attempts and no overlapping publication runs. The current site remains on the same Ghost theme and page setup.

Each eligible public Ghost post/page receives one stable `web-{Ghost ID}` record under `/website/`. Titles and URLs may change without creating another record. Existing discovery IDs are retained by the initial canonical-URL mapping, then held stable by Ghost ID. Two IDs using the same source URL fail reconciliation for review. Public posts/pages include essays, research, book descriptions, datasets' web records, research programmes, guides and public tool pages such as Encounter Differential. Private tools or unpublished source code cannot be inferred from a public guide.

The importer checks explicit `visibility=public`, publication status, source origin and publication time. It paginates through both complete endpoint collections, excludes internal tags and does not export author accounts, emails, members, subscribers, drafts, scheduled future content or nonpublic body data. It does not write back to Ghost, republish posts, send newsletters or create publication feedback loops.

The archive stores readable content HTML, an inert original content-HTML download, source metadata and permitted uploaded assets. Site-uploaded documents, pictures, audio/video and other supported files are captured under the site owner's archive instruction, retaining original credits and rights exceptions. External services and embeds remain explicitly labelled source links. A public source does not become archive ownership or a new licence. Unsupported/oversized/broken files remain links with an exact reason; they are not counted as locally preserved. Interactive code is preserved in the original source download where public; continued executable behavior or private software access is not claimed.

An uploaded citation JSON containing obsolete archive destinations receives a labelled public access derivative only when the citation's exact DOI and title match a curated item. Its original bytes remain unchanged in encrypted recovery. Source and access-copy checksums are recorded separately; the public report counts replacements. An unresolved obsolete reference withholds that public uploaded file for review instead of inventing an item equivalence or publishing a retired link.

Current resource limits: 5,000 source records, 8 MB per API response, 64 MB per file and 768 MB captured upload bytes per run, including reused cached assets. The GitHub Pages platform has its own site/build limits. Large future audiovisual collections require reviewing these limits and existing hosting capacity; no paid storage is silently purchased. Media types use a fixed extension map so Mac and Linux MIME databases cannot create spurious revisions; this classification is separate from the verified byte checksum.

## Metadata and ownership

`website_metadata.py` maps exact source title (without splitting subtitles from punctuation), credited website authors, repeated metadata declarations, public tags, authored summary where supplied, source-declared language, publisher, contributor, rights/licence, version and related/container statements. Unknown fields remain absent or explicitly qualified. Raw declarations retain repeats and Unicode. No LLM or paid service is involved.

Original website publication, current source publication field, source modification, first archive capture, selected revision capture and verification timestamps are distinct. The first observed publication date is never silently overwritten. DOI declarations matching a preserved curated deposit are marked with that exact evidence scope; concept DOIs remain version-family references. Other DOI/ISBN/ISSN/ORCID declarations are source assertions, not newly verified identities. A webpage update never mints a book edition. Existing `data/catalogue.json`, original files, citations, authority records, subject enrichment and programme curation are not mutated by synchronization.

Content hashes and asset signatures suppress duplicate revisions. Repeated runs verify current source visibility and assets. Source modification timestamps older than the checkpoint are withheld rather than downgrading an archived record. Checkpoints are written after each completed record; failed runs can retain encrypted partial progress, and the next run reconciles the full source again.

## Withdrawal and recovery

A complete reconciliation removes missing/unpublished/nonpublic web records and their unreferenced readable assets from the next Pages artifact. Persistent capture history is encrypted with AES-256-GCM and RSA-OAEP to an offline recovery key. Only ciphertext and opaque ID/hash/revision mappings are stored on the separate `website-sync-state` branch. No offline private recovery key is available to GitHub Actions. The separately approved `MOO_ASSET_CACHE_KEY` repository secret permits reuse of encrypted uploaded-file caches after the source remains public and its ETag matches. It cannot decrypt record-history capsules, which have no runtime key wrapper. This avoids repeatedly downloading unchanged media from Ghost or GitHub Pages. The main branch is not edited by the scheduled job.

If the source collection cannot be completely verified, reconciliation is suspended. An isolated local build without a verified runtime contains no readable website captures. The publication gate (`python scripts/check_website_sync.py`) rejects a suspended, missing or malformed report before GitHub Pages packaging: the last successful live archive remains unchanged. An incomplete source response is never treated as a confirmed withdrawal. A complete verified empty source is accepted, so confirmed withdrawals still apply on the next successful reconciliation. Encrypted recovery history is retained. A platform/build/deployment outage can delay removal until a successful publication. Previously downloaded public copies, third-party caches, old Git history and short-lived deployment artifacts cannot be recalled. The current Ghost explorer fallback is restricted to independently public curated records. Website discovery text comes from the live reconciled archive index; an unavailable refresh therefore cannot restore frozen website text. Historical copies and already-downloaded caches cannot be revoked.

The encrypted private recovery key is held under the private T7 `Ghost Backups/archive-integration-current/website-sync-2026-11-05` folder. Its passphrase is in this Mac's Keychain under service `moo-website-sync-recovery-v1`, account `museum-of-one`. Back up the Mac Keychain as well as T7; losing both loses decryption capability. Only `config/website-recovery-public.pem` belongs in the repository. The asset-cache key is separately retained in this Mac’s Keychain as `moo-website-sync-asset-cache-v1`; its only remote storage is GitHub Actions secrets.

Offline recovery (output must be outside the public repository):

```sh
python3 scripts/restore_website_capture.py --vault /private/recovery/vault/ID/HASH.json --key '/Volumes/T7-Shield/Ghost Backups/archive-integration-current/website-sync-2026-11-05/recovery-key.encrypted.pem' --output /private/recovered-record.json
```

## Manual reconciliation and maintenance

In GitHub, open **Actions → Build and deploy archive → Run workflow** on `main`. This uses the same checkpoint, validation and Pages deployment as the schedule. Read the Actions summary and `/metadata/website-sync.json`; the public register is `/website-records.html`. A successful workflow result and live HTTP verification establish deployment, not merely a local build.

Local maintenance:

```sh
python3 -m pip install -r requirements-test.txt -r requirements-sync.txt
python3 scripts/website_state.py pull
python3 scripts/website_sync.py --dry-run
python3 scripts/website_sync.py
python3 scripts/build.py
python3 scripts/check.py
```

Local reads need only the public API. Saving the checkpoint uses the repository's existing authenticated Git transport. Actions uses its built-in short-lived repository token with contents-write permission only in the reconciliation job; Pages publication retains its existing permissions. No PAT, webhook secret, Ghost admin token or new paid hosting is required. The user approved the asset-only cache key in supported Actions secret storage. Ghost integration changes are confined to the fallback discovery projection (curated records only) and its index size budget; publications, design, theme layout and unrelated settings are unchanged. Failed pushes are lease-protected; do not force over a conflicting checkpoint. Restore it and reconcile again. Keep public keys stable until a deliberate key migration; old ciphertext needs its original private key.

Before deployment, the current 1.12.2 archive recovery package was fully hash verified and preserved as `website-sync-2026-11-05/before-sync.tar.gz` with its manifest. Rollback: disable the schedule, restore the prior implementation commit or reviewed source backup, and rebuild only the appropriate currently public material. Do not republish withdrawn content simply by restoring an old snapshot. Ghost requires no content rollback because synchronization never writes its publications.
