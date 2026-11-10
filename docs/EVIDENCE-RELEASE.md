# Releasing a reviewed evidence selection

This workflow adds an explicitly selected public dossier to the archive. It does not search research folders, infer permission from a downloaded file, or publish automatically. The first release contains Dorian Vale’s already published research pages and external institutional source locators. Those pages are genuine research documents; they are not facsimiles of the historical institutional records discussed in them.

The authoritative inputs are `data/evidence.json` and the selected derivatives in `assets/rai-archive/`. The archive build generates the shared public JSON, permanent record pages, citations, discovery entries and IIIF Presentation manifests from these inputs. Do not edit those generated outputs independently.

## 1. Make a small, reviewed selection

Use the explicitly selected, verified archive project on this Mac or drive. Follow `OPEN-ON-EITHER-MAC.md` when changing machines; a recent modification time does not identify the authoritative copy.

Keep three things distinct:

- **Source or preservation master:** the complete, unchanged original file, its provenance and checksum. Existing author-owned publication PDFs remain in the archive’s established publication workflow. Do not replace an edition or DOI file to correct a dossier description.
- **Public surrogate:** a deliberately selected page image derived from that source. Record the PDF file page, printed page or folio separately, the rendering process, dimensions and checksum. A photograph of a manuscript is a surrogate of that manuscript, not the physical object.
- **Reading layer:** extracted text, transcription, translation or commentary, explicitly labelled with its kind, author, date and review status. Extracted PDF text is not a new verified transcription of an institutional manuscript. Preserve uncertain readings and omissions; never invent missing language.

Private correspondence, complete local research folders, unpublished manuscripts, access credentials, source captures held only for checking, rights correspondence and internal QA notes stay outside the public repository. Maintain private permission evidence separately; put only a concise, non-sensitive release basis in public provenance. Review the *entire* selected image, including adjacent text, faces, annotations and embedded metadata. A checksum proves file identity, not rights, accuracy or completeness.

For an institutional source with no image reuse permission, release a **locator-only record**: exact source URL, repository/reference, page or catalogue-field locator, retrieval date and checksum of the checked response, limited factual readings and verification limits. Set `image`, `transcription`, `translation` and `commentary` to `null` when those layers are not released. Leave `imagesApproved` false. Public download access is not permission to redistribute.

## 2. Prepare the public metadata

Use the existing `data/evidence.json` as the field model. A release can contain only new or intentionally revised records; referenced existing collection, series, source and dossier records are resolved against the archive during validation. Give every collection, series, document, page, passage and claim a stable identifier. Keep local research groupings distinct from an institution’s fonds or series.

The release needs a `publication` object with `approved: true`, `privacyReviewed: true`, the actual reviewer in `approvedBy`, and the real `YYYY-MM-DD` review date in `approvedAt`. These fields record a completed review; do not populate them automatically. A document also needs:

- Explicit `sourceLayer`, `sourceLayerLabel` and `materialType`; a source URL and exact page/field locators.
- `provenance.sourceFileSHA256`, plus a statement of verification or derivation (`verification` or `rendering`). State what was checked and what remains unverified.
- `rights.metadataApproved` and a rights statement. Images and each reading layer have separate approval flags. Existing copyright stays intact; approval to display does not imply an open licence.
- For every image: `sha256`, positive pixel dimensions, descriptive `alt`, `privacyReviewed: true` and `metadataReviewed: true` after those checks. This importer supports selected PNG, JPEG and WebP derivatives.
- For every reading layer: an explicit `kind`, `by`, `status`, and permission for that layer. Selected passage text must end at a complete passage or explicitly mark its continuation. Regions use normalized `[x, y, width, height]` coordinates within the whole page.

Separate production, inscription, exhibition, acquisition, publication, catalogue-state, retrieval and local-release dates. A catalogue year is not automatically an object’s historical date; a retrieval time is not an amendment date. Retain disagreement between sources. A later catalogue description or the author’s own supplement is not automatically an independent witness.

Claims must point to exact available document/page IDs (and passage IDs when used). Distinguish documentary observations, proposed relationships and unresolved explanations. Record what could reopen the conclusion. English and Hangul names may aid discovery when they identify material actually present; do not add unrelated artists or infer authority identifiers.

## 3. Make an isolated release folder

Create a temporary folder **outside the public repository** containing only:

```text
reviewed-release/
  evidence.json
  release.json
  assets/rai-archive/exact-selected-page-v1.png
```

Copy only the selected images referenced by this `evidence.json`. The importer rejects unlisted files, symlinks, traversal paths, external image URLs, known private-field markers and private filesystem paths. It never opens other research folders. These checks supplement human privacy review; they cannot detect every sensitive statement inside an image or paragraph.

`release.json` records the bytes you reviewed, rather than granting permission:

