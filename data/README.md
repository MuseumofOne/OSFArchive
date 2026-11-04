# Extending the catalogue

Catalogue records live in catalogue.json. Preserve each id, accession (local item number), and item-page URL once published. Add records; never regenerate item numbers from list positions. MOO-CAT-001 through MOO-CAT-016 are assigned. Next available item number: MOO-CAT-017. This does not imply recovery of original Omeka accession numbers.

Add new collections in collections.json. New collection names also render automatically if found in a record. Edit programmes.json to register a new programme and add source-backed research_programmes relationships to items. Keep programme development status separate from publication status.

The shared record fields are id, accession, title, short_title, source_title, author, creators, date, type, collection, summary, subjects, keywords, language, medium, digital_formats, extent, files, rights, license, and source provenance. Existing Zenodo records also have doi, conceptdoi, zenodo_url, institutional_url and original snapshots in source/.

Optional archival fields can record physical_medium, dimensions, duration, physical_location, provenance_history, acquisition, spatial_coverage, temporal_coverage, alternate_titles, institutional_metadata and edition_statement. Only populate them when source evidence supports them. They can remain in JSON until a corresponding presentation is needed; do not invent physical custody for a digital publication.

Type is an open vocabulary. Examples: Book, Journal article, Working paper, Dataset, Photograph, Moving image, Sound recording, Correspondence, Institutional record. Files accept name, url, size, size_label, checksum and mimetype. The current archive hosts verified unmodified PDF access copies with source checksums and reader manifests, while retaining their repository URLs. Other media remain linked to their sources unless a separately reviewed access copy/viewer is added; no audio/video transcription is implied.

`summary` and `subjects` are editorial catalogue additions. `keywords` and `source_description_html` preserve repository fields. `research_programmes` entries include title, url, source_url, status, relation and relation_label. Source snapshots should remain verbatim, not updated in place to make a newer version look like the old one. Add a new item or explicitly document a version migration.

Rebuild with `python scripts/build.py`, then validate with `python scripts/check.py`. No new UI code is required for adding records in the existing catalogue structure. New record classes may need tailored display fields or viewers.

The current build validates the local application profile and generated citation/graph exports, and derives typed research discovery plus literal PDF passages. See `../docs/METADATA_PROFILE.md` and `../docs/DISCOVERY.md` for eligibility, evidence and source-preservation requirements. Install the pinned PyMuPDF dependency before a complete build.
