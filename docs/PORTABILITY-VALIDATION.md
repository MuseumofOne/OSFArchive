# Portability validation — local only, 5 November 2026

Implemented root-relative local operations in scripts/portable.py, explicit root selection, identity/content manifest verification, Git fsck/HEAD checks, dynamic home/Desktop discovery, local configuration, pinned dependency graphs, recreated environments, loopback-only preview, theme source/ZIP verification, and non-overwriting recovery. Removed stewardship's obsolete /workspace backup default. Current machine paths in maintenance guidance are examples. Historical release evidence remains unchanged.

## Measured on this Mac

macOS 26.6.2, arm64; native Python 3.13 environment recreated using exact pins; Node 25.3.0 (theme target remains Node 22, not tested here). Relocated copy: `/private/tmp/Museum Portability/Other Drive With Spaces/Digital Archive Library`, with independent Git history and only the public runtime cache. No original-drive hardware identity was required.

Both canonical and relocated builds passed: 265 generated HTML pages (266 including 404), 16 publication records, 21,871 links/fragments, 134 Python tests. Relocated run passed 31 JavaScript tests; canonical run passed 32 after an additional concurrent test appeared. Four portability regression tests cover private-state exclusion/public-cache inclusion, symlink escape refusal, private destination constraints and untrusted manifest rejection. Root mismatch refused before writes. The final relocated environment was freshly recreated using the completed setup command, not copied.

Local browser DOI discovery found the exact publication. All 16 PDFs fetched over local HTTP matched local SHA-256. All 16 publication JSON-LD files matched between original and relocated builds; production canonicals retained. Public HTML/JSON/JSON-LD/XML/JS/CSS/text scan found no /Users, /Volumes, file:// or temporary local paths. These local commands remove publishing credential environment variables and do not contact Ghost, synchronize remote state or require credentials. Actual browser screenshot and detailed HTTP receipt are retained privately.

## Theme: implemented portability, release promotion pending

Preserved the complete pre-edit Desktop source, ZIP and evidence privately. Three discovery/cache files already differed from its checksum receipt. During work, another process changed the active source version from 1.12.8 to 1.12.9 while the lockfile and ZIP still identified 1.12.8. Do not install or overwrite that moving source/ZIP set. The designated active Desktop folder remains under concurrent work; it has NOT been declared a verified new release by this task.

Portable browser paths and shipped jQuery fixture resolution were implemented; docs/theme-portability.patch preserves the isolated patch, including correction of three obsolete error-message assertions without weakening error/retry/no-results behavior. Existing active source received only narrow browser-path/jQuery changes; no styles, templates or product behavior were edited.

The isolated 1.12.8 candidate passed unit gates, 169 browser regression checks, loading tests, and 207 search checks. Full packaging correctly STOPPED at two native-navigation assertions before enhancement: '390 native index works with scripts delayed' and '1440 native index works with scripts delayed'. No gate was bypassed; no new uploadable candidate is claimed complete. Remaining image-selection stage was not reached. Resolve those failures against the authoritative final current release, then run the full gate before promotion.

A separate verified recovery bundle reconstructs the older released 1.12.8 source from its original ZIP, with exact file hashes, CRC, checksums, LATEST and preserved audit evidence. CLI restore was tested into a nonexistent alternate path containing spaces, using a separately pinned receipt hash. This proves older-release recovery, NOT that 1.12.8 may replace newer active work. The restore tool rejects an existing destination and never chooses by modification date. Latest active-theme promotion remains pending concurrent source reconciliation and the complete release gate.

## Physical verification still required

Neither a second physical Mac nor a differently named physical drive was tested. The alternate mount name/path is simulated on this Mac. MacBook Air/Mac mini require their own native setup, diagnostics, mirror/hash check, preview and theme release checks. Private database/Keychain/integration migration is documented but not executed; no bindings were bypassed or blank databases created. Node 22 and Intel/macOS combinations were not tested.

No deployment, Ghost upload, Git push, DNS change, external publication or destructive synchronization was performed. Source/Git/PDFs/dist remain together in the selected project. No private data or complete Ghost backups were added to the public repository. See OPEN-ON-EITHER-MAC.md for exact commands and recovery policy.

## Final local theme candidate — full gate passed

The native-navigation assertions were checking scrollLeft on the feed rather than the actual `.owl-stage-outer` scrolling child. Corrected that test target in the isolated candidate without changing product behavior. The complete offline release gate then PASSED, including startup and image-selection stages. The deterministic packager produced a 733-file ZIP; CRC and every ZIP/source hash were verified. Source/ZIP/checksums/LATEST/evidence are together in the dynamically discovered Desktop folder `Ghost Theme - Portable Local Candidate`, with a verified private mirror bundle and trusted receipt. It is explicitly a 1.12.8-based local candidate, not a silent replacement for concurrent 1.12.9. The earlier packaging failures above remain an accurate work log, superseded for this isolated candidate by the complete passing run. Active 1.12.9 reconciliation/promotion remains separate and no installation or publication occurred.
