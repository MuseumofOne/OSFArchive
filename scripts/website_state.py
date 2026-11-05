"""Checkpoint only encrypted recoveries and opaque mappings on a separate branch.
Uses the repository's existing GitHub Actions checkout authentication. Never
commits source content, changes main, or creates a PAT/admin credential.
"""
from pathlib import Path
import argparse,json,os,re,subprocess,tempfile
from website_sync import atomic
BRANCH='website-sync-state'
def git(*args,env=None,data=None,check=True):
 r=subprocess.run(['git',*args],input=data,capture_output=True,env=env)
 if check and r.returncode:raise RuntimeError('Git checkpoint operation failed: '+args[0])
 return r

def pull(work):
 probe=git('ls-remote','origin','refs/heads/'+BRANCH).stdout.decode().split()
 if not probe:atomic(work/'baseline-ref',b'');return
 sha=probe[0];git('fetch','--no-tags','origin','refs/heads/'+BRANCH)
 for row in git('ls-tree','-rz',sha).stdout.split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t');name=name.decode()
  if not (name=='state.json' or re.fullmatch(r'vault/(?:[a-f0-9]{24}|assets)/[a-f0-9]{64}\.json',name)):raise RuntimeError('Unexpected checkpoint path')
  atomic(work/name,git('cat-file','blob',meta.split()[2].decode()).stdout)
 atomic(work/'baseline-ref',sha.encode())

def push(work):
 old=(work/'baseline-ref').read_text().strip() if (work/'baseline-ref').exists() else ''
 env={**os.environ,'GIT_AUTHOR_NAME':'Museum of One archive synchronization','GIT_AUTHOR_EMAIL':'research@museumofone.art','GIT_COMMITTER_NAME':'Museum of One archive synchronization','GIT_COMMITTER_EMAIL':'research@museumofone.art'}
 with tempfile.TemporaryDirectory(prefix='moo-sync-index-') as tmp:
  env['GIT_INDEX_FILE']=str(Path(tmp)/'index')
  git('read-tree',old if old else '--empty',env=env)
  files=[work/'state.json']+sorted((work/'vault').rglob('*.json'))
  for p in files:
   if not p.is_file():continue
   name=p.relative_to(work).as_posix();blob=git('hash-object','-w',str(p)).stdout.decode().strip()
   git('update-index','--add','--cacheinfo','100644,'+blob+','+name,env=env)
  tree=git('write-tree',env=env).stdout.decode().strip()
  if old and git('rev-parse',old+'^{tree}').stdout.decode().strip()==tree:print('Encrypted checkpoint unchanged');return
  args=['commit-tree',tree]+(['-p',old] if old else [])
  commit=git(*args,env=env,data=b'Reconcile encrypted website capture checkpoint\n').stdout.decode().strip()
  git('push','origin',commit+':refs/heads/'+BRANCH,'--force-with-lease=refs/heads/'+BRANCH+':'+old)
  atomic(work/'baseline-ref',commit.encode());print('Encrypted checkpoint saved')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['pull','push']);p.add_argument('--work',type=Path,default=Path('.sync-work'));a=p.parse_args();a.work.mkdir(exist_ok=True);globals()[a.action](a.work.resolve())
