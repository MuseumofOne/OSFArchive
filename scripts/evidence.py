"""Public, source-qualified evidence descriptions and stable record pages.

Authored research pages, institutional catalogue metadata, and original archival
objects are separate material layers. Publication permission is required, not
inferred from local availability. This module never connects a private archive.
"""
from copy import deepcopy
from hashlib import sha256
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlencode
import json,re

E=lambda v:escape(str(v or ''),quote=True)
FIELDS={
 'collections': 'publication id title holdingInstitution introduction scope selection omissions arrangement relatedResearch sourceUrl rights release'.split(),
 'series':'note publication provenance id title collectionId description sourceUrl rights release'.split(),
 'documents': 'sourceReadings dossierIds publication provenance sourceLayerLabel id title collectionId seriesId creator date dates documentType holdingInstitution reference sourceUrl description coverage firstReleased revisions rights pages relatedResearch dossier dossiers claims sourceLayer materialType period language languages transcriptionStatus recordUrl readerUrl citation publicationId identifiers subjects sourceEvidence release'.split(),
 'dossiers':'publishedResearch version collectionId seriesId sourceIds claimIds status publication id title summary question limitations documentIds relatedResearch claims sources sourceUrl release updated'.split(),
}
def slug(value):
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',value):raise ValueError('Invalid evidence identifier: '+str(value))
 return value

def safe_url(value):
 p=urlsplit(str(value or ''))
 return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and not any(ord(c)<33 for c in str(value))

def public_release(value):
 return value.get('approved') is True and (value.get('reviewedForPrivacy') is True or value.get('privacyReviewed') is True) and value.get('approvedBy') and re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(value.get('approvedAt','')))

def require_public_tree(value,path='release'):
 """Explicit privacy/draft flags anywhere in a release stop public generation."""
 if isinstance(value,dict):
  for key in ('private','draft','is_draft','hidden'):
   if value.get(key) not in (None,False):raise ValueError('Nonpublic field at '+path+'.'+key)
  if value.get('visibility') not in (None,'public'):raise ValueError('Nonpublic visibility at '+path)
  if str(value.get('status','')).casefold() in {'private','draft','unpublished'}:raise ValueError('Nonpublic status at '+path)
  for key,child in value.items():require_public_tree(child,path+'.'+key)
 elif isinstance(value,list):
  for i,child in enumerate(value):require_public_tree(child,path+'['+str(i)+']')

