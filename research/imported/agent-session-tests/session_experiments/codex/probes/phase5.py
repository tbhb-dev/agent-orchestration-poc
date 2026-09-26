from lab import *
GATE={'type':'function','name':'lab_gate','description':'Pause this disposable experiment until the controller responds.','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}
def hold(c):
 t=start(c,dynamicTools=[GATE])['thread'];p=len(c.messages)
 r=c.ok('turn/start',{'threadId':t['id'],'input':[{'type':'text','text':'Call lab_gate once, then reply DONE. No other tools.'}]})
 req=c.wait(lambda x:x.get('method')=='item/tool/call'and x.get('params',{}).get('threadId')==t['id'],60,p)
 return t,r['turn']['id'],req
s=Server().start();c=Client(s.sock)
try:
 t,uid,req=hold(c);tid=t['id'];inp=lambda text:[{'type':'text','text':'Reply only '+text+'; do not call any tools.'}]
 a=c.ok('thread/queue/add',{'threadId':tid,'clientUserMessageId':'busy-A','input':inp('BUSY-A')})['queuedSubmission'];b=c.ok('thread/queue/add',{'threadId':tid,'clientUserMessageId':'busy-B','input':inp('BUSY-B')})['queuedSubmission']
 dup=c.call('thread/queue/add',{'threadId':tid,'clientUserMessageId':'busy-A','input':inp('BUSY-A')});record('busy_queue_duplicate',{'first':a,'repeat':dup})
 rows=c.ok('thread/queue/list',{'threadId':tid})['data'];order=[x['id']for x in reversed(rows)]
 record('busy_queue_reorder',c.call('thread/queue/reorder',{'threadId':tid,'queuedSubmissionIds':order}))
 record('busy_queue_update',c.call('thread/queue/update',{'threadId':tid,'queuedSubmissionId':b['id'],'input':inp('BUSY-B-EDITED')}))
 record('busy_queue_delete',c.call('thread/queue/delete',{'threadId':tid,'queuedSubmissionId':a['id']}))
 record('busy_queue_before_crash',c.ok('thread/queue/list',{'threadId':tid}));record('true_crash_status',brief(c.ok('thread/read',{'threadId':tid})['thread']))
 # Kill server while client is still connected and turn is waiting for tool result.
 s.stop(crash=True);c.close();s.start();c=Client(s.sock)
 record('true_crash_read',brief(c.ok('thread/read',{'threadId':tid})['thread']));record('true_crash_turns',c.ok('thread/turns/list',{'threadId':tid,'limit':10}))
 record('busy_queue_after_crash',c.ok('thread/queue/list',{'threadId':tid}));pos=len(c.messages)
 record('busy_queue_resume',brief(c.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']))
 ev=c.wait(lambda x:x.get('method')=='turn/completed'and x.get('params',{}).get('threadId')==tid,60,pos);record('busy_queue_auto_completion',ev['params']['turn'])
 record('busy_queue_after_completion',c.ok('thread/queue/list',{'threadId':tid}))
 # Compare usage on source and fork using a dedicated thread, no revert/compaction.
 t=start(c)['thread'];tid=t['id'];pos=len(c.messages);record('usage_source_turn1',turn(c,tid,'Remember USAGE-735 and reply OK. No tools.'));record('usage_source_turn2',turn(c,tid,'Reply with the remembered marker, no tools.'))
 original=[x['params']for x in c.messages[pos:]if x.get('method')=='thread/tokenUsage/updated'];record('usage_source_counters',original)
 f=c.ok('thread/fork',{'threadId':tid,'excludeTurns':True})['thread'];fid=f['id'];pos=len(c.messages);record('usage_fork_turn',turn(c,fid,'Reply with the remembered marker, no tools.'));record('usage_fork_counters',[x['params']for x in c.messages[pos:]if x.get('method')=='thread/tokenUsage/updated'])
 for label,ident in [('source',tid),('fork',fid)]:
  p=pathlib.Path(c.ok('thread/read',{'threadId':ident})['thread']['path']);rows=[]
  for line in p.open():
   x=json.loads(line)
   if x.get('type')=='token_usage_record':rows.append(x['payload'])
  record('usage_rollout_'+label,rows)
 # Spawn a disposable child explicitly for descendant archive/delete testing.
 t=start(c)['thread'];tid=t['id'];record('descendant_parent_turn',turn(c,tid,'This is an authorized session-lifecycle experiment. Spawn exactly one child agent with the task: Reply CHILD-OK without tools or file changes. Wait for the child to finish, then reply PARENT-OK. Do not use any other tools.',timeout=90))
 kinds=['cli','vscode','exec','appServer','subAgent','subAgentReview','subAgentCompact','subAgentThreadSpawn','subAgentOther','unknown']
 desc=c.ok('thread/list',{'ancestorThreadId':tid,'sourceKinds':kinds,'limit':100});childids=[x['id']for x in desc['data']];record('descendant_before_archive',[brief(x)for x in desc['data']])
 f=c.ok('thread/fork',{'threadId':tid,'excludeTurns':True})['thread'];fid=f['id']
 record('descendant_archive_parent',c.call('thread/archive',{'threadId':tid}));record('descendant_archived_ids',[x['id']for x in c.ok('thread/list',{'ancestorThreadId':tid,'archived':True,'sourceKinds':kinds,'limit':100})['data']]);record('archive_parent_listing',{'present':tid in [x['id']for x in c.ok('thread/list',{'archived':True,'sourceKinds':kinds,'limit':100})['data']]})
 record('descendant_unarchive_parent',c.call('thread/unarchive',{'threadId':tid}));record('descendant_after_unarchive',{'stillArchived':[x['id']for x in c.ok('thread/list',{'ancestorThreadId':tid,'archived':True,'sourceKinds':kinds,'limit':100})['data']]})
 record('descendant_delete_parent',c.call('thread/delete',{'threadId':tid}));record('descendant_delete_effects',{'parent':c.call('thread/read',{'threadId':tid}),'children':[c.call('thread/read',{'threadId':x})for x in childids],'fork':brief(c.ok('thread/read',{'threadId':fid})['thread'])})
 # active archive and delete restrictions in disposable threads
 for action in ['thread/archive','thread/delete']:
  t,uid,req=hold(c);tid=t['id'];record('active_'+action,c.call(action,{'threadId':tid}));record('active_after_'+action,c.call('thread/read',{'threadId':tid}))
finally:c.close();s.stop()
