import lab,shutil,os,subprocess,json
from lab import pathlib,record
lab.ROOT=pathlib.Path('/private/tmp/cdx-daemon-study');lab.ROOT.mkdir(exist_ok=True);lab.HOME=lab.ROOT/'home';lab.HOME.mkdir(exist_ok=True);lab.WORK=lab.ROOT/'workspace';lab.WORK.mkdir(exist_ok=True)
auth=lab.HOME/'auth.json'
if not auth.exists():auth.symlink_to(pathlib.Path.home()/'.codex/auth.json')
(lab.HOME/'config.toml').write_text('model_reasoning_effort="low"\n[analytics]\nenabled=false\n')
source=pathlib.Path.home()/'.codex/packages/app-server-daemon/releases/0.157.1-aarch64-apple-darwin'
dest=lab.HOME/'packages/app-server-daemon/releases'/source.name
if not dest.exists():shutil.copytree(source,dest,symlinks=True)
current=dest.parent.parent/'current'
if not current.exists():current.symlink_to(dest)
env=dict(os.environ,CODEX_HOME=str(lab.HOME));env.pop('CODEX_THREAD_ID',None)
def cli(action):
 r=subprocess.run(['codex','app-server','daemon',action],env=env,cwd=lab.WORK,capture_output=True,text=True,timeout=30)
 record('isolated_daemon_'+action,{'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});return r
s=None;a=None;b=None
try:
 assert cli('start').returncode==0
 v=cli('version');d=json.loads(v.stdout);assert d['socketPath'].startswith(str(lab.HOME))
 a=lab.Client(d['socketPath']);t=lab.start(a)['thread'];tid=t['id'];record('daemon_thread_turn',lab.turn(a,tid,'Remember DAEMON-552. Reply with it; no tools.'))
 s=lab.Server('standalone').start();b=lab.Client(s.sock)
 record('daemon_vs_standalone',{'daemonLoaded':a.ok('thread/loaded/list',{}),'standaloneLoaded':b.ok('thread/loaded/list',{}),'standaloneRead':lab.brief(b.ok('thread/read',{'threadId':tid})['thread']),'standaloneResume':b.call('thread/resume',{'threadId':tid,'excludeTurns':True})})
 a.close();a=None;cli('stop')
 record('standalone_after_daemon_stop',lab.brief(b.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']))
 record('standalone_after_daemon_recall',lab.turn(b,tid,'Reply with the earlier remembered marker; no tools.'))
finally:
 for c in [a,b]:
  if c:
   try:c.close()
   except Exception:pass
 if s:s.stop()
 cli('stop')
