import lab
from lab import pathlib,json,record
lab.ROOT=lab.ROOT/'upgrade';lab.ROOT.mkdir(exist_ok=True);lab.HOME=lab.ROOT/'home';lab.HOME.mkdir(exist_ok=True);lab.WORK=lab.ROOT/'workspace';lab.WORK.mkdir(exist_ok=True)
(lab.HOME/'auth.json').symlink_to(pathlib.Path.home()/'.codex/auth.json') if not(lab.HOME/'auth.json').exists()else None
(lab.HOME/'config.toml').write_text('model_reasoning_effort="low"\n[analytics]\nenabled=false\n')
old='/Users/tony/.codex/packages/standalone/releases/0.156.1-aarch64-apple-darwin/bin/codex'
s=lab.Server('upgrade',old).start();c=lab.Client(s.sock)
try:
 record('upgrade_old_init',c.init);t=lab.start(c)['thread'];tid=t['id'];record('upgrade_old_thread',lab.brief(t));record('upgrade_old_turn',lab.turn(c,tid,'Remember UPGRADE-MARKER-682. Reply with that marker only, no tools.'))
 record('upgrade_old_goal',c.call('thread/goal/set',{'threadId':tid,'objective':'Upgrade test paused goal','status':'paused','tokenBudget':500}))
 c.close();s.stop();s.binary='codex';s.start();c=lab.Client(s.sock);record('upgrade_new_init',c.init)
 record('upgrade_new_read',lab.brief(c.ok('thread/read',{'threadId':tid})['thread']))
 record('upgrade_new_resume',lab.brief(c.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']))
 record('upgrade_new_recall',lab.turn(c,tid,'What marker did I ask you to remember? Reply only with it; no tools.'))
 record('upgrade_new_goal',c.ok('thread/goal/get',{'threadId':tid}))
finally:c.close();s.stop()
# structural comparison, excluding documentation strings
root=pathlib.Path('/private/tmp/codex-session-study');oldp=root/'schema-0.156.1';newp=root/'schema-experimental'
def methods(p):return{v['properties']['method']['enum'][0]for v in json.loads((p/'ClientRequest.json').read_text())['oneOf']}
changes={}
for name in ['ThreadStartParams','ThreadResumeParams','ThreadForkParams','TurnStartParams','ThreadReadResponse','ThreadListParams','ThreadQueueAddParams']:
 af=list(oldp.rglob(name+'.json'));bf=list(newp.rglob(name+'.json'))
 if not af or not bf:continue
 a=json.loads(af[0].read_text());b=json.loads(bf[0].read_text());d={}
 for k in ['properties','definitions']:
  added=sorted(set(b.get(k,{}))-set(a.get(k,{})));removed=sorted(set(a.get(k,{}))-set(b.get(k,{})))
  if added or removed:d[k]={'added':added,'removed':removed}
 if d:changes[name]=d
record('upgrade_schema_diff',{'from':'0.156.1','to':'0.157.1','addedMethods':sorted(methods(newp)-methods(oldp)),'removedMethods':sorted(methods(oldp)-methods(newp)),'selectedFieldChanges':changes})
