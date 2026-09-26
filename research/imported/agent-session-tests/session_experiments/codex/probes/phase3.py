from lab import *
GATE={'type':'function','name':'lab_gate','description':'Pause a disposable session experiment until the test controller responds. Call exactly once when asked.','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}
def hold(c):
 t=start(c,dynamicTools=[GATE])['thread'];pos=len(c.messages)
 r=c.ok('turn/start',{'threadId':t['id'],'input':[{'type':'text','text':'Call lab_gate exactly once now. After it returns, reply GATE-DONE and any replacement marker requested by later input. Do not use other tools.'}]})
 req=c.wait(lambda x:x.get('method')=='item/tool/call' and x.get('params',{}).get('threadId')==t['id'],60,pos)
 return t,r['turn']['id'],req
s=Server().start();s2=Server('b');a=Client(s.sock);b=Client(s.sock)
try:
 # B reads only, then observe a small real turn
 t=start(a)['thread'];tid=t['id'];b.ok('thread/read',{'threadId':tid});p=len(b.messages)
 record('observer_turn',turn(a,tid,'Reply OBSERVER-TEST; no tools.'))
 time.sleep(.2);record('read_only_observer_events',[x.get('method')for x in b.messages[p:]if'method'in x])
 record('second_client_resume',brief(b.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']));p=len(b.messages)
 record('subscribed_turn',turn(a,tid,'Reply SUBSCRIBED-TEST; no tools.'))
 time.sleep(.2);record('resumed_observer_events',[x.get('method')for x in b.messages[p:]if'method'in x])
 # hold a real model turn at an external dynamic tool, steer and cross-runtime collision
 t,uid,req=hold(a);tid=t['id'];record('gate_wait',{'thread':brief(a.ok('thread/read',{'threadId':tid})['thread']),'requestMethod':req['method']})
 record('steer_stale',a.call('turn/steer',{'threadId':tid,'expectedTurnId':'stale-turn-id','input':[{'type':'text','text':'WRONG'}]}))
 record('steer_valid',b.call('turn/steer',{'threadId':tid,'expectedTurnId':uid,'input':[{'type':'text','text':'Use replacement marker STEER-924 in your final response.'}]}))
 record('revert_active',a.call('thread/revert',{'threadId':tid,'beforeTurnId':uid}))
 s2.start();d=Client(s2.sock)
 record('other_runtime_read',brief(d.ok('thread/read',{'threadId':tid})['thread']))
 record('other_runtime_loaded',d.ok('thread/loaded/list',{}))
 record('other_runtime_resume',d.call('thread/resume',{'threadId':tid,'excludeTurns':True},timeout=12));d.close();s2.stop()
 record('gate_second_subscribe',brief(b.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']))
 time.sleep(.3);pending=[x for x in b.messages if x.get('method')=='item/tool/call' and x.get('params',{}).get('threadId')==tid]
 record('pending_tool_replayed_to_second_client',{'count':len(pending),'sameRequestId':bool(pending and pending[-1]['id']==req['id'])})
 a.send({'id':req['id'],'result':{'contentItems':[{'type':'inputText','text':'RELEASED'}],'success':True}})
 done=b.wait(lambda x:x.get('method')=='turn/completed' and x.get('params',{}).get('turn',{}).get('id')==uid,60)
 record('steered_completion',done['params']['turn'])
 # owner disconnect while gate is pending; leave B subscribed
 t,uid,req=hold(a);tid=t['id'];b.ok('thread/resume',{'threadId':tid,'excludeTurns':True});a.close();time.sleep(.5)
 record('owner_disconnect_status',brief(b.ok('thread/read',{'threadId':tid})['thread']))
 pending=[x for x in b.messages if x.get('method')=='item/tool/call' and x.get('params',{}).get('threadId')==tid]
 if pending:
  b.send({'id':pending[-1]['id'],'result':{'contentItems':[{'type':'inputText','text':'SECOND-CLIENT-RELEASE'}],'success':True}})
  record('second_client_tool_resolution',b.wait(lambda x:x.get('method')=='turn/completed' and x.get('params',{}).get('turn',{}).get('id')==uid,60)['params']['turn'])
 else:record('disconnect_interrupt',b.call('turn/interrupt',{'threadId':tid,'turnId':uid}))
 a=Client(s.sock)
 # queue persistence, duplicates, reorder/cancel, explicit start after restart
 q=start(a)['thread']['id'];inp=lambda x:[{'type':'text','text':'Reply exactly '+x+'; no tools.'}]
 qa=a.ok('thread/queue/add',{'threadId':q,'clientUserMessageId':'queue-A','input':inp('QUEUE-A')})
 qb=a.ok('thread/queue/add',{'threadId':q,'clientUserMessageId':'queue-B','input':inp('QUEUE-B')})
 record('queue_add',[qa,qb]);record('queue_duplicate',a.call('thread/queue/add',{'threadId':q,'clientUserMessageId':'queue-A','input':inp('QUEUE-A')}))
 aid=qa['queuedSubmission']['id'];bid=qb['queuedSubmission']['id']
 record('queue_update',a.call('thread/queue/update',{'threadId':q,'queuedSubmissionId':bid,'input':inp('QUEUE-B-EDITED')}))
 record('queue_reorder',a.call('thread/queue/reorder',{'threadId':q,'queuedSubmissionIds':[bid,aid]}))
 record('queue_before_restart',a.ok('thread/queue/list',{'threadId':q}));a.close();b.close();s.stop(crash=True);s.start();a=Client(s.sock);b=Client(s.sock)
 record('queue_after_crash',a.ok('thread/queue/list',{'threadId':q}));record('queue_delete',a.call('thread/queue/delete',{'threadId':q,'queuedSubmissionId':aid}))
 a.ok('thread/resume',{'threadId':q,'excludeTurns':True});pos=len(a.messages)
 r=a.call('thread/queue/start',{'threadId':q});record('queue_start',r)
 if 'result'in r:
  uid=r['result']['turn']['id'];record('queue_completion',a.wait(lambda x:x.get('method')=='turn/completed' and x.get('params',{}).get('turn',{}).get('id')==uid,60,pos)['params']['turn'])
 record('queue_after_delivery',a.ok('thread/queue/list',{'threadId':q}))
 # kill server mid-tool; inspect turn state after recovery, then explicitly continue
 t,uid,req=hold(a);tid=t['id'];record('crash_before',brief(t));a.close();b.close();s.stop(crash=True);s.start();a=Client(s.sock);b=Client(s.sock)
 record('crash_after_read',brief(a.ok('thread/read',{'threadId':tid})['thread']))
 record('crash_after_turns',a.ok('thread/turns/list',{'threadId':tid,'limit':10}))
 record('crash_resume',brief(a.ok('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']))
 record('crash_recovery_turn',turn(a,tid,'The test controller restarted. Do not call tools. Reply RECOVERED.'))
finally:
 for c in [a,b]:
  try:c.close()
  except Exception:pass
 if hasattr(s2,'p')and s2.p.poll()is None:s2.stop()
 s.stop()
