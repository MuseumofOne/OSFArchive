"""Qualified linked-context projections used by existing metadata exports."""
from urllib.parse import urlsplit

def extend_graph(graph,r,itemurl,origin):
 nodes=graph['@graph'];by_id={n.get('@id'):n for n in nodes};edition=by_id.get('https://doi.org/'+r['doi']);catalogue=by_id.get(itemurl+'#catalogue-record')
 if edition is None or catalogue is None:return graph
 contents=r.get('contents',[])
 if contents:edition.setdefault('hasPart',[]).extend({'@id':origin+'/'+p['url']+'#component'} for p in contents)
 rolemap={'author':'author','publisher':'publisher'}
 for relation in r.get('entity_links',[]):
  identity=origin+'/entities/'+relation['id']+'.html#entity'
  catalogue.setdefault('mentions',[]).append({'@id':identity})
  role=relation.get('relation','').lower().replace(' ','_')
  # Contextual subjects do not become publication contributors.
  if role in ('artist_discussed','artwork_discussed','exhibition_discussed','subject_artist','subject_artwork','subject_exhibition'):
   edition.setdefault('about',[]).append({'@id':identity})
  nodes.append({'@type':'CreativeWork','@id':itemurl+'#relationship-'+relation['id']+'-'+role.replace('_','-'),'name':role.replace('_',' '),'about':{'@id':identity},'isBasedOn':{'@id':relation.get('source_url') or r['institutional_url']},'description':relation.get('note') or 'Source-qualified contextual relationship.'})
 if r.get('controlled_subjects'):
  oldrefs=catalogue.get('about',[]);oldrefs=oldrefs if isinstance(oldrefs,list) else [oldrefs]
  catalogue['about']=[ref for ref in oldrefs if ref.get('@id')=='https://doi.org/'+r['doi']]
  termset_id=origin+'/vocabulary.html';termset={'@type':'DefinedTermSet','@id':termset_id,'name':'Museum of One local editorial discovery vocabulary','url':termset_id,'description':'Published preferred labels, definitions, alternative labels and qualified external mappings.'};nodes.append(termset)
  for term in r['controlled_subjects']:
   term_id=origin+'/'+term['url'];nodes.append({'@type':'DefinedTerm','@id':term_id,'name':term['label'],'termCode':term['id'],'description':term.get('definition',''),'inDefinedTermSet':{'@id':termset_id}});catalogue['about'].append({'@id':term_id})
  # Remove obsolete local terms whose identifiers predated the maintained register.
  graph['@graph']=[n for n in nodes if not(n.get('@type') in ('DefinedTerm','DefinedTermSet') and '/subjects.html#' in n.get('@id',''))]
 for context in r.get('pirr_references',[]):
  target=context['programme_url'];node=next((n for n in graph['@graph'] if n.get('@id')==target),None)
  if node is not None:
   node['identifier']=[{'@type':'PropertyValue','propertyID':i['scheme'],'value':i['value'],'url':i['source_url']} for i in context.get('identifiers',[])]
 return graph

def relationship_assertions(r):
 result=[]
 for link in r.get('entity_links',[]):
  result.append({'field':'entity_link:'+link['id']+':'+link['relation'],'value':link,'source_url':link.get('source_url') or r['institutional_url'],'status':'institutional_context_relationship','note':'Contextual role is source-qualified; subject artists and referenced scholars are not publication coauthors.'})
 for field,note in [('contents','Analytic descriptions were checked against headings and pagination in the deposited PDF. Component records do not have independent deposits or DOIs.'),('controlled_subjects','Local preferred terms with definitions and synonyms. External alignment is scoped in the vocabulary register.'),('genre_terms','Local resource-genre classification. Digital file format is recorded separately.'),('archival_context','Provenance records what is documented and leaves unknown custody and original order explicit.'),('description_history','Catalogue description events; these are not work publication dates or acquisition dates.')]:
  if r.get(field):result.append({'field':field,'value':r[field],'source_url':(r.get('reading_copy') or {}).get('source_url',r['zenodo_url']) if field=='contents' else r.get('description_policy_url') or r['institutional_url'],'status':'derived_file_inspection' if field=='contents' else 'editorial_description_control','note':note,'reviewed':'2026-11-04'})
 if r.get('pirr_references'):result.append({'field':'pirr_references','value':r['pirr_references'],'source_url':r['institutional_url'],'status':'institutional_context_relationship','note':'PIRR project IDs and programme references identify research records, not publication versions or independent chapter deposits.'})
 return result
