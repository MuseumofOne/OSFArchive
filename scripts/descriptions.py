"""Readable source-description transcription without executing repository HTML."""
from html import escape
from html.parser import HTMLParser
import re


class _SourceText(HTMLParser):
    blocks = {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote'}

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = None
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored = tag
        elif not self.ignored and tag in self.blocks:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.ignored == tag:
            self.ignored = None
        elif not self.ignored and tag in self.blocks:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def repository_description_text(record):
    source = record.get("source_description_html") or ""
    return re.sub(r"\s+", " ", "".join(_SourceText(source).parts)).strip()


def repository_description_html(record):
    source = record.get('source_description_html')
    if not source:
        return ''
    lines = [re.sub(r'\s+', ' ', line).strip() for line in ''.join(_SourceText(source).parts).splitlines()]
    paragraphs = ''.join('<p>' + escape(line) + '</p>' for line in lines if line)
    if not paragraphs:
        return ''
    return ('<section class="item-section" id="repository-description"><h2>Repository description</h2>'
            '<span class="source-label">Description supplied to Zenodo · Source transcription</span>'
            '<p>This description belongs to the saved repository metadata and may discuss other editions or dates. '
            'The bibliographic record above identifies the selected deposited edition. Formatting is converted to readable text.</p>'
            '<div class="repository-description-text">' + paragraphs + '</div></section>')
