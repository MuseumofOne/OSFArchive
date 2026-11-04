# Metadata validation and unresolved authority questions

Review date: 4 November 2026. Scope: the 16 selected publication records in `dist/metadata/catalogue.json`, compared with the corresponding preserved `data/source/{id}.json` snapshots, current reader manifests and existing source-qualified authority notes. This is a local source-agreement review, not a fresh query to every external registry or a claim that the expired Omeka collection has been recovered.

## What the evidence establishes

| Status | Meaning in this report |
| --- | --- |
| Verified against preserved source | The current value agrees with the identified saved source. This verifies transcription/agreement, not the source's ultimate factual correctness or present online state. |
| Byte-verified | Current file bytes were hashed and agree with the recorded repository checksum or local reader-manifest digest. This does not establish authorship, ownership or agency registration. |
| Syntax/checksum checked | The identifier has the expected structure or check digit. This does not verify assignment to the work, edition or person. |
| Institution-provided / corroborated | Museum of One supplies contextual authorship, publication, relationship or identifier information; the recorded evidence and any independent access limitations remain attached. |
| Unresolved / scope-limited | Conflicting values, inaccessible authorities or work-level-only matches prevent a stronger conclusion. The field is withheld, separately scoped or explicitly qualified. |

Direct JSON comparisons passed for all 16 records for each of these eight fields: numeric source ID, version DOI, deposited publication date, preserved source title, original creator array, repository creation timestamp, repository modification timestamp and source resource-type object (128 field comparisons). The normalized public types retain the repository classifications: four books, two working papers, eight journal articles and two datasets. Dates retain four year-only values, one month-only value and eleven day-precision values.

File-name, source URL, byte-length and repository-checksum tuples agree between the catalogue and saved source for all 16 files. The current local PDF bytes also match all 16 source MD5 values and all 16 SHA-256 values in `data/readers.json`, recomputed during this review. Source licence IDs remain distinct: 14 CC BY 4.0 records and two CC BY-NC-ND 4.0 working papers. These deposit-level licence statements do not extinguish third-party material rights.

## Record-by-record review

“DOI agrees” below means exact agreement with the saved Zenodo snapshot, not a fresh DOI resolution or registration-agency audit. “No qualified serial” means no supported normalized ISSN relationship is asserted; a transcribed journal title may still be preserved separately in `source_journal`.

| Record ID / accession | Type | Deposited date | Precision | DOI: agrees with snapshot | ISBN applicability | Normalized serial source status |
| --- | --- | --- | --- | --- | --- | --- |
| 19864099 / MOO-CAT-001 | Book | 2026-04 | Month | `10.5281/zenodo.19864099` | `978-1-06-982030-3`: title-level book identifier; format/agency scope unresolved | No qualified serial |
| 19864115 / MOO-CAT-002 | Book | 2025 | Year | `10.5281/zenodo.19864115` | `978-1-06-982031-0`: title-level book identifier; format/agency scope unresolved | Source `isPartOf` ISSN 2819-7232 |
| 23395654 / MOO-CAT-003 | Book | 2026-05-18 | Day | `10.5281/zenodo.23395654` | `978-1-06-982033-4`: title-level book identifier; Google Books context recorded | No qualified serial |
| 20383926 / MOO-CAT-004 | Book | 2026-05-09 | Day | `10.5281/zenodo.20383926` | `978-1-06-982034-1`: title-level book identifier; institutional source | No qualified serial |
| 23430200 / MOO-CAT-005 | Working paper | 2026-10-17 | Day | `10.5281/zenodo.23430200` | Not supplied | No qualified serial |
| 23428974 / MOO-CAT-006 | Working paper | 2026-10-17 | Day | `10.5281/zenodo.23428974` | Not supplied | No qualified serial |
| 21715085 / MOO-CAT-007 | Journal article | 2026-07-31 | Day | `10.5281/zenodo.21715085` | Not supplied | No qualified serial |
| 21241866 / MOO-CAT-008 | Journal article | 2026-07-07 | Day | `10.5281/zenodo.21241866` | Not supplied | No qualified serial |
| 20593003 / MOO-CAT-009 | Journal article | 2026-06-08 | Day | `10.5281/zenodo.20593003` | Not supplied | No qualified serial |
| 19963428 / MOO-CAT-010 | Journal article | 2025-05-01 | Day | `10.5281/zenodo.19963428` | Not supplied | No qualified serial |
| 20100136 / MOO-CAT-011 | Dataset | 2026-02-09 | Day | `10.5281/zenodo.20100136` | No asserted item ISBN; three source alternatives retained as unverified | No qualified serial |
| 20100139 / MOO-CAT-012 | Dataset | 2026-02-09 | Day | `10.5281/zenodo.20100139` | Not supplied | No qualified serial |
| 21786998 / MOO-CAT-013 | Journal article | 2025-12-31 | Day | `10.5281/zenodo.21786998` | Not supplied | Source `isPublishedIn` ISSN 2819-7232 |
| 19863790 / MOO-CAT-014 | Journal article | 2026 | Year | `10.5281/zenodo.19863790` | Not supplied | No qualified serial |
| 19863836 / MOO-CAT-015 | Journal article | 2026 | Year | `10.5281/zenodo.19863836` | Not supplied | No qualified serial |
| 19863851 / MOO-CAT-016 | Journal article | 2026 | Year | `10.5281/zenodo.19863851` | Not supplied | No qualified serial |

