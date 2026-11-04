# Shared native archive explorer — 1.12.1

Prepared locally on 5 November 2026. The live theme remains 1.12.0 until a separately authorized publication. The current Ghost header, hero, introduction, section navigation and records/access note are retained. The shared explorer replaces the former separate search/collection/shelf sections beneath the introduction.

The standalone homepage and generated Ghost partial use `scripts/explorer.py`. Their headings and destinations adapt to the host, while their catalogue, navigation, controls and design come from the same renderer. `dist/assets/archive-explorer.css` scopes the archive's paper, ink, serif typography, collection tree and item register to this component. No iframe is used.

The explorer includes collection navigation, all 16 publication records, combined title/subject/identifier/collection/year/material filters, sorting, shelf/list views, the existing typed discovery and optional PDF-passage engine, saved records, CSV export and comparison of two or three records. Its expanded view traps keyboard focus, supports Escape, restores focus and leaves the surrounding website inert only while expanded. Narrow layouts collapse the collection tree.

Record and reader links retain permanent archive destinations. Saved lists use the existing browser-local storage key. An explicit record/full-archive link adds the bounded `moo_shelf` query parameter; the destination merges it into the existing list and removes it from the visible address. This is a navigation handoff, not continuous account synchronization. URL hashes retain explorer view, filters and discovery query for Back/reload. Source PDF page hashes are preserved.

All source values are escaped; inert record data is never executed. The public catalogue still passes the existing export-eligibility gate. Identifier distinctions, source date precision and unresolved ISBN scope remain qualified. Original source snapshots, PDFs, covers, book-reader code and the Ghost header/author templates remain unchanged.

After a successful archive build, run:

```sh
python3 -B scripts/sync_ghost_explorer.py --theme '/path/to/prepared/theme'
```

The command copies the generated partial, CSS/controller/core, four original cover files, and the matching discovery/passages feeds into the theme. `docs/SHARED-EXPLORER-SYNC.json` records source/target checksums. Rebuild the theme and verify those checksums before packaging. Do not edit the generated partial or theme's shared assets independently.

Validation: archive static checks; Python and JavaScript tests including real-corpus discovery benchmarks; theme build/integrity/unit gate; GScan; CUA desktop/mobile review of actual templates with fixture helpers and the standalone archive. This revision has not been installed on the live Ghost server. The full existing automated browser release gate is not represented as executed.
