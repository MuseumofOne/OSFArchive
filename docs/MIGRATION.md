# Omeka migration and legacy reconciliation

## What has been recovered

The current archive is a selected corpus of 16 public Zenodo records, corroborated with Museum of One publication pages. It includes source snapshots, edition identifiers, research relationships, individual archival descriptions and verified PDF access copies. It is not a recovered Omeka database, complete collection export or verified inventory of the expired archive.

The known former host is `https://museumofone.omeka.net`. The initial catalogue/snapshot inspection contained no structured former-service item mappings. The subsequent actual-theme inspection recovered two institutional working-paper link contexts with matching title and DOI. The former inventory is unavailable. Fresh public HTML inspection confirmed a self-canonical Ghost entrance at `/digital-archive-library/` containing an iframe for `https://museumofone.omeka.net` and direct external links. Homepage navigation also includes that entrance and a direct Omeka link. `/archive/` currently returns a Ghost 404. The inspected 1.11.10 theme is now the baseline for the prepared native 1.12.0 entrance at the same URL. Source preparation does not establish that the live CMS or former service has changed.

The current instruction is to replace every active Omeka navigation link, embed and metadata destination with the new archive. Former URLs are retained only as migration history and qualified provenance. No old records have been deleted, no Omeka redirects have been configured and no control over Omeka's canonical or robots behavior is assumed. The archive's numeric item URLs are preserved. Ghost source changes are prepared locally; live installation and account-managed content/settings changes remain held.

## Current destinations and evidence scope

The following are actual archive destinations, not asserted matches to particular Omeka items. The title and bibliographic description remain on each destination. Two rows have matching institutional link context from the verified theme; the former item pages themselves have not been recovered. Other rows remain unmatched. Exact old URLs and source hashes are retained in private migration evidence, rather than exposed as active public destinations.

| Local accession | Zenodo record ID | New archive record | Legacy item ID / URL | Reconciliation |
| --- | --- | --- | --- | --- |
| MOO-CAT-001 | 19864099 | `/items/19864099.html` | Unavailable | Unmatched |
| MOO-CAT-002 | 19864115 | `/items/19864115.html` | Unavailable | Unmatched |
| MOO-CAT-003 | 23395654 | `/items/23395654.html` | Unavailable | Unmatched |
| MOO-CAT-004 | 20383926 | `/items/20383926.html` | Unavailable | Unmatched |
| MOO-CAT-005 | 23430200 | `/items/23430200.html` | Known in private migration ledger | Institutional title/DOI link matched; former record not recovered |
| MOO-CAT-006 | 23428974 | `/items/23428974.html` | Known in private migration ledger | Institutional title/DOI link matched; former record not recovered |
| MOO-CAT-007 | 21715085 | `/items/21715085.html` | Unavailable | Unmatched |
| MOO-CAT-008 | 21241866 | `/items/21241866.html` | Unavailable | Unmatched |
| MOO-CAT-009 | 20593003 | `/items/20593003.html` | Unavailable | Unmatched |
| MOO-CAT-010 | 19963428 | `/items/19963428.html` | Unavailable | Unmatched |
| MOO-CAT-011 | 20100136 | `/items/20100136.html` | Unavailable | Unmatched |
| MOO-CAT-012 | 20100139 | `/items/20100139.html` | Unavailable | Unmatched |
| MOO-CAT-013 | 21786998 | `/items/21786998.html` | Unavailable | Unmatched |
| MOO-CAT-014 | 19863790 | `/items/19863790.html` | Unavailable | Unmatched |
| MOO-CAT-015 | 19863836 | `/items/19863836.html` | Unavailable | Unmatched |
| MOO-CAT-016 | 19863851 | `/items/19863851.html` | Unavailable | Unmatched |

Canonical origin for these routes is `https://archive.museumofone.art`. A generated route is not proof of public availability: GitHub Pages/custom-domain activation remains pending.

## Complete a mapping when evidence becomes available

1. Preserve a permitted Omeka export, public item page, archived page or institutional link as source evidence. Record its actual URL, item ID and retrieval date. Keep private exports outside the public repository until reviewed.
2. Match the work and edition using DOI, source title, creator, edition/version and publication date. A similar title alone is insufficient. Record uncertainty or a many-to-one edition relationship explicitly.
3. Store the verified original ID/URL as legacy provenance on the authoritative item, with a source reference and review note. Do not replace the new local accession with an old Omeka number or rewrite edition identifiers.
4. Confirm the new record's visible metadata, files, rights, exports, relationships and canonical destination. Reconcile any original attachments or descriptions separately; this selected corpus cannot establish that all former holdings have been recovered.
5. Replace every active Ghost Omeka link, embed and metadata destination with the appropriate new archive destination, after inspecting its context in the latest theme/content. A general link to the former Omeka root should link to `https://archive.museumofone.art/` (a specifically labelled catalogue link may use `catalogue.html`); a verified item link should resolve to its matched record. An unmatched legacy item must not be presented as a verified item mapping. Retain original URLs only in migration history/provenance, and preserve unrelated publication content. Theme source replacements are prepared; applying changes to live Ghost content/settings remains a later authorized step.
6. If the institution controls a legacy URL's server, separately authorize and test a permanent redirect to the verified destination. Otherwise document that no redirect is technically available.
7. Update this table with evidence, date, reviewer and status. Leave unsupported matches unresolved.

The public-page link inventory in `legacy-link-inventory.json` records observed active legacy references; it does not prove that every Ghost page, draft, template or metadata source has been searched. See [GHOST_INTEGRATION.md](GHOST_INTEGRATION.md) for the theme implementation handoff.

## Outstanding migration evidence

- Complete former Omeka item inventory, identifiers, files, descriptions and permissions.
- Direct former-record evidence beyond the two recovered institutional link contexts, and any omitted holdings.
- Authorized installation and account-managed content/settings changes for live destinations; the actual theme source and route snapshot are now inspected.
- Ability, if any, to configure redirects at the former host.
- Live availability and indexing of the new archive after authorized hosting activation.

Search engines decide when and whether to replace former results. Sitemap submission, accurate self-canonicals, distinctive archival description and institutional links support discovery; none guarantees ranking or removal of old Omeka results.