def prepare_evidence(payload,origin):
 """Fail closed, whitelist public fields, validate all parent and media links."""
 require_public_tree(payload)
 if payload.get('schema')!=1:raise ValueError('Unsupported evidence schema')
 if not public_release(payload.get('publication') or payload.get('release',{})):raise ValueError('Evidence needs an explicit reviewed public release')
 out={'schema':1,'release':deepcopy(payload.get('publication') or payload['release']),'canonicalOrigin':origin,'scope':str(payload.get('scope',''))}
 ids=set()
 for group,fields in FIELDS.items():
  out[group]=[]
  for raw in payload.get(group,[]):
   rid=slug(raw.get('id'))
   if rid in ids:raise ValueError('Duplicate evidence identifier: '+rid)
   ids.add(rid)
   if any(raw.get(k) not in (None,False) for k in ('private','draft','hidden')) or raw.get('visibility','public')!='public':raise ValueError('Nonpublic evidence: '+rid)
   if (raw.get('publication') or raw.get('release')) and not public_release(raw.get('publication') or raw['release']):raise ValueError('Unapproved evidence: '+rid)
   record={k:deepcopy(raw[k]) for k in fields if k in raw};record['recordUrl']=origin+('/dossiers/' if group=='dossiers' else '/evidence/')+rid+'.html'
   if not record.get('title'):raise ValueError('Missing evidence title: '+rid)
   if raw.get('sourceUrl') and not safe_url(raw['sourceUrl']):raise ValueError('Invalid evidence source URL')
   out[group].append(record)
 collections={r['id'] for r in out['collections']};series={r['id']:r for r in out['series']};documents={r['id']:r for r in out['documents']}
 for record in out['series']:
  if record.get('collectionId') not in collections or not safe_url(record.get('sourceUrl')):raise ValueError('Series hierarchy lacks source evidence')
 for doc in out['documents']:
  did=doc['id'];rights=doc.get('rights',{})
  if doc.get('collectionId') not in collections:raise ValueError('Unknown evidence collection')
  if doc.get('seriesId') and (doc['seriesId'] not in series or series[doc['seriesId']]['collectionId']!=doc['collectionId']):raise ValueError('Invalid evidence series')
  if rights.get('metadataApproved') is not True or not rights.get('statement') or not safe_url(doc.get('sourceUrl')):raise ValueError('Missing public source or rights: '+did)
  if not doc.get('sourceLayer') or not doc.get('materialType'):raise ValueError('Missing material provenance: '+did)
  doc['readerUrl']='https://www.museumofone.art/relational-archival-investigation/#rai-archive?'+urlencode({'document':did})
  seen=set()
  for page in doc.get('pages',[]):
   pid=slug(page.get('id'))
   if pid in seen:raise ValueError('Duplicate page in '+did)
   seen.add(pid);page['recordUrl']=doc['recordUrl']+'?'+urlencode({'page':pid})+'#'+pid
   image=page.get('image')
   if image:
    if str(image.get('src','')).startswith('/assets/rai-archive/') and '..' not in image['src']:image['src']=origin+image['src']
    if rights.get('imagesApproved') is not True or not safe_url(image.get('src')):raise ValueError('Image has no release permission or safe URL')
    if not image.get('alt') or not all(isinstance(image.get(k),int) and image[k]>0 for k in ('width','height')):raise ValueError('Image dimensions and description required')
   for key in ('transcription','translation','commentary'):
    layer=page.get(key)
    if not layer:continue
    if rights.get({'transcription':'transcriptionApproved','translation':'translationApproved','commentary':'commentaryApproved'}[key]) is not True:raise ValueError('Reading has no release permission: '+key)
    if not layer.get('by') or not layer.get('status'):raise ValueError('Reading attribution and status required')
    for passage in layer.get('passages',[]):
     token=slug(passage.get('id'))
     if token in seen:raise ValueError('Duplicate passage/page anchor in '+did)
     seen.add(token)
     box=passage.get('bbox')
     if box and (len(box)!=4 or any(not isinstance(x,(int,float)) or x<0 or x>1 for x in box) or box[0]+box[2]>1.0001 or box[1]+box[3]>1.0001):raise ValueError('Invalid page region')
 for dossier in out['dossiers']:
  if any(d not in documents for d in dossier.get('documentIds',[])):raise ValueError('Dossier refers to unavailable document')
 out['sources']=deepcopy(payload.get('sources',[]));out['claims']=deepcopy(payload.get('claims',[]))
 claim_ids=set()
 for claim in out['claims']:
  cid=slug(claim.get('id'))
  if cid in claim_ids or cid in ids:raise ValueError('Duplicate claim identifier: '+cid)
  claim_ids.add(cid)
  for ref in claim.get('support',[])+claim.get('publishedDiscussion',[]):
   if ref.get('documentId') not in documents or ref.get('pageId') not in {p['id'] for p in documents[ref['documentId']].get('pages',[])}:raise ValueError('Claim refers to unavailable evidence page')
   doc=documents[ref['documentId']];page=next(p for p in doc['pages'] if p['id']==ref['pageId'])
   passage=ref.get('passageId')
   if passage and passage not in {x['id'] for k in ('transcription','translation','commentary') for x in (page.get(k) or {}).get('passages',[])}:raise ValueError('Claim refers to unavailable passage')
   expected={doc['sourceUrl'],page['recordUrl'],doc['recordUrl']+'#'+page['id']}
   if passage:expected.add(doc['recordUrl']+'?'+urlencode({'page':page['id'],'passage':passage})+'#'+passage)
   if ref.get('url') not in expected:raise ValueError('Claim URL does not identify its source or exact page')
   if ref.get('sourceId') and ref['sourceId']!=doc['id']:raise ValueError('Claim source and document identity disagree')
  if claim.get('sourceIds') and any(i not in documents for i in claim['sourceIds']):raise ValueError('Unknown claim source')
 for dossier in out['dossiers']:
  if any(i not in {c['id'] for c in out['claims']} for i in dossier.get('claimIds',[])):raise ValueError('Unknown dossier claim')
 out['contentVersion']=sha256(json.dumps(out,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 return out

def load_evidence(root,origin):
 p=Path(root)/'data/evidence.json'
 return prepare_evidence(json.loads(p.read_text()),origin) if p.exists() else None

def copy_evidence_assets(payload,root,out):
 """Copy only declared authorized media, validating source bytes before output."""
 for doc in (payload or {}).get('documents',[]):
  for page in doc.get('pages',[]):
   image=page.get('image')
   if not image:continue
   path=urlsplit(image['src']).path
   if not path.startswith('/assets/rai-archive/') or '..' in path:raise ValueError('Evidence image is outside its released asset directory')
   rel=path.lstrip('/');source=Path(root)/rel;target=Path(out)/rel
   data=source.read_bytes()
   if not re.fullmatch(r'[a-f0-9]{64}',image.get('sha256','')) or sha256(data).hexdigest()!=image['sha256']:raise ValueError('Evidence image checksum mismatch: '+rel)
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)

def para(text):return '<p>'+E(text).replace('\n','<br>')+'</p>' if text else ''
def links(values):return '<ul>'+''.join('<li><a href="'+E(r['url'])+'">'+E(r.get('title') or r.get('label') or r['url'])+'</a>'+para(r.get('note'))+'</li>' for r in values if safe_url(r.get('url')))+'</ul>'
def badge(text):return '<span class="pill">'+E(text)+'</span>'
def row(label,value):return '<div><dt>'+E(label)+'</dt><dd>'+E(', '.join(value) if isinstance(value,list) else value)+'</dd></div>' if value else ''
def citation(doc):return doc.get('citation') or '. '.join(str(v) for v in [doc.get('creator'),doc['title'],doc.get('date'),doc.get('holdingInstitution'),doc.get('reference'),doc['recordUrl']] if v)+'.'

def evidence_discovery(payload,origin):
 if not payload:return []
 rows=[]
 for group,level in [('collections','Collection'),('series','Series'),('documents','Document'),('dossiers','Research dossier')]:
  for r in payload[group]:
   summary=r.get('description') or r.get('summary') or r.get('introduction') or ''
   source=r.get('sourceUrl') or (r.get('relatedResearch') or r.get('publishedResearch') or [{}])[0].get('url','')
   d=dict(id='evidence:'+r['id'],kind='evidence',title=r['title'],url=r['recordUrl'],summary=summary,aliases=[],identifiers=[r['id']]+r.get('identifiers',[]),relationships=[],sources=[{'url':source,'label':r.get('sourceLayer','Source-linked research description')}] if source else [],record_level=level,source_layer=r.get('sourceLayer','Museum of One editorial description'),material_type=r.get('materialType',level),period=r.get('period',''),languages=r.get('languages') or (r['language'] if isinstance(r.get('language'),list) else [r['language']] if r.get('language') else []),transcription_status=r.get('transcriptionStatus',''),collection=r.get('collectionId',''),date=r.get('date',''),subjects=r.get('subjects',[]))
   for key in ('collectionId','seriesId'):
    if r.get(key):d['relationships'].append({'relation':'part of','target_id':'evidence:'+r[key],'url':origin+'/evidence/'+r[key]+'.html','source_url':source,'note':'Local research presentation hierarchy; not an institutional fonds attribution.'})
   if r.get('publicationId'):d['relationships'].append({'relation':'pages from published edition','target_id':'publication:'+r['publicationId'],'url':origin+'/items/'+r['publicationId']+'.html','source_url':source,'note':'Authored research document, not an institutional manuscript.'})
   text=[r['title'],summary,r.get('creator',''),r.get('reference',''),r.get('coverage',''),d['source_layer'],d['material_type'],d['period'],*d['languages'],*d['identifiers'],*d['subjects']]
   for p in r.get('pages',[]):
    text.extend([p.get('label',''),p.get('locator','')]);text.extend(p.get(k,{}).get('text','') for k in ('transcription','translation','commentary') if p.get(k))
   text.extend(c['text'] for c in payload.get('claims',[]) if c['id'] in r.get('claimIds',[]));d['search_text']=' '.join(str(t) for t in text);d['source_layer_label']=r.get('sourceLayerLabel',d['source_layer']);rows.append(d)
 for doc in payload['documents']:
  parent=next(r for r in rows if r['id']=='evidence:'+doc['id'])
  for page in doc.get('pages',[]):
   layer=page.get('transcription') or {};text=layer.get('text','')
   row=deepcopy(parent);row.update(id='evidence:'+doc['id']+':'+page['id'],record_level='Page',title=doc['title']+' — '+page.get('label',page['id']),url=doc['recordUrl']+'#'+page['id'],summary=page.get('locator',''),identifiers=[doc['id']+':'+page['id']],text=text,search_text=' '.join([doc['title'],page.get('label',''),page.get('locator',''),text]),relationships=[{'relation':'page of','target_id':parent['id'],'url':parent['url'],'source_url':doc['sourceUrl'],'note':'Exact released PDF file page or external source locator; see material and source layer.'}]);rows.append(row)
 return rows

def build_evidence_pages(payload,write,layout,origin):
 if not payload:return []
 from evidence_iiif import build_iiif
 build_iiif(payload,write,origin)
 paths=[];documents={d['id']:d for d in payload['documents']};groups={r['id']:r for group in FIELDS for r in payload[group]}
 def emit(r,level,body):
  path=('dossiers/' if level=='Research dossier' else 'evidence/')+r['id']+'.html'; schema={'@context':'https://schema.org','@type':'WebPage','@id':r['recordUrl']+'#webpage','url':r['recordUrl'],'name':r['title'],'description':r.get('description') or r.get('summary') or r.get('introduction') or r['title'],'isPartOf':{'@id':origin+'/#website'},'mainEntity':{'@type':'Collection' if level in ('Collection','Series') else 'CreativeWork','@id':r['recordUrl']+'#record','name':r['title'],'url':r['recordUrl'],'additionalType':level}}
  if r.get('sourceUrl'):schema['mainEntity']['isBasedOn']=r['sourceUrl']
  if r.get('collectionId'):schema['mainEntity']['isPartOf']={'@id':groups[r['collectionId']]['recordUrl']+'#record'}
  if r.get('pages'):schema['mainEntity']['hasPart']=[{'@type':'CreativeWork','@id':r['recordUrl']+'#'+p['id'],'name':p.get('label',p['id']),'url':p['recordUrl']} for p in r['pages']]
  head='<div class="page-head"><div class="breadcrumb"><a href="../index.html">Archive</a> / <a href="../evidence.html">Evidence records</a></div><div class="eyebrow">'+E(level)+'</div><h1>'+E(r['title'])+'</h1></div>'
  html=layout(r['title'],schema['description'],head+'<div class="evidence-record">'+body+'</div>',path,base='../',schema=schema).replace('</head>','<link rel="stylesheet" href="../assets/evidence.css"><script defer src="../assets/evidence.js"></script></head>');write(path,html);paths.append(path)
 for collection in payload['collections']+payload['series']:
  body=''.join(para(collection.get(k)) for k in ('introduction','description','scope','selection','omissions','arrangement'))
  body+='<h2>Documents available to read</h2>'+links([{'url':d['recordUrl'],'title':d['title'],'note':d.get('materialType','')} for d in documents.values() if d.get('seriesId')==collection['id'] or d.get('collectionId')==collection['id']])
  body+=links(collection.get('relatedResearch',[]));emit(collection,'Series' if collection in payload['series'] else 'Collection',body)
 for doc in documents.values():
  body='<div class="evidence-badges">'+badge({'published-paper':'Published paper','source-locator':'External source locator'}.get(doc['materialType'],doc['materialType']))+badge(doc.get('sourceLayerLabel') or doc['sourceLayer'])+'</div>'+para(doc.get('description'))+para(doc.get('coverage'))
  body+='<div class="actions"><a class="button" href="#pages">'+('Read selected pages ↓' if doc.get('materialType')=='published-paper' else 'Read source locators ↓')+'</a><a class="text-link" href="'+E(doc['sourceUrl'])+'">'+('Published PDF ↗' if doc.get('materialType')=='published-paper' else 'Institutional source ↗')+'</a></div>'
  body+='<dl class="metadata">'+''.join(row(k,doc.get(v)) for k,v in [('Creator','creator'),('Date statement','date'),('Custody / repository','holdingInstitution'),('Reference','reference'),('Language','language'),('Material','materialType'),('Reading status','transcriptionStatus')])+'</dl>'
  if doc.get('dates'):body+='<h2>Date statements</h2>'+''.join(para(str(d.get('kind','Recorded date'))+': '+str(d.get('value',''))+' — '+str(d.get('note',''))) for d in doc['dates'])
  if doc.get('sourceReadings'):
   body+='<details><summary>Limited source-field readings</summary><dl class="metadata">'+''.join(row(k,', '.join(v) if isinstance(v,list) else v) for k,v in doc['sourceReadings'].items())+'</dl>'+para(doc.get('provenance',{}).get('verification'))+'</details>'
  body+='<nav id="pages" aria-label="Pages in this document"><h2>'+('Selected pages' if doc.get('materialType')=='published-paper' else 'Source locators')+'</h2>'+links([{'url':doc['recordUrl']+'#'+p['id'],'title':p.get('label',p['id'])} for p in doc.get('pages',[])])+'</nav>'
  for page in doc.get('pages',[]):
   pid=page['id'];body+='<section class="evidence-page" id="'+E(pid)+'" tabindex="-1"><h2>'+E(page.get('label',pid))+'</h2>'+para(page.get('locator'))
   im=page.get('image')
   if im:body+='<a href="'+E(im['src'])+'"><img src="'+E(im['src'])+'" alt="'+E(im['alt'])+'" width="'+str(im['width'])+'" height="'+str(im['height'])+'" loading="lazy"></a>'
   page_number=re.fullmatch(r'pdf-page-0*(\d+)',pid)
   source_page=doc['sourceUrl'].split('#',1)[0]+'#page='+str(int(page_number.group(1))) if im and page_number else doc['sourceUrl']
   body+='<p><a href="'+E(source_page)+'">'+('Open this page in the published PDF ↗' if im else 'Consult institutional source ↗')+'</a> · <a href="'+E(page['recordUrl'])+'">Permanent page link</a></p>'
   for key,label in [('transcription','Published text / transcription'),('translation','Translation'),('commentary','Research commentary')]:
    layer=page.get(key)
    if not layer:continue
    body+='<details><summary>'+label+'</summary>'+para(' · '.join(str(layer[k]) for k in ('by','date','status') if layer.get(k)))+para(layer.get('note'))+para(layer.get('text'))
    for passage in layer.get('passages',[]):body+='<div id="'+E(passage['id'])+'" tabindex="-1"><h3>'+E(passage.get('label',passage['id']))+'</h3><blockquote>'+E(passage.get('text'))+'</blockquote>'+para(passage.get('uncertainty'))+'<p><a href="'+E(doc['recordUrl']+'?'+urlencode({'page':pid,'passage':passage['id']})+'#'+passage['id'])+'">Permanent passage link</a></p></div>'
    body+='</details>'
   body+='</section>'
  body+='<section id="provenance"><h2>Provenance and verification</h2><dl class="metadata">'+''.join(row(k,v) for k,v in doc.get('provenance',{}).items())+'</dl></section>'
  if doc['rights'].get('imagesApproved') is True and any(p.get('image') for p in doc.get('pages',[])):
   body+='<p><a href="../iiif/'+doc['id']+'/manifest.json">IIIF Presentation manifest ↗</a> · Selected published pages; no image API service.</p>'
  body+='<section id="citation"><h2>Cite this research document</h2>'+para(citation(doc))+'<p><a href="../metadata/evidence/'+doc['id']+'.csl.json">CSL JSON</a> · <a href="../metadata/evidence/'+doc['id']+'.ris">RIS</a> · <a href="../metadata/evidence/'+doc['id']+'.bib">BibTeX</a></p></section><section id="rights"><h2>Source, rights and selection</h2>'+para(doc['rights']['statement'])+para(doc['rights'].get('credit'))+links(doc.get('sourceEvidence',[]))+'</section><section id="history"><h2>Record history</h2>'+para('First release of this research presentation: '+str(doc.get('firstReleased') or payload['release']['approvedAt']))+''.join(para(' · '.join(str(r.get(k,'')) for k in ('date','by','description'))) for r in doc.get('revisions',[]))+'</section>'
  related=[{'url':d['recordUrl'],'title':d['title']} for d in payload['dossiers'] if doc['id'] in d.get('documentIds',[])];body+='<h2>Related research</h2>'+links(related+doc.get('relatedResearch',[]))
  emit(doc,'Document',body)
  doi=doc.get('reference','') if re.fullmatch(r'10\.\d{4,9}/\S+',doc.get('reference','')) else ''
  published=doc.get('provenance',{}).get('publicationDate','');year=published[:4] if re.fullmatch(r'\d{4}-\d{2}-\d{2}',published) else ''
  csl={'id':doc['recordUrl'],'type':'report' if doc.get('sourceLayer')=='research-document' else 'document','title':doc['title'],'author':[{'literal':doc.get('creator','')}],'URL':doc['recordUrl'],'note':doc.get('sourceLayerLabel',doc.get('sourceLayer',''))+'. '+doc.get('coverage','')}
  if doi:csl['DOI']=doi
  if year:csl['issued']={'date-parts':[[int(v) for v in published.split('-')]]}
  if doc.get('provenance',{}).get('version'):csl['version']=doc['provenance']['version']
  write('metadata/evidence/'+doc['id']+'.csl.json',json.dumps(csl,ensure_ascii=False,indent=2))
  write('metadata/evidence/'+doc['id']+'.ris','TY  - '+('RPRT' if doi else 'GEN')+'\nTI  - '+doc['title']+'\nAU  - '+doc.get('creator','')+'\nUR  - '+doc['recordUrl']+('\nDO  - '+doi if doi else '')+('\nPY  - '+year if year else '')+'\nN1  - '+csl['note']+'\nER  -\n')
  def bib(v):return str(v).replace('\\','\\textbackslash{}').replace('{','\\{').replace('}','\\}')
  fields={'title':doc['title'],'author':doc.get('creator',''),'url':doc['recordUrl'],'note':csl['note']}
  if doi:fields['doi']=doi
  if year:fields['year']=year
  write('metadata/evidence/'+doc['id']+'.bib','@misc{'+doc['id']+',\n'+',\n'.join('  '+k+' = {'+bib(v)+'}' for k,v in fields.items())+'\n}\n')
 for dossier in payload['dossiers']:
  body=para(dossier.get('summary'))+para(dossier.get('question'))+'<h2>Documents and source locators</h2>'+links([{'url':documents[d]['recordUrl'],'title':documents[d]['title']} for d in dossier.get('documentIds',[])])
  for claim in [c for c in payload.get('claims',[]) if c['id'] in dossier.get('claimIds',[])]:body+='<section id="'+E(claim['id'])+'"><h2>'+E(claim.get('title') or {'documentary':'Documentary finding','explanatory':'Explanation','consequential':'Historical consequence'}.get(claim.get('level'),'Research claim'))+'</h2>'+para(claim.get('statement') or claim.get('text'))+para(claim.get('status'))+links([{'url':groups[x['documentId']]['recordUrl']+'?'+urlencode({'page':x['pageId']})+'#'+x['pageId'],'title':groups[x['documentId']]['title']} for x in claim.get('support',[])])+para(claim.get('limitation'))+para(claim.get('reopening'))+para(claim.get('responsibility'))+'</section>'
  body+='<h2>Source records</h2>'+links([{'url':groups[i]['recordUrl'],'title':groups[i]['title']} for i in dossier.get('sourceIds',[])])+'<h2>Limits of the comparison</h2>'+para(dossier.get('limitations'))+links(dossier.get('relatedResearch',[]));emit(dossier,'Research dossier',body)
 body='<div class="page-head"><div class="eyebrow">Evidence records</div><h1>Read the record in context.</h1>'+para(payload.get('scope'))+'</div><h2>Collections</h2>'+links([{'url':c['recordUrl'],'title':c['title'],'note':c.get('introduction','')} for c in payload['collections']])+'<h2>Research dossiers</h2>'+links([{'url':d['recordUrl'],'title':d['title'],'note':d.get('summary','')} for d in payload['dossiers']])+'<p><a href="https://www.museumofone.art/research-programmes/">Research programmes ↗</a> · <a href="https://www.museumofone.art/relational-archival-investigation/">RAI methodology ↗</a></p>'
 write('evidence.html',layout('Evidence records','Source-qualified research documents, exact pages and documentary comparisons.',body,'evidence.html'));paths.append('evidence.html');write('metadata/rai-evidence.v1.json',json.dumps(payload,ensure_ascii=False,indent=2));return paths
