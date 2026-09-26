from lab import *
s=Server().start();a=Client(s.sock);b=Client(s.sock)
try:
 # Establish tool-output persistence separately from user-provided markers.
 secret='TOOL-OUTPUT-'+os.urandom(4).hex();(WORK/'tool_marker.txt').write_text(secret)
 t=start(a)['thread'];tid=t['id'];record('tool_history_turn',turn(a,tid,'Read tool_marker.txt with a shell tool, remember its exact contents, and reply just READ. Do not echo the contents in your final response.'))
 (WORK/'tool_marker.txt').unlink();a.close();b.close();s.stop();s.start();a=Client(s.sock);b=Client(s.sock)
 a.ok('thread/resume',{'threadId':tid,'excludeTurns':True});r=turn(a,tid,'Without calling any tools, repeat the exact contents of the file you read earlier.');record('tool_history_resume',{'expected':secret,'result':r,'exactMatch':r['answers']==[secret]})
 # A heartbeat verifies a process is running, rather than merely a zombie/PID reuse.
 script=WORK/'heartbeat.py';script.write_text("import os,time,pathlib\np=pathlib.Path(__file__).parent\n(p/'heartbeat.pid').write_text(str(os.getpid()))\nfor i in range(150):\n (p/'heartbeat.txt').write_text(str(i)); time.sleep(.2)\n")
 for name in ['heartbeat.pid','heartbeat.txt']:(WORK/name).unlink(missing_ok=True)
 t=start(a)['thread'];tid=t['id'];pos=len(a.messages)
 r=a.ok('turn/start',{'threadId':tid,'input':[{'type':'text','text':'Run python3 '+str(script)+' using the command execution tool with yield_time_ms=1000. If still running, wait for it. No other commands.'}]});uid=r['turn']['id']
 for _ in range(300):
  if(WORK/'heartbeat.txt').exists():break
  time.sleep(.1)
 assert(WORK/'heartbeat.pid').exists()
 pid=int((WORK/'heartbeat.pid').read_text());record('heartbeat_interrupt',a.call('turn/interrupt',{'threadId':tid,'turnId':uid}));a.wait(lambda x:x.get('method')=='turn/completed'and x['params']['turn']['id']==uid,10,pos)
 time.sleep(1);v1=(WORK/'heartbeat.txt').read_text();time.sleep(2);v2=(WORK/'heartbeat.txt').read_text()
 ps=subprocess.run(['ps','-p',str(pid),'-o','pid=,stat=,comm='],capture_output=True,text=True).stdout.strip()
 record('heartbeat_after_interrupt',{'first':v1,'second':v2,'continued':int(v2)>int(v1),'process':ps,'terminals':a.call('thread/backgroundTerminals/list',{'threadId':tid})})
 try:os.kill(pid,signal.SIGTERM);record('heartbeat_cleanup',{'terminated':pid})
 except ProcessLookupError:pass
 # Finish deletion test with dependent fork removed.
 logs=[json.loads(x)for x in EVENTS.read_text().splitlines()]
 e=next(x['data']for x in reversed(logs)if x['test']=='descendant_delete_effects');parent=e['parent']['result']['thread']['id'];fid=e['fork']['id'];childids=[x['result']['thread']['id']for x in e['children']]
 paths=[x['result']['thread']['path']for x in [e['parent']]+e['children']]
 record('delete_dependent_fork',a.call('thread/delete',{'threadId':fid}));record('delete_parent_without_fork',a.call('thread/delete',{'threadId':parent}))
 record('delete_cascade_final',{'parent':a.call('thread/read',{'threadId':parent}),'children':[a.call('thread/read',{'threadId':x})for x in childids],'rolloutFilesExist':[pathlib.Path(x).exists()for x in paths]})
 # Database/byte-level residue of deleted parent/child, only within the disposable home.
 residue={}
 for p in HOME.rglob('*'):
  if p.is_file()and not p.is_symlink()and p.stat().st_size<20000000:
   raw=p.read_bytes()
   hits=[x for x in [parent]+childids if x.encode()in raw]
   if hits:residue[str(p.relative_to(HOME))]=len(hits)
 record('deleted_id_residual_files',residue)
 # Confirm resume subscription supports turn/start on the same in-flight turn.
 gate={'type':'function','name':'lab_gate','description':'Pause disposable experiment.','inputSchema':{'type':'object','properties':{}}}
 t=start(a,dynamicTools=[gate])['thread'];tid=t['id'];pos=len(a.messages)
 uid=a.ok('turn/start',{'threadId':tid,'input':[{'type':'text','text':'Call lab_gate once, then reply FINAL with any later marker. No other tools.'}]})['turn']['id']
 req=a.wait(lambda x:x.get('method')=='item/tool/call'and x['params']['threadId']==tid,60,pos)
 r=b.call('turn/start',{'threadId':tid,'input':[{'type':'text','text':'Later marker: SECOND-START-332.'}]});record('concurrent_turn_start',{'originalTurnId':uid,'secondResponse':r})
 a.send({'id':req['id'],'result':{'success':True,'contentItems':[{'type':'inputText','text':'CONTINUE'}]}})
 record('concurrent_turn_completion',a.wait(lambda x:x.get('method')=='turn/completed'and x['params']['turn']['id']==uid,60,pos)['params']['turn'])
finally:a.close();b.close();s.stop()