All four asserted book ISBNs pass their check-digit validation. The three alternate ISBN strings retained for 20100136 also pass checksum validation; that does not make them identifiers of the manual. Normalized serial links are limited to the two source-declared relationships above. The authority dataset records ISSN Portal metadata observed in a search index, with direct access obstructed by bot protection. Do not promote this to an unqualified fresh registry verification or apply the ISSN to every article based on keywords.

## Corrections and discrepancies retained

- **19864099, first volume:** the current publisher citation title and the unchanged PDF's reported title-page variant, “Post–Interprative Criticism: Volume I,” are distinguished. The source reports a copyright-page first publication in 2025 and a first edition. `2026-04` is the selected repository release v5's publication-date field, not proof of a new book edition. The printed ISBN remains qualified; a new agency assignment has not been independently verified. The catalogue does not silently repair the source PDF or replace its title-page transcription.
- **20100136, operational manual:** an inapplicable inherited book ISBN was cleared from the normalized item ISBN. Three source alternatives, `978-1-06-982030-3`, `978-1-06-982031-0` and `978-1-06-982032-7`, remain in `source_identifiers` with unverified applicability. The source classifies this manual as a dataset; that classification is retained alongside its editorial methodological context. Its source journal/volume statement alone is not treated as a verified item ISBN or qualified ISSN relationship.
- **20100139, coverage variants:** the source title uses 1980–2025; the deposited filename uses 1981–2025. Both survive as source evidence. No coverage range has been silently harmonized or asserted as settled without examining and documenting the underlying dataset scope.
- **19863790, 19863836 and 19863851:** the institutional pages corroborate the work through title, authorship and context, but their saved HTML does not explicitly link these selected edition DOIs. These are work-level matches, not verified exact-edition links. Source descriptions cite 2025/earlier DOIs while the selected records' publication fields say 2026. Both contexts remain qualified; a website date is not substituted for the deposited date.
- **21715085 and 21241866:** institutional web records respectively show 29 July versus the selected deposit's 31 July 2026, and 6 July versus 7 July 2026. These are preserved as distinct publication-record dates.
- **23395654 and 20383926:** a programme/publication register may link a version-family DOI. The archive keeps the selected edition DOI and concept-family DOI separate. For 23395654 the institutional second-edition description is preserved; an Arabic translation in development is not presented as a deposited translated edition.
- **Creator statements:** several sources include organizational or URL-form creator entries. The original arrays are preserved. The public bibliographic-author statement is institutionally corroborated and distinguished from the raw source creator list; it does not invent contributor roles or affiliations.
- **Source journal spelling:** 20593003 supplies “Journal of Post-Interpretive Critiism”; other records supply “Journal of Post-Interpretive Criticism” or “Museum of One.” Original source journal fields remain evidence, rather than proof that every item belongs to the normalized serial or permission to silently standardize a source title.

