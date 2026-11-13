"""Static release checks for the archive. Standard library plus Node syntax check.

This checks the built artifacts without claiming browser or external-link QA.
Run after scripts/build.py: python scripts/check.py
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from archive_design import STYLES, THEME_COLOR, VIEWPORT, asset_url, source as style_source
from publication_arrangement import collection_anchor, collection_link


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ERRORS: list[str] = []


def require(condition, message):
    if not condition:
        ERRORS.append(message)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = []
        self.links = []
        self.jsonld = []
        self.jsonld_buffer = None
        self.text = []
        self.canonical = None
        self.canonicals = []
        self.meta = {}
        self.iframes = []
        self.stylesheets = []
        self.body_classes = []
        self.cards = Counter()
        self.pending_card = None
        self.capture_section = None
        self.inventory_group = None
        self.collection_href = None
        self.collection_links = Counter()
        self.edition_links = []
        self.explorer_counts = {}
        self.count_text = None
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get('class') or '').split()
        name = self.path.name
        if name == 'website-records.html' and tag == 'section' and 'section' in classes:
            self.capture_section = attrs.get('id')
        if name == 'finding-aid.html' and tag == 'table':
            self.inventory_group = attrs.get('data-edition-group')
        if name == 'catalogue.html' and 'data-record' in attrs:
            self.pending_card = (attrs.get('data-group'), attrs.get('data-format'))
        if name in ('methodology.html', 'website-records.html'):
            if 'book-card' in classes:
                self.pending_card = ('Methodology', 'edition')
            elif 'publication-card' in classes:
                self.pending_card = (self.capture_section or 'Methodology', 'website')
        if tag == 'a':
            href = attrs.get('href', '')
            if self.pending_card:
                self.cards[(*self.pending_card, href)] += 1
                self.pending_card = None
            if self.inventory_group and href.startswith('items/'):
                self.cards[self.inventory_group, href] += 1
            if 'ax-collection-row' in classes:
                self.collection_href = href
            if attrs.get('data-ax-view') == 'catalogue':
                self.edition_links.append(href)
        if 'data-ax-full-count' in attrs:
            self.collection_links[attrs['data-ax-full-count'], attrs.get('data-count'), self.collection_href] += 1
        for key in ('data-ax-total', 'data-ax-deposit-count', 'data-ax-website-count', 'data-ax-full-count',
                    'data-capture-count', 'data-capture-total'):
            if key in attrs:
                values = self.explorer_counts.setdefault((key, attrs[key]), [])
                self.count_text = (tag, values, [])
        if tag == 'body':
            self.body_classes = (attrs.get('class') or '').split()
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.stylesheets.append(attrs.get('href'))
        if tag == 'iframe':
            self.iframes.append(attrs.get('src', ''))
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.append(attrs["name"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.jsonld_buffer = []
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
            self.canonicals.append(self.canonical)
        if tag == "meta" and attrs.get("name"):
            self.meta.setdefault(attrs['name'], []).append(attrs.get('content', ''))

    def handle_data(self, data):
        if self.count_text:
            self.count_text[2].append(data)
        if self.jsonld_buffer is not None:
            self.jsonld_buffer.append(data)
        else:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.collection_href = None
        if tag == 'article':
            self.pending_card = None
        if tag == 'section':
            self.capture_section = None
        if tag == 'table':
            self.inventory_group = None
        if self.count_text and tag == self.count_text[0]:
            _, values, parts = self.count_text
            values.append(''.join(parts).strip())
            self.count_text = None
        if tag == "script" and self.jsonld_buffer is not None:
            self.jsonld.append("".join(self.jsonld_buffer))
            self.jsonld_buffer = None


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        ERRORS.append(f"Invalid/missing JSON {path.relative_to(ROOT)}: {exc}")
        return None


def normalized_doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value or ""), flags=re.I).lower().strip()


def check_explorer_counts(pages, origin, records):
    required = ['catalogue.html', 'methodology.html', 'index.html', 'finding-aid.html', 'website-records.html']
    by_name = {name: pages.get((DIST / name).resolve()) for name in required}
    integration = DIST / 'integration/archive-explorer.hbs'
    if not all(by_name.values()) or not integration.is_file():
        require(False, 'Catalogue consistency check is missing a required page or integration partial.')
        return
    arrangement = load(DIST / 'metadata/publication-arrangement.json') or {}
    captures = arrangement.get('records', [])
    standalone = [row for row in captures if row['collection'] and not row['edition_path']]
    reference = [row for row in captures if not row['collection']]
    linked = [row for row in captures if row['edition_path']]
    editions = [(row['collection'], 'edition', f"items/{row['id']}.html") for row in records]
    inventory = Counter(editions + [(row['collection'], 'website', row['capture_path']) for row in standalone])
    require(by_name['catalogue.html'].cards == inventory,
            'Displayed catalogue records differ from the edition and capture inventories by identity, collection or format.')
    require(by_name['methodology.html'].cards == Counter({key: n for key, n in inventory.items() if key[0] == 'Methodology'}),
            'Methodology destination differs from the expected catalogue records.')
    require(by_name['finding-aid.html'].cards == Counter({(group, path): 2 for group, _, path in editions}),
            'Finding aid inventory must list each deposited edition with matching reference and title links.')

    capture_index = by_name['website-records.html']
    captures_by_section = Counter((collection_anchor(row['collection']) if row['collection'] else 'website-reference',
                                  'website', row['capture_path']) for row in captures)
    require(capture_index.cards == captures_by_section, 'Website capture index has missing, duplicate or misplaced records.')
    capture_totals = {'all': len(captures), 'standalone': len(standalone), 'linked': len(linked), 'reference': len(reference)}
    require(capture_totals['all'] == sum(n for key, n in capture_totals.items() if key != 'all'),
            'Website capture categories do not form an exhaustive breakdown.')
    expected_captures = {('data-capture-total', key): [str(n)] for key, n in capture_totals.items()}
    groups = arrangement.get('collections', {})
    for anchor in [*(collection_anchor(group) for group in groups), 'website-reference']:
        n = sum(count for (section, _, _), count in captures_by_section.items() if section == anchor)
        expected_captures['data-capture-count', anchor] = [f'{n} website {"capture" if n == 1 else "captures"}']
    require(capture_index.explorer_counts == expected_captures, 'Website capture index counts differ from the records displayed.')
    require(Counter(row['capture_path'] for row in captures) ==
            Counter(path.relative_to(DIST).as_posix() for path in (DIST / 'website').glob('web-*.html')),
            'Readable capture files differ from the classification inventory.')

    cards = Counter()
    for (group, form, _), count in inventory.items():
        cards[group, form] += count
    full = {group: cards[group, 'edition'] + cards[group, 'website'] for group in groups}
    feed = load(DIST / 'metadata/research-discovery.v2.json') or {}
    rows = feed.get('records', [])
    kinds = Counter(row['kind'] for row in rows)
    prefix = origin + '/'
    indexed_cards = Counter((row['collection'], 'edition' if row['kind'] == 'publication' else 'website',
                             row.get('archive_url', row['url']).removeprefix(prefix))
                            for row in rows if row['kind'] == 'publication' or row.get('catalogue_record') is True)
    require(indexed_cards == inventory, 'Discovery entries differ from the catalogue by identity, collection or format.')
    require(Counter((row.get('original_url'), row.get('archive_url'), row.get('collection') or None)
                    for row in rows if row['kind'] == 'website' and row.get('archive_url')) ==
            Counter((row['source_url'], prefix + row['capture_path'], row['collection']) for row in captures),
            'Website discovery destinations and collection assignments differ from the capture inventory.')
    by_url = {row['url']: row for row in rows}
    for row in linked:
        website = by_url.get(row['source_url'], {})
        edition = by_url.get(prefix + row['edition_path'], {})
        scope = row['edition_relationship']
        require(all(any(edge.get('target_id') == target.get('id') and edge.get('url') == target.get('url')
                        and edge.get('evidence_scope') == scope for edge in source.get('relationships', []))
                    for source, target in ((website, edition), (edition, website))),
                f"Missing reciprocal edition relationship or wrong evidence scope: {row['capture_path']}")
    require(feed.get('collection_counts') == full, 'Discovery collection totals do not match the catalogue cards.')

    totals = {'catalogue': sum(full.values()), 'publication': kinds['publication'],
              'website': sum(count for (_, format), count in cards.items() if format == 'website'),
              **{kind: kinds[kind] for kind in ('chapter', 'entity', 'programme')}}
    expected = {('data-ax-total', key): [str(count)] for key, count in totals.items()}
    for group, count in full.items():
        expected['data-ax-full-count', group] = [f'{count} catalogue {"record" if count == 1 else "records"} ↗']
        expected['data-ax-deposit-count', group] = [str(cards[group, 'edition'])]
        expected['data-ax-website-count', group] = [str(cards[group, 'website'])]
    for page, base in ((by_name['index.html'], ''), (Page(integration), prefix)):
        require(page.explorer_counts == expected,
                f'Explorer counts do not match the catalogue and discovery index: {page.path.relative_to(DIST)}')
        require(page.collection_links == Counter((group, str(n), base + collection_link(group)) for group, n in full.items()),
                f'Explorer collection counts link to the wrong destinations: {page.path.relative_to(DIST)}')
        require(page.edition_links and set(page.edition_links) == {base + 'finding-aid.html#inventory'},
                f'Deposited edition controls must link to the edition inventory: {page.path.relative_to(DIST)}')


def main():
    require((DIST / "index.html").is_file(), "Build output missing: run scripts/build.py first.")
    if ERRORS:
        return report()
    # The host serves this machine token as an HTML file without a page layout.
    pages = {p.resolve(): Page(p) for p in DIST.rglob("*.html")
             if p != DIST / 'google0d801b50e1695db7.html'}
    for name in STYLES:
        tracked, built = style_source(ROOT, name), DIST / 'assets' / name
        require(tracked.is_file() and built.is_file() and tracked.read_bytes() == built.read_bytes(),
                f"Style output differs from tracked source: {name}. Rebuild before publishing.")
    if ERRORS:
        return report()
    require(len(pages) >= 5, "Core pages are missing.")
    origins = {urlsplit(page.canonical).netloc for page in pages.values() if page.canonical}
    require(len(origins) == 1, f"Canonical URLs use inconsistent origins: {origins}")
    public_catalogue = load(DIST / 'metadata' / 'catalogue.json') or {}
    origin = str(public_catalogue.get('canonical_origin') or '').rstrip('/')
    require(urlsplit(origin).scheme == 'https' and bool(urlsplit(origin).netloc), 'Public catalogue lacks an absolute HTTPS canonical_origin.')
    catalogue = load(ROOT / "data" / "catalogue.json")
    records = catalogue.get("records", []) if isinstance(catalogue, dict) else catalogue or []
    check_explorer_counts(pages, origin, records)
    canonical_values = [page.canonical for page in pages.values()]
    require(len(canonical_values) == len(set(canonical_values)), 'Multiple HTML pages have the same canonical URL.')
    internal_links = 0
    for path, page in pages.items():
        relative = path.relative_to(DIST)
        style_base = (urlsplit(origin).path.rstrip('/') + '/' if relative.as_posix() == '404.html'
                      else '../' * (len(relative.parts) - 1))
        required_styles = ['archival-design.css']
        if relative.as_posix() == 'index.html':
            required_styles.append('archive-explorer.css')
        if relative.parts[0] == 'website':
            required_styles.append('website-captures.css')
        for name in required_styles:
            require(page.stylesheets.count(style_base + asset_url(ROOT, name)) == 1,
                    f"Missing or duplicated current {name}: {relative}")
        require('archive-registry' in page.body_classes, f"Missing archive design shell: {relative}")
        require(page.meta.get('viewport') == [VIEWPORT], f"Missing archive mobile viewport: {relative}")
        require(page.meta.get('theme-color') == [THEME_COLOR], f"Missing archive theme color: {relative}")
        require(bool(page.canonical), f"Missing canonical URL: {relative}")
        require(len(page.canonicals) == 1, f"Expected exactly one canonical URL: {relative}")
        require(page.canonical == origin + ('/' if relative.as_posix() == 'index.html' else '/' + relative.as_posix()), f"Canonical URL does not match the stable page path: {relative}")
        require(not page.iframes, f"Archive must operate without iframe dependencies: {relative}")
        duplicates = [k for k, v in Counter(page.ids).items() if v > 1]
        require(not duplicates, f"Duplicate fragment IDs in {relative}: {duplicates}")
        text = " ".join(page.text)
        require(not re.search(r"\blorem ipsum\b|\bTODO\b|\binsert (?:title|image|description) here\b", text, re.I), f"Unfinished placeholder copy in {relative}")
        for raw in page.jsonld:
            try:
                json.loads(raw)
            except ValueError as exc:
                ERRORS.append(f"Invalid inline JSON-LD in {relative}: {exc}")
        for link in page.links:
            parsed = urlsplit(link)
            require(parsed.hostname != 'museumofone.omeka.net', f"Active legacy Omeka destination in {relative}: {link}")
            if parsed.scheme and parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc and parsed.netloc not in origins:
                continue
            if parsed.path.startswith("/") or parsed.netloc:
                target_path = unquote(parsed.path)
                base_path = urlsplit(origin).path.rstrip('/')
                if base_path and (target_path == base_path or target_path.startswith(base_path + '/')):
                    target_path = target_path[len(base_path):]
                target = DIST / target_path.lstrip("/")
            elif not parsed.path:
                target = path
            else:
                target = path.parent / unquote(parsed.path)
            target = target.resolve()
            if target.is_dir():
                target /= "index.html"
            internal_links += 1
            require(target.is_relative_to(DIST.resolve()), f"Local link escapes dist in {relative}: {link}")
            require(target.is_file(), f"Broken local link in {relative}: {link}")
            if parsed.fragment and target in pages:
                fragment=unquote(parsed.fragment)
                page_route=re.fullmatch(r"page=(\d+)",fragment)
                if target.parent == (DIST/'read').resolve() and page_route:
                    manifest=load(DIST/'metadata/readers'/(target.stem+'.json')) or {}
                    require(1 <= int(page_route[1]) <= manifest.get('page_count',0), f"Reader page outside source extent in {relative}: {link}")
                elif target == (DIST / 'index.html').resolve() and fragment == 'ax:view=reading':
                    require('archive-explorer' in pages[target].ids, f"Missing explorer for reading list in {relative}")
                else:
                    require(fragment in pages[target].ids, f"Missing fragment in {relative}: {link}")

    parsed_json = {}
    for extension in ("*.json", "*.jsonld"):
        for path in DIST.rglob(extension):
            parsed_json[path.resolve()] = load(path)
    # Retired service references can also hide in inline structured data,
    # search feeds and scripts, rather than ordinary navigation anchors.
    # Original deposited PDFs are preservation objects and are not rewritten.
    for path in DIST.rglob('*'):
        if path.is_file() and path.suffix.lower() in {'.html', '.json', '.jsonld', '.js', '.css', '.xml', '.txt', '.bib', '.ris'}:
            require('museumofone.omeka.net' not in path.read_text(encoding='utf-8').lower(),
                    f'Retired archive hostname in public output: {path.relative_to(DIST)}')
    quality = load(DIST / 'metadata' / 'quality-report.json') or {}
    require(bool(quality.get('checks')) and all(not check.get('errors') and check.get('executed', True)
            for check in quality.get('checks', {}).values()), 'Metadata quality checks are missing, failed or unexecuted.')
    for path in DIST.rglob("*.xml"):
        try:
            ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            ERRORS.append(f"Invalid XML {path.relative_to(DIST)}: {exc}")

    require(bool(records), "Catalogue has no records.")
    ids = [str(r.get("id", "")) for r in records]
    dois = [normalized_doi(r.get("doi")) for r in records]
    require(all(ids) and len(set(ids)) == len(ids), "Record IDs are empty or duplicated.")
    require(all(dois) and len(set(dois)) == len(dois), "Record DOIs are empty or duplicated.")
    expected_items = {rid + '.html' for rid in ids}
    require({path.name for path in (DIST/'items').glob('*.html')} == expected_items,
            'Stale or missing item pages: reconcile withdrawn/renamed records explicitly before deployment.')
    feed = load(DIST / 'metadata' / 'search-index.v1.json') or {}
    require(feed.get('schema_version') == 1 and feed.get('canonical_origin') == origin, 'Integration feed version/origin mismatch.')
    feed_records = feed.get('records') or []
    require({str(r.get('id')) for r in feed_records} == set(ids) and len(feed_records) == len(ids),
            'Public search feed differs from the selected public catalogue.')
    for record in feed_records:
        require(record.get('url') == origin + '/items/' + str(record.get('id')) + '.html',
                'Search result does not link to its canonical record: ' + str(record.get('id')))
    try:
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locations = [node.text for node in ET.parse(DIST/'sitemap.xml').findall('s:url/s:loc', ns)]
        intended = {page.canonical for path, page in pages.items() if path.name != '404.html'}
        require(len(locations) == len(set(locations)) and set(locations) == intended,
                'Sitemap must contain every intended public HTML page exactly once, excluding the error page.')
        require('noindex' in ','.join(pages[(DIST/'404.html').resolve()].meta.get('robots', [])), 'Error page lacks noindex.')
    except (OSError, ET.ParseError, KeyError) as exc:
        ERRORS.append('Sitemap/error-page contract failed: ' + str(exc))
    for r in records:
        rid = str(r["id"])
        source = load(ROOT / "data" / "source" / (rid + ".json"))
        downloaded_source = DIST / "metadata" / "source" / (rid + ".json")
        require(downloaded_source.is_file(), f"Missing original source download for {rid}")
        if source:
            metadata = source.get("metadata", {})
            source_doi = source.get("doi") or metadata.get("doi")
            require(normalized_doi(source_doi) == normalized_doi(r.get("doi")), f"DOI differs from original snapshot for {rid}")
            require(str(source.get("id") or source.get("recid")) == rid, f"Snapshot ID differs from catalogue ID for {rid}")
            source_path = ROOT / "data" / "source" / (rid + ".json")
            if downloaded_source.is_file():
                require(downloaded_source.read_bytes() == source_path.read_bytes(), f"Original snapshot changed in download for {rid}")
        item_path = (DIST / "items" / (rid + ".html")).resolve()
        require(item_path in pages, f"Missing item page for {rid}")
        if item_path in pages:
            require(r.get("zenodo_url") in pages[item_path].links, f"Missing source record link for {rid}")
            require(r.get("institutional_url") in pages[item_path].links, f"Missing institutional corroboration link for {rid}")
        export = parsed_json.get((DIST / "metadata" / (rid + ".json")).resolve())
        if export:
            provenance = export.get("field_assertions") or export.get("provenance")
            require(bool(provenance), f"Metadata export lacks field assertions/provenance for {rid}")
        graph = parsed_json.get((DIST / "metadata" / (rid + ".jsonld")).resolve())
        require(isinstance(graph, dict) and isinstance(graph.get("@graph"), list), f"Missing structured entity graph for {rid}")
        if not isinstance(graph, dict) or not isinstance(graph.get("@graph"), list):
            continue
        nodes = graph["@graph"]
        node_ids = [node.get("@id") for node in nodes]
        require(len(node_ids) == len(set(node_ids)), f"Duplicate structured entity IDs for {rid}")
        edition_id = "https://doi.org/" + normalized_doi(r.get("doi"))
        edition = next((n for n in nodes if n.get("@id") == edition_id), None)
        local = next((n for n in nodes if n.get("@id", "").endswith("#catalogue-record")), None)
        require(bool(edition) and bool(local) and edition is not local, f"Publication and local record not separated for {rid}")
        if edition and local:
            about = local.get("about")
            about_refs = about if isinstance(about, list) else [about] if isinstance(about, dict) else []
            require(any(ref.get("@id") == edition_id for ref in about_refs if isinstance(ref, dict)), f"Local record points to wrong publication for {rid}")
            lookup = {node.get("@id"): node for node in nodes}
            # Additional about links must be declared local editorial terms, not
            # unsupported publication equivalences or external authority claims.
            for ref in about_refs:
                if not isinstance(ref, dict):
                    require(False, f"Invalid local about relation for {rid}")
                    continue
                if ref.get("@id") == edition_id:
                    continue
                term = lookup.get(ref.get("@id"), {})
                require(term.get("@type") == "DefinedTerm" and str(term.get("name", "")).casefold() in {str(s).casefold() for s in (r.get("subjects") or [])}, f"Unqualified additional about relation for {rid}: {ref.get('@id')}")
                termset = lookup.get(term.get("inDefinedTermSet", {}).get("@id"), {})
                require(termset.get("@type") == "DefinedTermSet" and "local editorial" in termset.get("name", "").lower(), f"Discovery term lacks its local vocabulary scope for {rid}")
            programmes = r.get("research_programmes") or []
            programme_urls = {programme.get("url") for programme in programmes}
            for ref in local.get("mentions") or []:
                if isinstance(ref,dict) and ref.get("@id") in programme_urls:
                    continue
                linked=(export or {}).get('entity_links',[])
                relation=next((link for link in linked if isinstance(ref,dict) and ref.get('@id','').endswith('/entities/'+link['id']+'.html#entity')),None)
                require(bool(relation), f"Structured context has no item-specific entity or programme relationship for {rid}")
                if relation:
                    role=relation['relation'].lower().replace(' ','_')
                    relation_node=next((node for node in nodes if node.get('@id','').endswith('#relationship-'+relation['id']+'-'+role.replace('_','-'))),{})
                    require(relation_node.get('isBasedOn',{}).get('@id')==relation.get('source_url'),f"Entity relationship lacks its source evidence for {rid}: {relation['id']}")
            allowed_evidence = {r.get("zenodo_url"), r.get("institutional_url")} | {programme.get("source_url") or programme.get("url") for programme in programmes}
            for ref in local.get("isBasedOn") or []:
                require(isinstance(ref, dict) and ref.get("@id") in allowed_evidence, f"Structured catalogue evidence has no qualified source for {rid}")
            require(edition.get("datePublished") == r.get("date"), f"Publication date changed or conflated for {rid}")
            require(local.get("description") == r.get("summary"), f"Editorial summary missing from catalogue entity for {rid}")
        family = normalized_doi(r.get("conceptdoi"))
        if family and family != normalized_doi(r.get("doi")) and edition:
            require(edition.get("exampleOfWork", {}).get("@id") == "https://doi.org/" + family, f"Version-family relation missing for {rid}")
    try:
        result = subprocess.run(["node", "--check", str(DIST / "assets" / "app.js")], capture_output=True, text=True, check=False)
        require(result.returncode == 0, "app.js syntax check failed: " + result.stderr.strip())
    except OSError as exc:
        ERRORS.append("Node syntax check unavailable: " + str(exc))
    return report(f"Checked {len(pages)} HTML pages, {internal_links} local links/fragments, {len(records)} source-qualified records, JSON/JSON-LD/XML exports, and app.js syntax.")


def report(success=""):
    if ERRORS:
        print("Static QA failed:", file=sys.stderr)
        for error in ERRORS:
            print("- " + error, file=sys.stderr)
        return 1
    print(success or "Static QA passed.")
    print("External-link availability and browser rendering were not tested.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
