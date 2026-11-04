"""Read-only public Ghost link audit. Standard library; no CMS mutations.

By default, print JSON to stdout. Files are written only with --output and/or
--snapshots. A local sitemap inventory may be passed with --inventory; otherwise
the public sitemap index is discovered. Snapshots are optional public HTML only.
This cannot inspect unpublished Ghost content, theme source or runtime-only links.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INSTITUTION = 'https://www.museumofone.art/'
ARCHIVE = 'https://archive.museumofone.art/'
LEGACY_HOST = 'museumofone.omeka.net'
HOST = r'(?:[a-z0-9-]+\.)*[a-z0-9-]*omeka[a-z0-9-]*\.[a-z]{2,}(?:\.[a-z]{2,})?'
URL_PATTERN = re.compile(r'(?:(?:https?:)?//)?' + HOST + r'(?::\d+)?(?:/[^\s<>"\'`\\]*)?(?:\?[^\s<>"\'`\\]*)?(?:\#[^\s<>"\'`\\]*)?', re.I)


def fetch(url, timeout):
    """Fetch one public HTTP resource, with bounded response size and timeout."""
    request = Request(url, headers={'User-Agent': 'MuseumOfOne-PublicLegacyLinkAudit/1.0'})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                return {'url': url, 'status': response.status, 'final_url': response.url,
                        'error': 'Response exceeds audit size limit', 'body': ''}
            charset = response.headers.get_content_charset() or 'utf-8'
            return {'url': url, 'status': response.status, 'final_url': response.url,
                    'content_type': response.headers.get_content_type(),
                    'body': raw.decode(charset, errors='replace')}
    except HTTPError as exc:
        raw = exc.read(8 * 1024 * 1024)
        return {'url': url, 'status': exc.code, 'final_url': exc.url,
                'error': 'HTTP ' + str(exc.code), 'body': raw.decode('utf-8', errors='replace')}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {'url': url, 'status': None, 'error': str(exc), 'body': ''}


def destinations(value):
    """Recognize literal, HTML-encoded and common JSON-escaped Omeka URLs."""
    text = unescape(value).replace('\\/', '/')
    text = re.sub(r'\\u00(2[fF]|3[aA])', lambda m: '/' if m[1].lower() == '2f' else ':', text)
    if '%3a' in text.lower() or '%2f' in text.lower():
        text = unquote(text)
    for match in URL_PATTERN.finditer(text):
        value = match.group(0).rstrip('.,;)')
        normalized = 'https:' + value if value.startswith('//') else value
        if not normalized.lower().startswith(('https://', 'http://')):
            normalized = 'https://' + normalized
        yield value, normalized, text[max(0, match.start()-55):match.end()+90][:350]


class References(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.script_type = None
        self.canonical = None
        self.feed(html)
        self.close()

    def add(self, value, category, element, attribute=None):
        for literal, destination, context in destinations(value):
            item = {'category': category, 'element': element,
                    'old_destination': destination, 'literal': literal,
                    'line': self.getpos()[0], 'context': context}
            if attribute:
                item['attribute'] = attribute
            self.references.append(item)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'link' and values.get('rel', '').lower() == 'canonical':
            self.canonical = values.get('href')
        if tag == 'script':
            self.script_type = values.get('type', '').lower()
        for attribute, value in attrs:
            if value is None:
                continue
            if tag == 'iframe' and attribute in ('src', 'data-src'):
                category = 'iframe'
            elif tag == 'meta' or (tag == 'link' and values.get('rel', '').lower() in ('canonical','alternate')):
                category = 'canonical/meta/structured-data'
            elif tag == 'script' or attribute.startswith('on'):
                category = 'script/text'
            else:
                category = 'nav/link'
            self.add(value, category, tag, attribute)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.script_type = None

    def handle_data(self, data):
        if self.script_type == 'application/ld+json':
            self.add(data, 'canonical/meta/structured-data', 'script')
        else:
            self.add(data, 'script/text', 'script' if self.script_type is not None else 'text')

    def handle_comment(self, data):
        self.add(data, 'script/text', 'comment')


def proposed_destination(reference, archive_root):
    parsed = urlsplit(reference['old_destination'])
    if parsed.hostname == LEGACY_HOST and parsed.path in ('', '/') and not parsed.query and not parsed.fragment:
        return {'proposed_new_destination': archive_root,
                'mapping_status': 'general_archive_entrance',
                'mapping_basis': 'Known former institutional archive root to configured independent archive root. This is not an item-level equivalence or a live-availability assertion.'}
    if parsed.hostname == LEGACY_HOST:
        return {'proposed_new_destination': None,
                'mapping_status': 'pending_legacy_item_or_route_reconciliation',
                'mapping_basis': 'No verified original item or route mapping is available. Do not silently replace with a specific new item or generic root.'}
    return {'proposed_new_destination': None,
            'mapping_status': 'manual_context_review_other_omeka_host',
            'mapping_basis': 'Other Omeka hosts may describe external collections or software; institutional equivalence is not established.'}


def sitemap_inventory(sitemap_url, timeout):
    groups, failures, pending, seen = [], [], [sitemap_url], set()
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        result = fetch(url, timeout)
        if result['status'] != 200 or not result.get('body'):
            failures.append({k:v for k,v in result.items() if k != 'body'})
            continue
        try:
            root = ET.fromstring(result['body'])
        except ET.ParseError as exc:
            failures.append({'url':url, 'error':'Invalid sitemap XML: '+str(exc)})
            continue
        urls = [el.text for parent in root for el in parent if el.tag.rsplit('}',1)[-1]=='loc' and el.text]
        if root.tag.rsplit('}',1)[-1]=='sitemapindex':
            pending.extend(urls)
        else:
            groups.append({'sitemap':url,'count':len(urls),'urls':urls})
    return groups, failures


def audit(groups, timeout=25, workers=6, archive_root=ARCHIVE, snapshots=None, sitemap_failures=None):
    urls = sorted({INSTITUTION} | {url for group in groups for url in group['urls']})
    pages, references = [], []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch,url,timeout):url for url in urls}
        for future in as_completed(futures):
            response = future.result()
            body = response.pop('body')
            parser = References(body)
            observed = parser.references
            response['references_found'] = len(observed)
            response['audit_complete'] = response.get('status')==200 and not response.get('error')
            if observed and snapshots:
                filename = sha256(response['url'].encode()).hexdigest()[:20]+'.html'
                snapshots.mkdir(parents=True, exist_ok=True)
                (snapshots/filename).write_text(body,encoding='utf-8')
                response['snapshot_sha256'] = sha256(body.encode()).hexdigest()
                response['snapshot_name'] = filename
            for item in observed:
                item.update({'source_page':response['url'], 'source_status':response['status']})
                item.update(proposed_destination(item,archive_root))
                references.append(item)
            pages.append(response)
    references.sort(key=lambda r:(r['source_page'],r['line'],r['category'],r['old_destination']))
    pages.sort(key=lambda r:r['url'])
    failures = [page for page in pages if not page['audit_complete']]
    categories = {category:sum(r['category']==category for r in references) for category in sorted({r['category'] for r in references})}
    local_home = ROOT/'dist/index.html'
    canonical = References(local_home.read_text()).canonical if local_home.is_file() else None
    local_verified = bool(canonical and urlsplit(canonical).netloc == urlsplit(archive_root).netloc and urlsplit(canonical).path in ('/','/index.html'))
    return {
        'audit_version':1,
        'audited_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'method':'Read-only public HTML fetches and HTML attribute, JSON-LD, script and text inspection. No CMS/theme changes.',
        'configured_archive_root':archive_root,
        'destination_verification':{'configured_archive_root':archive_root,
                                    'generated_homepage_verified':local_verified,
                                    'generated_homepage_canonical':canonical if local_verified else None,
                                    'public_hosting_https':'not_verified',
                                    'legacy_item_equivalence':'not_verified'},
        'scope':{'homepage':INSTITUTION,'sitemaps':groups,'unique_public_urls_requested':len(urls)},
        'summary':{'fetched_successfully':sum(page['audit_complete'] for page in pages),
                   'coverage_failures':len(failures),'sitemap_failures':len(sitemap_failures or []),
                   'pages_with_legacy_references':sum(page['references_found']>0 for page in pages),
                   'reference_occurrences':len(references),'categories':categories,
                   'unique_legacy_destinations':sorted({r['old_destination'] for r in references}),
                   'pending_item_or_route_mappings':sum(r['mapping_status']=='pending_legacy_item_or_route_reconciliation' for r in references)},
        'limitations':['Only public sitemap URLs and homepage are covered. Drafts, unlisted pages, theme source, Ghost settings and runtime-generated links require separate inspection.',
                      'An HTML reference is evidence of its presence in the response, not proof that a legacy destination works or that an item migration has been matched.',
                      'No Omeka item IDs or route mappings are inferred. Replacement requires access to the latest theme and any affected Ghost content.',
                      'Optional snapshots contain fetched public HTML; snapshot names and hashes are included without local workspace paths.'],
        'pages':pages,'coverage_failures':failures,'sitemap_failures':sitemap_failures or [],'references':references}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,help='Read an existing JSON list of sitemap/count/urls groups')
    parser.add_argument('--sitemap',default=INSTITUTION+'sitemap.xml')
    parser.add_argument('--output',type=Path,help='Explicitly write JSON report; otherwise print to stdout')
    parser.add_argument('--snapshots',type=Path,help='Explicitly save public HTML only for pages with references')
    parser.add_argument('--timeout',type=float,default=25)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--archive-root',default=ARCHIVE)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6 or not 0 < args.timeout <= 60:
        parser.error('Use 1–6 workers and a timeout greater than zero and at most 60 seconds')
    archive = urlsplit(args.archive_root)
    if archive.scheme != 'https' or not archive.netloc or archive.path not in ('','/') or archive.query or archive.fragment:
        parser.error('--archive-root must be an HTTPS origin')
    if args.inventory:
        groups = json.loads(args.inventory.read_text())
        failures = []
    else:
        groups, failures = sitemap_inventory(args.sitemap,args.timeout)
    report = audit(groups,args.timeout,args.workers,args.archive_root.rstrip('/')+'/',args.snapshots,failures)
    serialized = json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(serialized)
        print(json.dumps(report['summary'],ensure_ascii=False))
    else:
        print(serialized,end='')


if __name__=='__main__':
    main()
