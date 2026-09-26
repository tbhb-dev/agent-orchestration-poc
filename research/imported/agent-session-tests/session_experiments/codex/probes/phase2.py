from lab import *
s=Server().start();c=Client(s.sock);ids=json.loads((ROOT/'ids.json').read_text());tid=ids['main']
try:
 record('restart_before_resume',brief(c.ok('thread/read',{'threadId':tid})['thread']))
 r=c.ok('thread/resume',{'threadId':tid,'excludeTurns':True,'sandbox':'read-only','approvalPolicy':'on-request'})
 record('resume_settings',{'thread':brief(r['thread']),'approvalPolicy':r.get('approvalPolicy'),'sandbox':r.get('sandbox')})
 record('resume_recall',turn(c,tid,'What exact marker did I ask you to remember? Reply only with it, without tools.'))
 turns=c.ok('thread/turns/list',{'threadId':tid,'limit':50,'itemsView':'full','sortDirection':'asc'})
 record('turns_after_resume',{'ids':[x['id']for x in turns['data']],'count':len(turns['data'])})
 first=turns['data'][0]['id'];second=turns['data'][1]['id']
 (WORK/'shared.txt').write_text('BEFORE_FORK')
 f=c.ok('thread/fork',{'threadId':tid,'lastTurnId':first,'excludeTurns':True})['thread'];fid=f['id'];ids['fork']=fid
 record('fork',brief(f));record('fork_turn_count',len(c.ok('thread/turns/list',{'threadId':fid,'limit':50})['data']))
 record('fork_recall',turn(c,fid,'Reply only with the exact marker from the earlier user message; no tools.'))
 (WORK/'shared.txt').write_text('AFTER_FORK_SHARED')
 record('fork_filesystem',{'sameCwd':f['cwd']==str(WORK),'sharedFile':(pathlib.Path(f['cwd'])/'shared.txt').read_text(),'sourceTurnCount':len(c.ok('thread/turns/list',{'threadId':tid,'limit':50})['data'])})
 record('set_paused_goal',c.call('thread/goal/set',{'threadId':tid,'objective':'Disposable lifecycle test objective','status':'paused','tokenBudget':1000}))
 record('revert',c.call('thread/revert',{'threadId':tid,'beforeTurnId':second}))
 record('revert_effects',{'turnIds':[x['id']for x in c.ok('thread/turns/list',{'threadId':tid,'limit':50})['data']],'goal':c.ok('thread/goal/get',{'threadId':tid}),'file':(WORK/'shared.txt').read_text(),'forkStillReadable':'result'in c.call('thread/read',{'threadId':fid})})
 # archive and rename only disposable fork
 record('rename',c.call('thread/name/set',{'threadId':fid,'name':'Disposable Codex lifecycle fork'}))
 record('archive_loaded_idle',c.call('thread/archive',{'threadId':fid}))
 record('archive_enumeration',{'active':[x['id']for x in c.ok('thread/list',{'sourceKinds':['appServer'],'limit':100})['data']],'archived':[x['id']for x in c.ok('thread/list',{'sourceKinds':['appServer'],'archived':True,'limit':100})['data']]})
 record('unarchive',c.call('thread/unarchive',{'threadId':fid}))
 record('delete_fork',c.call('thread/delete',{'threadId':fid}))
 record('deleted_fork_read',c.call('thread/read',{'threadId':fid}))
 e=start(c,ephemeral=True)['thread'];ids['ephemeral']=e['id'];record('ephemeral_start',brief(e))
 record('ephemeral_turn',turn(c,e['id'],'Reply exactly EPHEMERAL-TEST; no tools.'))
 record('ephemeral_inventory',{'loaded':c.ok('thread/loaded/list',{}),'stored':[x['id']for x in c.ok('thread/list',{'sourceKinds':['appServer'],'limit':100})['data']]})
 (ROOT/'ids.json').write_text(json.dumps(ids));c.close();s.stop();s.start();c=Client(s.sock)
 record('ephemeral_after_restart',c.call('thread/read',{'threadId':ids['ephemeral']}))
 # exact persistent traces of ephemeral id in lab only; report filenames, not content
 matches=[]
 for p in HOME.rglob('*'):
  if p.is_file() and not p.is_symlink() and p.stat().st_size<20000000:
   if ids['ephemeral'].encode() in p.read_bytes():matches.append(str(p.relative_to(HOME)))
 record('ephemeral_residual_files',matches)
finally:
 c.close();s.stop()