```json
{
  "schema": 1,
  "evidenceFile": "evidence.json",
  "evidenceSha256": "SHA-256 of the exact evidence.json bytes",
  "assets": [
    {
      "path": "assets/rai-archive/exact-selected-page-v1.png",
      "sha256": "SHA-256 of the exact image bytes",
      "bytes": 123456,
      "width": 1323,
      "height": 1871
    }
  ]
}
```

The numbers above are examples, not defaults. Image dimensions must match the stored file. Limits are 200 images, 25 MiB per image, 512 MiB per release and 20 MiB per JSON file. A locator-only release has an empty `assets` array.

After creating and reviewing `evidence.json` and copying only its selected images, this local command can write the manifest. Run it from the verified archive project and replace the example release path. It reads only the explicitly referenced images and does not mark anything approved:

```sh
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
from import_evidence_release import read_json, images, checked_path, verify_asset, digest, encoded
folder = Path('/absolute/path/to/reviewed-release')
payload, raw = read_json(folder / 'evidence.json')
assets = []
for relative, expected in images(payload, 'https://archive.museumofone.art').items():
    path = checked_path(folder, relative)
    size = verify_asset(path, expected)
    assets.append(dict(path=relative, bytes=size, **expected))
manifest = dict(schema=1, evidenceFile='evidence.json', evidenceSha256=digest(raw), assets=assets)
(folder / 'release.json').write_bytes(encoded(manifest))
PY
```

## 4. Validate without changing the archive

From the verified archive project:

```sh
python3 scripts/import_evidence_release.py /absolute/path/to/reviewed-release \
  --root /absolute/path/to/verified-archive --dry-run
```

Dry-run is also the default. It validates the reviewed publication gate using the same `prepare_evidence` function as the archive build, all record references, rights, provenance, image checksums and dimensions. It reports the resulting record counts, changed IDs, new assets and metadata hashes. It makes no archive, backup or staging changes. A failure must be resolved in the reviewed release; do not bypass a rights or privacy check simply to complete an import.

## 5. Import locally with a private backup

After inspecting the dry-run result:

```sh
python3 scripts/import_evidence_release.py /absolute/path/to/reviewed-release \
  --root /absolute/path/to/verified-archive \
  --apply --backup-dir /absolute/path/to/private-evidence-backups
```

The backup folder must be separate from the public repository and release folder. Each import retains the exact previous metadata, its referenced page images, the release manifest and a receipt there. Treat that backup as private.

The importer stages and checks the new files, installs new image names without overwriting existing files, then atomically replaces `data/evidence.json` **last**. This is a manifest-last commit, not a whole-directory atomic swap. Before the commit, the previous metadata still points to its unchanged assets. On a handled failure before commit, newly installed images are removed. A sudden process termination can leave an unreferenced image or `.evidence-import.lock`; inspect the receipt and previous metadata before recovery. Do not delete another running importer’s lock. Run one import/build at a time.

This operation does not rebuild, push, deploy, upload to Ghost or alter the original PDFs. It must not be described as publication.

## 6. Correct a released record without erasing its history

Unchanged IDs may be included again. A changed existing record is rejected unless the release carries an explicitly reviewed `migration` and the command adds `--allow-reviewed-migration`.

The migration has its own completed approval fields, a concrete `reason`, `expectedExistingSha256` for the exact current `data/evidence.json`, and `replaces`: an exact list of changed `{group, id, expectedSha256}` entries. Per-record hashes use `record_hash(record)` from the importer (canonical sorted JSON), not the raw file hash. Generate these from the freshly verified baseline; stale hashes fail.

For a document revision, retain `firstReleased`, every existing page and passage ID, and all earlier `revisions`. Append an attributed, dated description matching the migration approval date. Use a **new versioned image filename** if the surrogate changes. Existing image paths are immutable even during a migration. The previous bytes and record state remain in the private backup; deliberately add a separate public version record when readers need to compare historical versions. Never silently reassign an existing identifier to a different source, rewrite an original edition, remove a prior finding or treat a corrected extraction as a change to the historical object.

## 7. Rebuild, inspect and publish through the normal workflow

After local import, run these from the verified archive project (not concurrently with another build):

```sh
python3 -m unittest discover -s tests -p 'test_evidence*.py'
python3 scripts/build.py
```

Inspect the generated `dist/evidence/` and `dist/dossiers/` pages, shared `dist/metadata/rai-evidence.v1.json`, citations, discovery links and selected images. Check the reader at desktop and mobile sizes: source labels, page numbers, readable images, selected regions, layer toggles, comparison, permanent links and copyright. IIIF Presentation manifests describe the released images; they do not assert an IIIF Image API or permission for unreleased originals.

Use the project’s established reviewed deployment process only when publication is authorized. After deployment, verify the actual public record, page/passage links, source URLs, image bytes, reading labels and search results. A successful local import or build is not evidence that the public archive changed. Keep the private receipt so a later correction can be tied to the exact released bytes.
