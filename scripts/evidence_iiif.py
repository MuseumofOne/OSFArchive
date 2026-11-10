"""IIIF Presentation 3 exports of explicitly released selected-page facsimiles.

Full static image resources are used. This does not assert an Image API service,
complete digitization, original institutional custody, or permission beyond each
document's recorded rights. Input is the prepared public evidence projection.
"""
from __future__ import annotations
import json
from urllib.parse import urlparse

CONTEXT = 'http://iiif.io/api/presentation/3/context.json'
FORMATS = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}

def lang(value):
    return {'en': [str(value)]}

def build_iiif(payload, write, origin):
    """Write manifest JSON via write(relative_path, text); return emitted paths."""
    origin = origin.rstrip('/')
    paths, entries = [], []
    for doc in payload.get('documents', []):
        pages = [p for p in doc.get('pages', []) if p.get('image')]
        if not pages:
            continue
        rights = doc.get('rights', {})
        if rights.get('imagesApproved') is not True or rights.get('metadataApproved') is not True:
            raise ValueError('IIIF export requires explicit metadata and image release: ' + doc['id'])
        manifest_id = origin + '/iiif/' + doc['id'] + '/manifest.json'
        record_url = doc.get('recordUrl') or origin + '/evidence/' + doc['id'] + '.html'
        manifest = {
            '@context': CONTEXT, 'id': manifest_id, 'type': 'Manifest',
            'label': lang(doc['title'] + ' — selected page images'),
            'summary': lang(doc.get('coverage') or doc.get('description') or 'Selected released page images; consult the record for scope.'),
            'requiredStatement': {'label': lang('Attribution and rights'), 'value': lang(rights.get('credit', '') + ' ' + rights.get('statement', ''))},
            'homepage': [{'id': record_url, 'type': 'Text', 'label': lang('Permanent catalogue record'), 'format': 'text/html'}],
            'metadata': [
                {'label': lang(label), 'value': lang(doc[key])}
                for key, label in [('creator','Creator'),('reference','Reference'),('holdingInstitution','Holding institution'),('date','Publication date'),('documentType','Document type'),('coverage','Selection and extent')]
                if doc.get(key)
            ],
            'items': []
        }
        rights_uri = rights.get('url') or rights.get('uri')
        if rights_uri and str(rights_uri).startswith(('https://rightsstatements.org/', 'http://rightsstatements.org/', 'https://creativecommons.org/', 'http://creativecommons.org/')):
            manifest['rights'] = rights_uri
        elif 'in copyright' in str(rights.get('credit', '')).lower():
            manifest['rights'] = 'https://rightsstatements.org/vocab/InC/1.0/'
        source = doc.get('sourceUrl', '')
        if source.startswith('https://') and urlparse(source).path.lower().endswith('.pdf'):
            manifest['rendering'] = [{'id': source, 'type': 'Text', 'label': lang('Complete published PDF edition'), 'format': 'application/pdf'}]
        for page in pages:
            image = page['image']
            src = image['src']
            if src.startswith('/assets/rai-archive/'):
                src = origin + src
            if not src.startswith(origin + '/assets/rai-archive/') or '..' in urlparse(src).path:
                raise ValueError('IIIF exports only explicitly hosted release images: ' + src)
            suffix = '.' + urlparse(src).path.rsplit('.', 1)[-1].lower()
            if suffix not in FORMATS:
                raise ValueError('Unsupported IIIF image format: ' + suffix)
            width, height = image.get('width'), image.get('height')
            if type(width) is not int or type(height) is not int or width < 1 or height < 1:
                raise ValueError('IIIF canvas requires measured image dimensions')
            canvas_id = manifest_id + '#canvas-' + page['id']
            canvas = {
                'id': canvas_id, 'type': 'Canvas', 'label': lang(page.get('label') or page['id']),
                'height': height, 'width': width,
                'items': [{'id': canvas_id + '-painting', 'type': 'AnnotationPage', 'items': [{
                    'id': canvas_id + '-image', 'type': 'Annotation', 'motivation': 'painting',
                    'body': {'id': src, 'type': 'Image', 'format': FORMATS[suffix], 'height': height, 'width': width},
                    'target': canvas_id
                }]}]
            }
            text = page.get('transcription', {})
            if rights.get('transcriptionApproved') is True and text.get('text'):
                annotation = {
                    'id': canvas_id + '-text-annotation', 'type': 'Annotation',
                    'motivation': 'supplementing',
                    'label': lang('Published page text — ' + str(text.get('status') or text.get('method') or 'see catalogue for reading status')),
                    'body': {'type': 'TextualBody', 'value': text['text'], 'format': 'text/plain', 'language': text.get('language') or 'en'},
                    'target': canvas_id
                }
                canvas['annotations'] = [{'id': canvas_id + '-text', 'type': 'AnnotationPage', 'items': [annotation]}]
            manifest['items'].append(canvas)
        path = 'iiif/' + doc['id'] + '/manifest.json'
        write(path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        paths.append(path)
        entries.append({'id': manifest_id, 'type': 'Manifest', 'label': manifest['label']})
    collection = {
        '@context': CONTEXT, 'id': origin + '/iiif/collection.json', 'type': 'Collection',
        'label': lang('Museum of One — released document images'),
        'summary': lang('Approved page images with document-specific scope, original custody and rights retained in each catalogue record. Static full-image Presentation manifests; no Image API service is asserted.'),
        'items': entries
    }
    write('iiif/collection.json', json.dumps(collection, ensure_ascii=False, indent=2) + '\n')
    paths.append('iiif/collection.json')
    return paths
