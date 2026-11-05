"""Ghost fallback holds curated public records only; website text stays live.
The same source drives archive discovery. No Ghost design or publication edits.
"""
import copy,hashlib,json
from pathlib import Path

def fallback(payload):
 p=copy.deepcopy(payload);p.pop('content_version',None)
 p['records']=[r for r in p['records'] if r['kind']!='website'];ids={r['id'] for r in p['records']}
 for r in p['records']:r['relationships']=[e for e in r['relationships'] if e['target_id'] in ids]
 if 'counts' in p:p['counts'].pop('website',None)
 p['scope']='Curated public fallback only. Website records require the live reconciled archive index.'
 p['content_version']=hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return p

def apply(theme,source):
 theme=Path(theme);source=Path(source);data=fallback(json.loads(source.read_text()))
 out=theme/'assets/archive/research-discovery.v2.json';out.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')))
 js=theme/'assets/js/research-discovery.js';s=js.read_text().replace('maxBytes:4*1024*1024','maxBytes:24*1024*1024');js.write_text(s)
 return {'records':len(data['records']),'website_records':0,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--theme',required=True,type=Path);p.add_argument('--source',default=Path('dist/metadata/research-discovery.v2.json'),type=Path);a=p.parse_args();print(json.dumps(apply(a.theme,a.source)))
