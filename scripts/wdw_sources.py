"""A scoped, source-qualified supplement to the published WDW working paper.

This collection is independent of the RAI reader implementation. Institutional
records are links, not locally reproduced archival objects or inferred holdings.
"""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re


PATH = 'evidence/when-documentation-becomes-the-work.html'
DATA_PATH = 'metadata/when-documentation-becomes-the-work-sources.json'


def e(value):
    return escape(str(value or ''), quote=True)


def source_collection_link():
    return ('<section class="reading" aria-labelledby="research-source-collections">'
            '<h2 id="research-source-collections">Research source collections</h2>'
            f'<p><a href="{PATH}">When Documentation Becomes the Work: evidence and source access ↗</a></p>'
            '<p>Inspect the records behind the Rim Dong Sik, Kim Kulim and Sung Neung Kyung cases, '
            'with access conditions, source-specific limitations and related scholarship. '
            'This annotated selection supplements the published working paper.</p></section>')


def _validate(data, root):
    seen = set()
    for row in data['records'] + data['abstractOnly'] + data['relatedPublications']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row['id']) or row['id'] in seen:
            raise ValueError('Invalid or duplicate WDW source identifier')
        seen.add(row['id'])
        if not row['sourceUrl'].startswith('https://'):
            raise ValueError('WDW source requires a public HTTPS locator')
        if row.get('hostedUrl'):
            expected = 'https://archive.museumofone.art/assets/documents/'
            if row.get('hostingDecision') != 'host-unmodified-with-attribution' or not row.get('licenceUrl') or not row.get('attribution'):
                raise ValueError('Hosted WDW source lacks its recorded reuse conditions')
            if not row['hostedUrl'].startswith(expected):
                raise ValueError('Unexpected hosted WDW file location')
            file = root / 'dist/assets/documents' / row['hostedUrl'].removeprefix(expected)
            if sha256(file.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Hosted WDW source differs from the verified unmodified file')
        elif row.get('hostingDecision') not in (None, 'link-only'):
            raise ValueError('Unexpected WDW hosting decision')


def _source(row, origin):
    body = f'<article class="wdw-source" id="{e(row["id"])}">'
    body += f'<p class="eyebrow">{e(row["type"])} · {e(row["accessStatus"])}</p>'
    body += f'<h3>{e(row["title"])}</h3><p class="wdw-byline">{e(row["creator"])} · {e(row["date"])}</p>'
    body += f'<p class="wdw-locator">{e(row["locator"])}</p>'
    body += f'<p><strong>What this source supports.</strong> {e(row["annotation"])}</p>'
    body += f'<p><strong>Limit.</strong> {e(row["limitations"])}</p>'
    body += '<div class="actions">'
    if row.get('hostedUrl'):
        path = '../' + row['hostedUrl'].split('archive.museumofone.art/', 1)[1]
        body += f'<a class="button" href="{e(path)}">Read the complete article · PDF ↗</a>'
        body += f'<a class="text-link" href="{e(row["publisherUrl"])}">Original publication ↗</a>'
    else:
        body += f'<a class="text-link" href="{e(row["sourceUrl"])}">Open the original source ↗</a>'
        if row.get('downloadUrl') and row['downloadUrl'] != row['sourceUrl']:
            body += f'<a class="text-link" href="{e(row["downloadUrl"])}">Institutional PDF ↗</a>'
    body += f'<a class="wdw-permalink" href="#{e(row["id"])}" aria-label="Permanent link to {e(row["title"])}">Source link #</a></div>'
    body += f'<details class="wdw-rights"><summary>Rights and access</summary><p>{e(row["rights"])}</p>'
    if row.get('licenceUrl'):
        body += f'<p>{e(row["attribution"])}</p><p><a href="{e(row["licenceUrl"])}">{e(row["licence"])} ↗</a></p>'
        body += '<p>The complete publisher PDF is supplied without alteration, free of charge, for noncommercial access. '
        body += 'No endorsement is implied and no additional restrictions are imposed on the licensed material. '
        body += 'Separate rights in any credited third-party content remain applicable.</p>'
        body += f'<p class="wdw-checksum">SHA-256: {e(row["sha256"])}</p>'
    body += '</details></article>'
    return body


CSS = '''.wdw-intro{max-width:780px;font-size:16px;line-height:1.8}.wdw-intro p{margin:0 0 18px}.wdw-nav{display:flex;gap:12px 24px;flex-wrap:wrap;border-block:1px solid var(--line);padding:22px 0;margin:34px 0 50px;font:12px/1.8 var(--sans)}.wdw-group{margin:0 0 56px;max-width:960px;scroll-margin-top:30px}.wdw-group>h2{font:42px/1.2 var(--serif);font-weight:400;margin:0 0 25px}.wdw-source{padding:30px 0;border-top:1px solid var(--line);scroll-margin-top:28px}.wdw-source h3{font:27px/1.35 var(--serif);font-weight:400;max-width:850px;margin:12px 0 14px;overflow-wrap:anywhere;word-break:normal}.wdw-source p{font-size:14px;line-height:1.85;max-width:830px;margin:12px 0}.wdw-source .eyebrow{font:10px/1.8 var(--mono);letter-spacing:.6px;color:var(--wine)}.wdw-source .wdw-byline{font-size:13px}.wdw-source .wdw-locator{font-size:12px;color:var(--muted)}.wdw-source .actions{margin:20px 0 14px;gap:15px 24px}.wdw-source .actions a{font-size:12px}.wdw-permalink{color:var(--muted)}.wdw-rights{max-width:830px;color:var(--muted)}.wdw-rights summary{cursor:pointer;font-size:12px;line-height:1.8}.wdw-rights p{font-size:12px}.wdw-checksum{overflow-wrap:anywhere}.wdw-note{padding:24px 28px;background:var(--white);border-left:2px solid var(--wine);max-width:890px;margin:24px 0 35px}.wdw-note p{font-size:14px;line-height:1.85}.wdw-related{padding:22px 0;border-top:1px solid var(--line)}.wdw-related h3{font:25px/1.35 var(--serif);font-weight:400;margin:0 0 12px}.wdw-related p{font-size:14px;line-height:1.85}.wdw-footer{margin:40px 0 70px;font-size:12px;line-height:1.8;color:var(--muted)}@media(max-width:600px){.wdw-group>h2{font-size:34px}.wdw-source h3{font-size:24px}.wdw-note{padding:15px 18px}.wdw-nav{gap:9px 20px}.wdw-source .actions{align-items:flex-start}}'''


def build_wdw_sources(write, layout, origin, root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    data = json.loads((root / 'data/wdw-evidence.json').read_text())
    _validate(data, root)
    page_url = origin + '/' + PATH
    body = '<div class="page-head"><div class="breadcrumb"><a href="../index.html">Library</a> / <a href="../sources.html">Sources</a> / Working-paper evidence</div>'
    body += '<div class="eyebrow">Korean experimental art / Research source collection</div><h1>When documentation<br>becomes the work.</h1>'
    body += '<p>Evidence and source access</p></div><div class="wdw-intro">'
    body += f'<p>{e(data["description"])}</p><p>{e(data["facsimilePolicy"])}</p>'
    body += '<p>These annotations identify what each consulted source can establish and what remains open. '
    body += f'The collection supplements <a href="https://doi.org/{e(data["publication"]["relatedPaperDoi"])}">version {e(data["publication"]["relatedPaperVersion"])} of the published working paper</a> '
    body += f'and preserves access to <a href="https://doi.org/{e(data["publication"]["previousPaperDoi"])}">version 1.0</a>; '
    body += 'it does not replace either deposited edition or indicate journal acceptance.</p></div>'
    groups = [('rim-dong-sik', 'Rim Dong Sik'), ('kim-kulim', 'Kim Kulim'), ('sung-neung-kyung', 'Sung Neung Kyung'), ('comparative-scholarship', 'Comparative scholarship')]
    body += '<nav class="wdw-nav" aria-label="Source collection sections">'
    for anchor, name in groups + [('access-gaps', 'Articles consulted by abstract'), ('related-research', 'Working paper and RAI')]:
        body += f'<a href="#{anchor}">{e(name)}</a>'
    body += '</nav>'
    for anchor, name in groups:
        rows = [r for r in data['records'] if r.get('relatedCase', ['Comparative scholarship'])[0] == name]
        body += f'<section class="wdw-group" id="{anchor}"><h2>{e(name)}</h2>'
        body += ''.join(_source(row, origin) for row in rows) + '</section>'
    body += '<section class="wdw-group" id="access-gaps"><h2>Articles consulted by abstract</h2>'
    body += '<div class="wdw-note"><p>The following three final journal articles have been identified, but their complete texts were not obtained from lawful free sources. '
    body += 'Their abstracts establish the existence and stated scope of prior scholarship. Full arguments, notes and object histories remain to be checked. '
    body += 'The separately listed 2024 conference paper is a distinct text.</p></div>'
    body += ''.join(_source(row, origin) for row in data['abstractOnly']) + '</section>'
    body += '<section class="wdw-group" id="related-research"><h2>The working paper and RAI</h2>'
    body += f'<div class="wdw-note"><p>{e(data["overlapDisclosure"])}</p></div>'
    for row in data['relatedPublications']:
        body += f'<article class="wdw-related" id="{e(row["id"])}"><h3><a href="{e(row["sourceUrl"])}">{e(row["title"])} ↗</a></h3>'
        body += f'<p>{e(row["creator"])} · {e(row["date"])} · Version {e(row.get("version", "1.0"))}</p><p>{e(row["relation"])}</p></article>'
    body += '</section><div class="wdw-footer">'
    body += f'<p>Collection prepared {e(data["preparedDate"])} · {len(data["records"])} source records · {len(data["abstractOnly"])} abstract-only access records. '
    body += 'Dates and titles in source records retain their stated roles; a reporting year is not automatically a publication or event date.</p>'
    body += f'<p><a href="../{DATA_PATH}" download>Download the annotated source register · JSON ↓</a> · '
    body += '<a href="../sources.html">All sources and authority records ↗</a></p></div>'
    nodes = []
    for row in data['records'] + data['abstractOnly']:
        nodes.append({'@type': 'CreativeWork', '@id': page_url + '#' + row['id'],
                      'name': 'Source annotation: ' + row['title'], 'url': page_url + '#' + row['id'],
                      'creator': {'@type': 'Organization', 'name': 'Museum of One'},
                      'datePublished': data['preparedDate'],
                      'description': row['annotation'] + ' Limitation: ' + row['limitations'],
                      'isBasedOn': {'@type': 'CreativeWork', '@id': row['sourceUrl'], 'url': row['sourceUrl'],
                                    'name': row['title'], 'creator': row['creator'], 'inLanguage': row.get('language', '')}})
    graph = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': page_url, 'url': page_url, 'name': data['title'],
         'description': data['description'], 'datePublished': data['preparedDate'], 'inLanguage': 'en',
         'about': {'@id': 'https://doi.org/' + data['publication']['relatedPaperDoi']},
         'keywords': ['Korean experimental art', 'Korean art history', 'performance documentation', 'photography', 'provenance'],
         'hasPart': [{'@id': n['@id']} for n in nodes],
         'isPartOf': {'@type': 'WebSite', '@id': origin + '/#website', 'name': 'Museum of One Digital Archive Library', 'url': origin + '/'}},
        *nodes]}
    html = layout(data['title'], data['description'], body, PATH, '../', schema=graph)
    html = html.replace('</head>', '<link rel="stylesheet" href="../assets/wdw-evidence.css"></head>')
    write(PATH, html)
    write('assets/wdw-evidence.css', CSS)
    write(DATA_PATH, json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return [PATH]
