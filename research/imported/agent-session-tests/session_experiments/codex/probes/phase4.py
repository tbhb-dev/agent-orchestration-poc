from lab import *
s=Server().start();a=Client(s.sock);b=Client(s.sock)
def done(c,uid,pos=0,timeout=90):return c.wait(lambda x:x.get('method')=='turn/completed'and x.get('params',{}).get('turn',{}).get('id')==uid,timeout,pos)['params']['turn']
def begin(c,tid,text,**kw):return c.ok('turn/start',{'threadId':tid,'input':[{'type':'text','text':text}],**kw})['turn']['id']
try:
 # Native user-input request in Plan mode
 t=start(a)['thread'];tid=t['id'];pos=len(a.messages)
 uid=begin(a,tid,'This is a disposable protocol test. Use request_user_input to ask which marker to use, with choices ALPHA and BETA. Wait for my answer, then repeat it. Do not use other tools.',collaborationMode={'mode':'plan','settings':{'model':t['model'],'reasoning_effort':'low'}})
 req=a.wait(lambda x:x.get('method')=='item/tool/requestUserInput',60,pos);record('input_request',req);b.ok('thread/resume',{'threadId':tid,'excludeTurns':True})
 record('input_wait_status',brief(b.ok('thread/read',{'threadId':tid})['thread']))
 breq=b.wait(lambda x:x.get('method')=='item/tool/requestUserInput'and x.get('params',{}).get('threadId')==tid,10)
 record('input_broadcast',{'sameId':req['id']==breq['id']})
 answers={q['id']:{'answers':['BETA']}for q in req['params']['questions']}
 b.send({'id':breq['id'],'result':{'answers':answers}});record('input_completion',done(a,uid,pos))
 record('input_resolved_events',[x for x in a.messages[pos:]if x.get('method')=='serverRequest/resolved'])
 # Approval: a harmless explicitly escalated command in a read-only test thread
 t=start(a,sandbox='read-only',approvalPolicy='on-request',approvalsReviewer='user')['thread'];tid=t['id'];pos=len(a.messages)
 uid=begin(a,tid,'Protocol test: run a shell command that writes the literal APPROVAL-OK to '+str(WORK/'approval.txt')+'. Explicitly request sandbox escalation for that command because this thread is read-only. Use a command tool with sandbox_permissions=require_escalated and a justification. Do not use apply_patch. Afterward reply APPROVAL-DONE.')
 req=a.wait(lambda x:'id'in x and x.get('method')in ['item/commandExecution/requestApproval','item/permissions/requestApproval'],60,pos);record('approval_request',req);b.ok('thread/resume',{'threadId':tid,'excludeTurns':True})
 record('approval_wait_status',brief(b.ok('thread/read',{'threadId':tid})['thread']))
 breq=b.wait(lambda x:x.get('method')==req['method']and x.get('params',{}).get('threadId')==tid,10)
 if req['method']=='item/commandExecution/requestApproval':
  b.send({'id':breq['id'],'result':{'decision':'accept'}})
 else:raise RuntimeError('unexpected permission request: inspect before granting')
 record('approval_completion',done(a,uid,pos));record('approval_file',{'exists':(WORK/'approval.txt').exists(),'text':(WORK/'approval.txt').read_text()if(WORK/'approval.txt').exists()else None})
 record('approval_resolution_events',[x for x in a.messages[pos:]if x.get('method')=='serverRequest/resolved'])
 # Real tool subprocess, bounded at 40s, interrupted after its start marker
 script=WORK/'long_command.py';script.write_text("import os,time,pathlib\np=pathlib.Path(__file__).parent\n(p/'command.pid').write_text(str(os.getpid()))\n(p/'command-started.txt').write_text('STARTED')\ntime.sleep(40)\n(p/'command-finished.txt').write_text('FINISHED')\n")
 for name in ['command.pid','command-started.txt','command-finished.txt']:(WORK/name).unlink(missing_ok=True)
 t=start(a)['thread'];tid=t['id'];pos=len(a.messages)
 uid=begin(a,tid,'Run exactly python3 '+str(script)+' using the command execution tool, with a yield time of 1000 ms if available. If it is still running, wait for it with the tool. Do not run any other commands.')
 for _ in range(300):
  if(WORK/'command.pid').exists():break
  time.sleep(.1)
 assert(WORK/'command.pid').exists(),'command never started'
 pid=int((WORK/'command.pid').read_text());record('interrupt_request',a.call('turn/interrupt',{'threadId':tid,'turnId':uid}));record('interrupt_completion',done(a,uid,pos))
 time.sleep(1)
 try:os.kill(pid,0);alive=True
 except ProcessLookupError:alive=False
 record('interrupt_process_effects',{'pid':pid,'aliveAfter1s':alive,'startedFile':(WORK/'command-started.txt').exists(),'finishedFile':(WORK/'command-finished.txt').exists()})
 if alive:os.kill(pid,signal.SIGTERM);record('interrupt_test_cleanup',{'terminatedSurvivor':pid})
 # Manual compaction over real turns plus clearly labelled synthetic bulk history
 tid=json.loads((ROOT/'ids.json').read_text())['main'];a.ok('thread/resume',{'threadId':tid,'excludeTurns':True});pos=len(a.messages)
 text='Synthetic historical filler for a compaction experiment. Preserve BLUE-ORCHID-741 as the key fact.\n'+''.join('Record %d: the scratch experiment has no production side effects; counters and context are independent.\n'%i for i in range(600))
 record('compaction_inject',a.call('thread/inject_items',{'threadId':tid,'items':[{'type':'message','role':'user','content':[{'type':'input_text','text':text}]}]}))
 record('precompact_recall',turn(a,tid,'Reply only with the remembered marker; no tools.'))
 before=a.ok('thread/turns/list',{'threadId':tid,'limit':100,'itemsView':'summary'});pos=len(a.messages)
 record('compact_request',a.call('thread/compact/start',{'threadId':tid}))
 try:
  ev=a.wait(lambda x:x.get('method')=='thread/compacted'or(x.get('method')=='item/completed'and x.get('params',{}).get('item',{}).get('type')=='contextCompaction'),90,pos);record('compact_event',ev)
 except TimeoutError:record('compact_event_timeout',{'methods':[x.get('method')for x in a.messages[pos:]if'method'in x]})
 # wait for runtime to become idle before asking recall
 for _ in range(100):
  st=a.ok('thread/read',{'threadId':tid})['thread']['status']
  if st['type']!='active':break
  time.sleep(.2)
 after=a.ok('thread/turns/list',{'threadId':tid,'limit':100,'itemsView':'summary'})
 record('compaction_history',{'beforeIds':[t['id']for t in before['data']],'afterIds':[t['id']for t in after['data']],'status':st})
 record('postcompact_recall',turn(a,tid,'What exact marker did I originally ask you to remember? Reply only with it; no tools.'))
 record('usage_events',[x['params']for x in a.messages if x.get('method')=='thread/tokenUsage/updated'and x['params'].get('threadId')==tid])
finally:
 a.close();b.close();s.stop()