## Dates and local description lifecycle

All 16 local `record_created` values remain unknown and absent. The review did not invent a historical creation date from a deposit, publication, source review or build timestamp.

All 16 current `record_modified` values are `2026-11-04`, derived from documented local description-history events. `record_modified_provenance` identifies those event IDs and declares the derivation. These values date the description, not the work or edition. The source-review date is also 4 November 2026 but represents a separate event; coincident dates do not make their meanings interchangeable.

Repository `source_created` and `source_modified` exactly preserve the saved Zenodo timestamps. In qualified DC application-profile version2 they are explicitly repository provenance (`cat:repositoryRecordCreated` and `cat:repositoryRecordModified`), while local record dates use `cat:recordCreated`/`cat:recordModified`; `dcterms:issued` retains the deposited publication-date field. This replaces the misleading generic work `created`/`modified` mapping. Original-work dates remain absent unless supported separately. A reported first-edition statement is retained as evidence, not automatically converted into a new structured original-work date.

## External authority limits and manual review queue

`data/authorities.json` records the evidence status. A focused official ORCID API check on 4 November 2026 is recorded below; other unresolved assignments have not been upgraded without evidence.

1. **ISBN edition/format allocation:** reconcile the original ISBN Canada assignment and PDF/EPUB scope for the first two volumes. Inspect item-level evidence for all ISBNs before describing them as independently agency-verified. Google Books context for *Threads of Sand* is useful corroboration, not universal edition identity.
2. **Author ISNI conflict:** the sources contain `0000000528819744` and `0000000537155247`. Neither is asserted as independently verified or merged with `sameAs`. Both official identifier URLs returned HTTP 403 in the current recheck; no assignment decision was made. Obtain the corresponding authoritative records before resolving the conflict.
3. **ORCID:** the official public person API for `0009-0004-7737-5094` returned HTTP 200 on 4 November 2026, with credit name Dorian Vale and the Museum of One website URL. The matching public registry profile has now been inspected. These profile fields are user-supplied and do not independently verify biography, affiliation or endorsement. A minimal observation receipt is retained in `data/source/authority-review-2026-11-04.json`.
4. **Library and Archives Canada:** the general institutional link and website archive index have different scopes. No item-level LAC holdings record or particular website capture is verified. Do not assert legal deposit, custody or preservation of every book by LAC.
5. **OCLC:** the source authority notes withhold `1412305300` and `1412468296` as verified item identifiers because WorldCat title matches were not independently inspectable. Their institutional assertion is not a verified holdings record.
6. **Other repositories/catalogues:** E-LIS, Google Books, AfricArXiv, BiblioBoard, Knowledge Commons and PhilArchive links carry their recorded access and edition limitations. E-LIS's publication-state inconsistency remains visible; restricted catalogue shells do not establish inspected editions. These links confer no accreditation or peer-review claim.
7. **Institutional and research identities:** no verified ROR identifier is supplied; a pending registration is not a registration. PIRR references retain the published project/programme scope. Local subjects and Getty genre alignments retain their own mapping qualifications, without claiming blanket LCSH or Getty assignment.

## Current export validation

The shared citation model, CSL-JSON/BibTeX/RIS generation, applicable Scholar tags, visible citations and qualified JSON-LD/DC projections are now implemented. The application-profile gate checks source consistency, identifier scope, explicit dates, stable identities, relationship targets and actual on-disk export agreement; the builder runs it before output and again against generated files. The quality page/report publish the measured result, warnings and review queue. See [METADATA_PROFILE.md](METADATA_PROFILE.md). Local profile/export checks pass in the current build; the final release report records the exact complete tests and environment limits. This does not establish independent registry agreement or standards certification.

Structured data, citation tags and strong metadata support discovery but do not guarantee Google Scholar inclusion, search indexing or rankings. Live HTTPS, external link availability, actual browser behavior and Ghost installation require their own evidence.
