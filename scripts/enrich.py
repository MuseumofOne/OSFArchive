"""Add source-qualified discovery metadata without changing source transcriptions.

Standard library only; importing this module performs no writes. Run this file
with --write to update catalogue.json explicitly. Original snapshots are untouched.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
from pathlib import Path
import argparse
import json
import mimetypes
import re


def date_precision(value):
    """Identify supplied precision; never fill an unknown month or day."""
    text=str(value or '').strip()
    if re.fullmatch(r'\d{4}',text):return 'year'
    if re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',text):return 'month'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):
        try:date.fromisoformat(text);return 'day'
        except ValueError:return 'invalid_date'
    return 'not_supplied' if not text else 'unrecognized'


def isbn_details(value):
    normalized=re.sub(r'[^0-9Xx]','',str(value or '')).upper()
    valid=None
    if len(normalized)==13 and normalized.isdigit():
        valid=sum(int(c)*(1 if i%2==0 else 3) for i,c in enumerate(normalized))%10==0
    elif len(normalized)==10 and normalized[:9].isdigit() and (normalized[-1].isdigit() or normalized[-1]=='X'):
        valid=sum((10-i)*(10 if c=='X' else int(c)) for i,c in enumerate(normalized))%11==0
    return {'source_value':str(value),'normalized':normalized,'checksum_valid':valid,
            'note':'Checksum validation tests the identifier syntax only; it does not verify assignment, format or edition applicability.'}


def enrich_record(record, authorities=None):
    """Return a rerunnable enriched copy. Existing transcribed fields are retained."""
    r=deepcopy(record);authorities=authorities or {};source=r.get('zenodo_url');institution=r.get('institutional_url')
    r['date_precision']=date_precision(r.get('date'))
    titles=[]
    def title(value,kind,url):
        value=str(value or '').strip()
        if value and value!=r.get('title') and not any(t['title']==value for t in titles):titles.append({'title':value,'kind':kind,'source_url':url})
    title(r.get('source_title'),'repository_title',source)
    institutional=r.get('institutional_metadata') or {}
    title(institutional.get('title'),'institutional_web_record_title',institution)
    title(institutional.get('publication_title'),'institutional_publication_title',institution)
    # This variant is explicitly transcribed in the source bibliographic note.
    description=r.get('source_description_html','')
    if str(r.get('id'))=='19864099' and 'Post&ndash;Interprative Criticism: Volume I' in description:
        title('Post–Interprative Criticism: Volume I','title_page_variant_reported_by_repository',source)
        title('Foundational Essays (Collected Doctrines, Treaties, Theories, and Application)','title_page_subtitle_reported_by_repository',source)
    r['alternate_titles']=titles
    formats=[];total=0;checksums=[]
    for f in r.get('files') or []:
        mime=f.get('mimetype') or f.get('mime_type') or mimetypes.guess_type(f.get('name',''))[0] or 'application/octet-stream'
        f['mimetype']=mime
        if mime not in formats:formats.append(mime)
        if isinstance(f.get('size'),(int,float)):total+=f['size']
        checksum=f.get('checksum')
        if checksum:
            algorithm,_,value=checksum.partition(':')
            valid=bool(re.fullmatch(r'[0-9a-fA-F]{32}',value)) if algorithm.lower()=='md5' else bool(re.fullmatch(r'[0-9a-fA-F]{64}',value)) if algorithm.lower()=='sha256' else None
            checksums.append({'filename':f.get('name'),'algorithm':algorithm,'value':value,'syntax_valid':valid,'verification':'source_checksum_transcription; bytes not independently recomputed'})
    r['digital_extent']={'file_count':len(r.get('files') or []),'total_bytes':total,'formats':sorted(formats),'checksums':checksums,'source_url':source,'derivation':'File count and total bytes calculated from repository file metadata; MIME inferred from filename when absent.'}
    candidates=[]
    for value in [r.get('isbn')]+[a.get('identifier') for a in r.get('alternate_identifiers') or [] if isinstance(a,dict)]:
        if not value or not re.fullmatch(r'[0-9Xx\-\s]{10,24}',str(value)):continue
        details=isbn_details(value)
        if len(details['normalized']) not in (10,13) or any(x['source_value']==details['source_value'] for x in candidates):continue
        book=r.get('type','').lower()=='book' or r.get('collection')=='Books & volumes'
        details.update({'scope':'title_level_book_identifier; format applicability follows edition source' if book else 'source_alternate_identifier; applicability to this item unverified','source_url':source})
        candidates.append(details)
    orcid_value=str(r.get('orcid') or '').removeprefix('https://orcid.org/')
    orcid_digits=orcid_value.replace('-','')
    orcid_valid=None
    if re.fullmatch(r'\d{15}[\dX]',orcid_digits):
        total_check=0
        for digit in orcid_digits[:-1]:total_check=(total_check+int(digit))*2
        check=(12-total_check%11)%11
        orcid_valid=orcid_digits[-1]==('X' if check==10 else str(check))
    r['identifier_validation']={'orcid':{'source_value':r.get('orcid'),'checksum_valid':orcid_valid,'note':'ISO 7064 MOD 11-2 checksum only; this is not a live registry verification.'},'isbn':candidates,'doi':{'source_value':r.get('doi'),'syntax_valid':bool(re.fullmatch(r'10\.\d{4,9}/\S+',str(r.get('doi') or ''))),'note':'Syntax check only; repository snapshot supplies the identifier.'}}
    r['isbn_applicability']='title_level_book_identifier' if r.get('isbn') and (r.get('type','').lower()=='book' or r.get('collection')=='Books & volumes') else 'unverified' if r.get('isbn') else 'unverified' if candidates and not (r.get('type','').lower()=='book' or r.get('collection')=='Books & volumes') else 'not_supplied'
    if r.get('isbn_applicability')=='unverified':
        original=r.get('isbn')
        r['source_identifiers']=[x for x in (r.get('source_identifiers') or []) if x.get('scheme')!='isbn']+[{'scheme':'isbn','value':x['source_value'],'scope':x['scope'],'source_url':source} for x in candidates]
        r['isbn']=None
        r['identifier_validation']['isbn_note']='ISBNs listed in repository alternate identifiers refer to other publications or lack item-level applicability. They are retained as source identifiers, not asserted as this item’s ISBN.'
    # Only a source-declared serial relation qualifies; keywords alone do not.
    serial=None
    for relation in r.get('related_identifiers') or []:
        if str(relation.get('scheme','')).lower()=='issn' and relation.get('identifier')=='2819-7232' and relation.get('relation') in ('isPartOf','isPublishedIn'):
            auth=authorities.get('serial',{})
            serial={'title':auth.get('title','Post-interpretive criticism'),'issn':'2819-7232','url':auth.get('url','https://portal.issn.org/resource/ISSN/2819-7232'),'source_url':source,'source_relation':relation['relation'],'authority_status':auth.get('status','source_linked_serial_identifier')}
    r['serial']=serial
    if serial:
        digits=serial['issn'].replace('-','')
        total_check=sum((8-i)*(10 if c=='X' else int(c)) for i,c in enumerate(digits))
        r['identifier_validation']['issn']={'source_value':serial['issn'],'checksum_valid':total_check%11==0,'scope':'serial identifier, not item DOI or ISBN','note':'Checksum only; source relationship and authority-record status are documented separately.'}
    roles=[]
    for category,entries in [('creator',r.get('creators') or []),('contributor',r.get('source_contributors') or [])]:
        for entry in entries:
            if not isinstance(entry,dict):continue
            role=entry.get('role') or entry.get('type')
            roles.append({'name':entry.get('name'),'source_category':category,'source_role':role,'role_label':role or 'Creator (role not supplied)','affiliation_as_supplied':entry.get('affiliation'),'source_url':source})
    r['contributor_roles']=roles
    links=[];haystack=(r.get('title','')+' '+r.get('short_title','')).casefold()
    for work in authorities.get('works',[]):
        if work.get('match_title','').casefold() in haystack:
            for entry in work.get('records',[]):
                links.append({**deepcopy(entry),'scope':'Bibliographic context; inspect source for edition applicability','source_url':entry.get('evidence_url') or work.get('institutional_url') or institution})
    r['authority_links']=links
    r['metadata_profile']={'name':'Museum of One source-qualified catalogue profile','version':'2','note':'Local application profile using schema.org and qualified Dublin Core; not an archival standards certification.','source_snapshot_preserved':True}
    return r


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    data=Path(__file__).resolve().parents[1]/'data';records=json.loads((data/'catalogue.json').read_text());auth=json.loads((data/'authorities.json').read_text())
    enriched=[enrich_record(r,auth) for r in records]
    if args.write:(data/'catalogue.json').write_text(json.dumps(enriched,ensure_ascii=False,indent=2)+'\n')
    print(f'Enriched {len(enriched)} records'+(' and saved catalogue.json' if args.write else ' in memory; use --write to save')+'. Original snapshots unchanged.')

if __name__=='__main__':main()
