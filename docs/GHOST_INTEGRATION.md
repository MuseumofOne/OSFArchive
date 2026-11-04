# Ghost integration: prepared native entrance

The actual Desktop theme and T7 working copy are now available locally. The verified 1.11.10 theme ZIP is the baseline for the prepared 1.12.0 revision. The prepared source includes the native entrance, shared typed retrieval, bundled discovery/passages, public archive destinations and the current website shell. This is local preparation; it does not establish installation or public hosting.

## Preserve the current entrance and publication pages

`https://www.museumofone.art/digital-archive-library/` remains the entrance. The prepared `page-digital-archive-library.hbs` inherits `default.hbs` and replaces the retired embedded catalogue with native HTML. It includes three verified collection categories, selected deposited books, scoped search and a direct full-catalogue link. Its static content and ordinary GET form remain useful without JavaScript.

The existing header, footer, appearance preference, mobile menu and global Ghost search remain in place. Publication pages retain their own addresses, original prose and canonicals. The entrance adds no separate canonical, Open Graph or JSON-LD block; existing Ghost metadata hooks remain authoritative. The latest local route snapshot contains the ordinary page entrance and no `/archive/` alias. No route edit is required to select the slug-specific template.

## Current generated assets

| Archive build output | Bundled theme destination | Purpose |
| --- | --- | --- |
| `dist/metadata/research-discovery.v2.json` | `assets/archive/research-discovery.v2.json` | Typed publications, chapters, entities, concepts, programmes and reviewed public website records |
| `dist/metadata/research-passages.v2.json` | `assets/archive/research-passages.v2.json` | Separate literal PDF text-layer search and source-page destinations |
| `dist/assets/research-discovery.js` | `assets/js/research-discovery.js` | Shared validation, deterministic ranking, loading and scoped search controller |

Copy all three outputs from one reviewed archive build before preparing a theme candidate. Do not manually edit the bundled catalogue. The old `metadata/search-index.v1.json` contract and enhancement remain available for compatibility; the current native entrance uses v2. The existing `metadata/discovery.json` reading-list contract is unchanged.

The shared script is available to global search and mounts the scoped interface only where its container exists. Theme asset addresses use `{{asset}}`, except the unchanged reader URL that deliberately retains its previously verified CDN-bypass version.

## Native markup and failure behavior

The prepared template implements this shared contract:

```handlebars
<section data-research-discovery data-search-only="true"
  data-archive-origin="https://archive.museumofone.art"
  data-index-snapshot="{{asset 'archive/research-discovery.v2.json'}}"
  data-passages-url="{{asset 'archive/research-passages.v2.json'}}">
  <form data-discovery-form method="get"
    action="https://archive.museumofone.art/research-discovery.html">
    <label for="archive-query">Search by title, name, subject or identifier</label>
    <input id="archive-query" name="q" type="search">
    <label><input name="fulltext" type="checkbox" value="1"> Include text inside publications</label>
    <button type="submit">Search</button>
  </form>
  <p data-discovery-status role="status" aria-live="polite"></p>
  <ol data-discovery-results></ol>
  <button data-discovery-more type="button" hidden>Show more results</button>
  <a href="https://archive.museumofone.art/catalogue.html">Browse the full catalogue</a>
</section>
```

The actual template also provides record-type selection, static collection/edition links, source context and cover attribution. Empty-query browsing is suppressed on this curated entrance until a query or filter is supplied. The standalone discovery page retains its complete static browsing fallback.

The controller intercepts form submission only after a valid snapshot loads. A failed or invalid index leaves ordinary navigation intact. Passage data loads only when requested. It quotes literal extracted text, records the extraction method and rights context, and links to the PDF file page; the original PDF remains authoritative for layout and wording.

Remote refresh is not configured in the prepared theme. Once public HTTPS and actual Ghost-origin CORS are verified, a later authorized revision may add `data-index-url="https://archive.museumofone.art/metadata/research-discovery.v2.json"`. Failed remote refreshes retain a valid bundled snapshot. Requests omit credentials and have timeout/size limits.

## Global discovery

The existing public Ghost Posts/Pages query remains active. Global search adds validated archive and reviewed website snapshots, deduplicating by exact canonical URL with live Ghost records first. Snapshot website records are distinct from deposited editions and do not transfer website dates into publication dates.

The original Ghost same-origin destination restriction remains. Archive descriptive records are separately restricted to the archive origin and permitted typed paths. Website snapshot destinations are allowed only at `https://www.museumofone.art`. Index strings are rendered through text nodes. Identifier/title/name matches rank above incidental metadata; result labels identify the descriptive level and website/archive source. See [DISCOVERY.md](DISCOVERY.md) for the full schema and retrieval limits.

## Legacy destination reconciliation

The prepared theme replaces public former-library links in its colophon, research indexes and citation JSON. Two working-paper links were reconciled through their institutional title and deposited DOI, rather than equality of numeric item IDs. Unmatched item links require a labelled catalogue query and explicit uncertainty. The root entrance uses native content, its homepage card omits the retired CMS HTML copy, and archive navigation preserves the existing entrance address.

This source work does not alter live CMS bodies, navigation settings, code injection, feeds or other account-managed content. The reviewed public-source inventory and private migration evidence identify any remaining live references for a later authorized change. Do not claim a complete recovered catalogue or control over the former host's redirects.

## Design and validation evidence

The actual 1.11.10 type families, palette, widths, spacing and breakpoints were extracted into the prepared theme's `docs/ARCHIVE-DESIGN.md`. The entrance uses those tokens; the independent archive keeps its own runtime CSS.

The deterministic build, integrity checks, complete unit portion of the existing theme gate and focused archive trust/ranking/fallback tests pass locally. GScan 6.7 targeting Ghost 6 reports no errors and the same inherited versioned reader-URL warning as the original theme. The author template and corrected reader files remain byte-identical to the verified baseline; authorized guard updates are documented in the theme.

Exact Ghost 6.74 runtime setup failed because its published npm package omitted required component archives. The local visual preview compiles actual templates with Handlebars and documented fixture Ghost helpers; it does not certify actual Ghost routing. Browser review uses CUA. The existing full legacy Playwright browser gate has not been executed in this environment. Ordinary production packaging still requires its unchanged complete gate; any separate candidate archive must be labelled prepared and carry the outstanding validation limits.

A later release must validate actual Ghost rendering, existing page types, navigation/global search/mobile menu, metadata, keyboard behavior, no-JavaScript behavior, both index failures, source-page arrival, and both directions of navigation. Install only after the external hosting hold is satisfied and installation is authorized. Re-audit live legacy destinations afterward. Preserve the original ZIP and settings/routes snapshots for rollback. See [DEPLOYMENT.md](DEPLOYMENT.md) and [MIGRATION.md](MIGRATION.md).
