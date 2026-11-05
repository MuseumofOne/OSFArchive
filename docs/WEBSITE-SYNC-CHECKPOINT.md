# Synchronization checkpoint — 5 November 2026

Deployed implementation: `c0f2fcefeeea376bad9c33f7ac2ec42d92fb2a1d`. Successful Actions publication: https://github.com/MuseumofOne/OSFArchive/actions/runs/41944734877 . The archive serves 118 public website captures, with 287 connected discovery records in total. The 16 curated publication editions remain independently described and unchanged.

Verified: 118 public record pages; SHA-256 of all 118 original content-HTML downloads; 132 distinct preserved upload destinations covering 154 source upload URLs and 22 audio files; zero failed attachments. One uploaded citation resource has an explicitly labelled access derivative replacing two obsolete destinations by exact DOI/title matches. Original source bytes remain in encrypted recovery.

Reconciliation reuses encrypted files for 152 upload URLs and leaves all 118 existing revision lists unchanged. Both complete public Ghost collections are paginated. No Admin API or OSF service is used. Missing/nonpublic source records lose their readable archive copies at the next successful publication; encrypted history remains recoverable.

The current Ghost theme is 1.12.2 with two necessary integration-file changes: the curated-only fallback discovery projection and the shared live-refresh loader. Its ZIP SHA-256 is `3a54575b7e31af51dc0ed2b62054acfec53c3cb7f0f91b6a8e08d044cbca07be`. The website's content, styling, layout and navigation were preserved. Native desktop/mobile search for Encounter Differential returns nine results and exposes its stored archive capture.

Current T7 source, generated archive and ignored runtime checkpoint remain directly in the Digital Archive Library folder. The Desktop theme folder holds one current source tree and ZIP with matching checksums and current evidence. Complete recovery packages and encryption recovery materials are kept separately in private T7 Ghost Backups. See WEBSITE-SYNCHRONIZATION.md for operation, scope, resource limits and recovery; see RELEASE-WEBSITE-SYNC-2026-11-05.md for release verification.
