#!/usr/bin/env python3
"""Local-only archive operations. Never discovers, merges or publishes copies."""
from pathlib import Path
import argparse, hashlib, http.server, json, os, platform, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
IDENTITY = 'museum-of-one-public-archive-v1'
SKIP = {'.git', '.sync-work', '.venv', '__pycache__', '.DS_Store', '.local', 'audit', '.pytest_cache'}
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def inventory(root, skip=SKIP):
    rows={}
    for base, dirs, files in os.walk(root):
        
        if Path(base)==root/'.sync-work':
            dirs[:]=['public'] if (Path(base)/'public').exists() else []
            files=[]
        else: dirs[:]=sorted(d for d in dirs if d not in skip or (Path(base)==root and d=='.sync-work'))
        for d in dirs:
            if (Path(base)/d).is_symlink(): raise ValueError('Refusing directory symlink')
        for name in sorted(files):
            p=Path(base)/name
            if name in skip or name.endswith('.pyc'): continue
            if p.is_symlink(): raise ValueError('Refusing symlink: '+str(p))
            rows[p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':digest(p)}
    return rows

def identity(root):
    if json.loads((root/'config/project-identity.json').read_text())['id'] != IDENTITY: raise ValueError('Wrong project identity')
    for f in ('scripts/build.py','data/catalogue.json','dist/index.html','.git'):
        if not (root/f).exists(): raise ValueError('Incomplete project: '+f)
def outside(p, root):
    if p.resolve().is_relative_to(root.resolve()): raise ValueError('Private manifests/config/backups must be outside the public project')
def desktop():
    # macOS Foundation returns the user-configured Desktop, including iCloud redirection.
    if sys.platform=='darwin':
        r=subprocess.run(['swift','-e','import Foundation; print(FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask)[0].path)'],capture_output=True,text=True)
        if r.returncode: raise ValueError('Desktop discovery failed; set MOO_DESKTOP explicitly')
        return Path(r.stdout.strip())
    return Path.home()/'Desktop'
def config(path):
    p=Path(path).expanduser() if path else Path.home()/'.config/museum-of-one/local.json'
    outside(p,ROOT)
    return json.loads(p.read_text()) if p.exists() else {}
def verify(root, manifest, expected):
    if digest(manifest)!=expected: raise ValueError('Untrusted or changed manifest; obtain its SHA-256 independently')
    m=json.loads(manifest.read_text())
    if m['id']!=IDENTITY: raise ValueError('Wrong manifest identity')
    if subprocess.run(['git','fsck','--full','--no-reflogs'],cwd=root,capture_output=True).returncode: raise ValueError('Git object integrity check failed')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=m['git_head']: raise ValueError('Git HEAD differs from trusted mirror manifest')
    actual=inventory(root)
    if actual!=m['files']:
        changed=sorted(k for k in set(actual)|set(m['files']) if actual.get(k)!=m['files'].get(k))
        raise ValueError('Mirror differs; do not merge or refresh blindly: '+', '.join(changed[:30]))
    return m

def run(args,root,env=None): subprocess.run(args,cwd=root,env=env,check=True)
def theme_verify(folder):
    m=json.loads((folder/'FILE-CHECKSUMS.json').read_text())
    for rel,h in m['theme'].items():
        p=folder/'theme'/rel
        if not p.resolve().is_relative_to((folder/'theme').resolve()) or digest(p)!=h: raise ValueError('Theme source mismatch: '+rel)
    actual={k:v['sha256'] for k,v in inventory(folder/'theme',{'.git','node_modules','__pycache__','.DS_Store','.venv'}).items()}
    if actual!=m['theme']: raise ValueError('Theme source file set differs')
    zips=list(folder.glob('*.zip'))
    if len(zips)!=1: raise ValueError('Expected exactly one authoritative theme ZIP')
    import zipfile
    with zipfile.ZipFile(zips[0]) as z:
        if z.testzip(): raise ValueError('Theme ZIP CRC failure')
        names={n for n in z.namelist() if not n.endswith('/')}
        if names!=set(m['theme']): raise ValueError('ZIP/source file sets differ')
        for n in names:
            if hashlib.sha256(z.read(n)).hexdigest()!=m['theme'][n]: raise ValueError('ZIP differs: '+n)
    if zips[0].name not in (folder/'LATEST.txt').read_text(): raise ValueError('LATEST does not identify ZIP')
    if digest(zips[0]) not in (folder/'SHA256SUMS.txt').read_text(): raise ValueError('ZIP checksum receipt differs')
    return zips[0]

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,required=True);a.add_argument('--config');a.add_argument('--manifest',type=Path);a.add_argument('--sha256');a.add_argument('--output',type=Path);a.add_argument('--theme-folder',type=Path);a.add_argument('--bundle',type=Path);a.add_argument('--port',type=int,default=8765)
    a.add_argument('command',choices=['doctor','seal','verify','setup','check','build','preview','theme-verify','theme-save','theme-restore'])
    x=a.parse_args();root=x.root.expanduser().resolve()
    if root!=ROOT: raise ValueError('Use scripts/portable.py from the explicitly selected root; refusing another copy')
    identity(root);c=config(x.config)
    if x.command=='doctor':
        print(json.dumps({'system':platform.system(),'macOS':platform.mac_ver()[0],'architecture':platform.machine(),'python':sys.version.split()[0],'python_executable':sys.executable,'home':str(Path.home()),'Desktop':str(Path(os.environ['MOO_DESKTOP'])) if os.environ.get('MOO_DESKTOP') else str(desktop()),'git':shutil.which('git'),'node':shutil.which('node'),'credentials_required_for_public_work':False},indent=2));return
    if x.command=='seal':
        if not x.output: raise ValueError('Explicit private --output required')
        outside(x.output,root)
        if x.output.exists(): raise ValueError('Manifest exists; choose a new reviewed baseline, never overwrite')
        x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps({'id':IDENTITY,'scope':'Public source, PDFs, tools, dist; excludes Git objects, private runtime, environments and audit; not a full backup','git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'files':inventory(root)},indent=2)+'\n');print(digest(x.output));return
    if not x.manifest or not x.sha256: raise ValueError('--manifest and independently trusted --sha256 required')
    verify(root,x.manifest,x.sha256)
    if x.command=='verify': print('Identity and complete public content/release manifest match. Git/private runtime excluded.');return
    if x.command=='setup':
        if sys.version_info<(3,12): raise ValueError('Install Python >=3.12 on this Mac first')
        if not shutil.which('node'): raise ValueError('Install Node >=22 (theme target 22) first')
        if int(subprocess.check_output(['node','--version'],text=True).strip().lstrip('v').split('.')[0])<22: raise ValueError('Node >=22 required')
        target=root/'.venv'
        if target.exists(): raise ValueError('Existing environment: rename it explicitly; copied environments must not be reused')
        run([sys.executable,'-m','venv',str(target)],root);run([str(target/'bin/python'),'-m','pip','install','-r','requirements-local.lock'],root)
        (target/'portable-environment.json').write_text(json.dumps({'root':str(root),'machine':platform.node(),'architecture':platform.machine()}));return
    if x.command in ('check','build'):
        py=root/'.venv/bin/python'
        if not py.exists(): raise ValueError('Run setup to create this machine’s environment')
        stamp=root/'.venv/portable-environment.json'
        if not stamp.exists() or json.loads(stamp.read_text())!={'root':str(root),'machine':platform.node(),'architecture':platform.machine()}: raise ValueError('Copied or unverified environment: recreate with setup on this machine/root')
        env={k:v for k,v in os.environ.items() if not k.startswith(('GHOST_','GITHUB_','MOO_')) and k not in ('SITE_ORIGIN','WEBSITE_SYNC_DIR','GH_TOKEN')};env['SITE_ORIGIN']='https://archive.museumofone.art'
        if x.command=='build': run([str(py),'scripts/build.py'],root,env)
        run([str(py),'scripts/check.py'],root,env);run([str(py),'-m','unittest','discover','-s','tests','-p','test_*.py'],root,env)
        run(['node','--test',*map(str,sorted((root/'tests').glob('*.test.cjs')))],root,env);return
    if x.command=='preview':
        class PublicOnly(http.server.SimpleHTTPRequestHandler):
            def translate_path(self,path):
                p=Path(super().translate_path(path)).resolve()
                if not p.is_relative_to((root/'dist').resolve()): return str(root/'dist/__refused__')
                return str(p)
        from functools import partial
        print(f'Local preview only: http://127.0.0.1:{x.port}',flush=True)
        http.server.ThreadingHTTPServer(('127.0.0.1',x.port),partial(PublicOnly,directory=str(root/'dist'))).serve_forever();return
    if x.command=='theme-restore':
        if not x.bundle or not x.output or x.output.exists(): raise ValueError('Select --bundle and a nonexistent --output Desktop folder; never overwrites')
        outside(x.bundle,root);outside(x.output,root)
        receipt=json.loads((x.bundle/'PORTABLE-THEME.json').read_text())
        # Authority hash must be configured separately, never inferred from modification time.
        if digest(x.bundle/'PORTABLE-THEME.json')!=c.get('theme_receipt_sha256'): raise ValueError('Configure independently trusted theme_receipt_sha256 first')
        if inventory(x.bundle,SKIP|{'PORTABLE-THEME.json'})!=receipt['files']: raise ValueError('Theme recovery bundle changed')
        theme_verify(x.bundle);shutil.copytree(x.bundle,x.output);os.chmod(x.output,0o700);theme_verify(x.output);print('Restored verified source/ZIP/evidence without installation.');return
    folder=x.theme_folder or (Path(c['theme_folder']) if c.get('theme_folder') else None)
    if not folder: folder=(Path(os.environ['MOO_DESKTOP']) if os.environ.get('MOO_DESKTOP') else desktop())/c.get('theme_directory','Ghost Theme - 2026-11-05')
    folder=folder.expanduser().resolve();outside(folder,root);z=theme_verify(folder)
    if x.command=='theme-save':
        if not x.output or x.output.exists(): raise ValueError('Explicit nonexistent private --output bundle required')
        outside(x.output,root);shutil.copytree(folder,x.output);os.chmod(x.output,0o700);theme_verify(x.output)
        receipt={'version':json.loads((folder/'theme/package.json').read_text())['version'],'zip_sha256':digest(z),'files':inventory(x.output,SKIP|{'PORTABLE-THEME.json'})}
        (x.output/'PORTABLE-THEME.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Trusted theme_receipt_sha256:',digest(x.output/'PORTABLE-THEME.json'))
    else: print('Verified theme:',z.name,digest(z))
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as e: sys.exit('PORTABILITY: '+str(e))
