"""Copy one reviewed archive build into a prepared Ghost theme; never deploy."""
from pathlib import Path
import argparse,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1]

def sync(theme):
    theme=Path(theme).resolve();out=ROOT/'dist'
    assert (theme/'page-digital-archive-library.hbs').is_file(), 'Expected the Museum of One theme'
    pairs=[(out/'integration/archive-explorer.hbs',theme/'partials/generated/archive-explorer.hbs')]
    for name in ['archive-explorer.css','archive-explorer.js','archive-core.js']:
        pairs.append((out/'assets'/name,theme/'assets/archive/explorer'/name))
    for row in json.loads((out/'metadata/discovery.json').read_text()):
        if row.get('cover'):
            path=(out/row['cover']).resolve()
            assert path.is_relative_to((out/'assets').resolve()) and path.is_file(), 'Invalid public cover'
            pairs.append((path,theme/'assets/archive/explorer'/path.relative_to((out/'assets').resolve())))
    for name in ['research-discovery.v2.json','research-passages.v2.json']:
        pairs.append((out/'metadata'/name,theme/'assets/archive'/name))
    pairs.append((out/'assets/research-discovery.js',theme/'assets/js/research-discovery.js'))
    receipt=[]
    for source,target in pairs:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        assert source.read_bytes()==target.read_bytes()
        receipt.append({'source':str(source.relative_to(ROOT)),'target':str(target.relative_to(theme)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    (theme/'docs/SHARED-EXPLORER-SYNC.json').write_text(json.dumps({'generator':'scripts/sync_ghost_explorer.py','files':receipt},indent=2)+'\n')
    print('Synchronized',len(pairs),'shared files; no deployment')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--theme',type=Path,required=True);args=parser.parse_args();sync(args.theme)
