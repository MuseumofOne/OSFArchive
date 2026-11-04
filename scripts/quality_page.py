"""Readable catalogue quality report, generated from executed validation."""
from html import escape
from html.parser import HTMLParser
import json


class GraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buffer = None
        self.graphs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type') == 'application/ld+json':
            self.buffer = ''

    def handle_data(self, data):
        if self.buffer is not None:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.buffer is not None:
            self.graphs.append(json.loads(self.buffer))
            self.buffer = None


def collect_graphs(output, paths):
    graphs = []
    for path in paths:
        parser = GraphParser()
        parser.feed((output / path).read_text())
        graphs.extend(parser.graphs)
    graphs.extend(json.loads(p.read_text()) for p in (output / 'metadata').glob('*.jsonld')
                  if p.name != 'knowledge-graph.jsonld')
    return graphs


def build_quality_page(write, layout, report):
    e = lambda value: escape(str(value), quote=True)
    dims = report['dimensions']
    body = '<div class="page-head"><div class="eyebrow">Description &amp; accountability</div><h1>A record you can inspect.</h1><p>How the catalogue is checked, where its evidence comes from, and what remains unresolved.</p></div>'
    body += '<div class="quality-grid">'
    for value, label in [(report['records'], 'Publication records checked'),
                         (dims['typed_relationships'], 'Explicit relationships'),
                         (dims['relationships_with_evidence'], 'Relationships with source evidence')]:
        body += f'<div><strong>{e(value)}</strong><span>{e(label)}</span></div>'
    body += '</div><div class="reading"><h2>Checks on this build</h2><dl class="metadata">'
    for name, check in report['checks'].items():
        state = 'Passed' if check.get('executed', True) and not check['errors'] else 'Not executed' if not check.get('executed', True) else 'Requires correction'
        body += f'<div><dt>{e(name.replace("_", " ").capitalize())}</dt><dd>{state}</dd></div>'
    body += '</dl><p>These checks compare the catalogue against its description rules and generated files. They do not certify the source’s factual accuracy or guarantee inclusion in external search services.</p>'
    body += '<h2>The scope of a match</h2><p>A website can describe a work without identifying the exact deposited edition. The catalogue records that distinction.</p><dl class="metadata">'
    for name, count in dims['institutional_match_scope'].items():
        body += f'<div><dt>{e(name.replace("_", " ").capitalize())}</dt><dd>{count} records</dd></div>'
    body += '</dl><h2>Questions kept open</h2><ul>'
    body += f'<li>{len(dims["title_level_isbn_format_unresolved"])} book records retain title-level ISBNs with unresolved format allocation. These are not exported as confirmed edition ISBNs.</li>'
    body += f'<li>{len(dims["local_creation_date_unknown"])} local description creation dates remain unknown. Repository dates are recorded separately.</li>'
    body += f'<li>{dims["relationships_with_passage_locator"]} relationships have a verified PDF-page locator. Other relationships identify the supporting source without implying a checked passage.</li>'
    body += '</ul><p>Authority identifiers are published only with their recorded evidence and qualifications. See <a href="sources.html">sources and authority records</a> and <a href="policies.html">description policies</a>.</p>'
    body += '<h2>Download and inspect</h2><ul class="source-list">'
    for name, label in [('quality-report.json','Build quality report'),('metadata-profile.json','Metadata application profile'),('relationships.json','Evidence-backed relationship assertions'),('relations.json','Relationship vocabulary'),('knowledge-graph.jsonld','Connected research metadata')]:
        body += f'<li><a href="metadata/{name}">{label} ↓</a></li>'
    body += '</ul><p><a href="research-help.html">Suggest a correction or request research help ↗</a></p></div>'
    write('metadata-quality.html',layout('Catalogue quality','Inspect validation, evidence scope and unresolved catalogue questions.',body,'metadata-quality.html'))
    return ['metadata-quality.html']
