import os,json,socket,struct,base64,hashlib,threading,time,subprocess,pathlib,signal,sqlite3
ROOT=pathlib.Path('/private/tmp/codex-session-study/lifecycle'); ROOT.mkdir(exist_ok=True)
WORK=ROOT/'workspace';WORK.mkdir(exist_ok=True)
HOME=ROOT/'home';HOME.mkdir(exist_ok=True)
OUT=pathlib.Path('/Users/tony/Code/github.com/tbhb/agent-session-tests/session_experiments/codex')
EVENTS=OUT/'results.jsonl'
def record(label,data):
 row={'at':time.time(),'test':label,'data':data}
 with EVENTS.open('a') as f:f.write(json.dumps(row,default=str)+'\n')
 print(label,json.dumps(data,default=str)[:1800],flush=True)
class Client:
 def __init__(self,path,experimental=True):
  self.s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.s.settimeout(20);self.s.connect(str(path));self.messages=[];self.cv=threading.Condition();self.counter=0;self.lock=threading.Lock();self.dead=False
  key=base64.b64encode(os.urandom(16)).decode();self.s.sendall(('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
  b=b''
  while b'\r\n\r\n' not in b:b+=self.s.recv(1)
  assert b.startswith(b'HTTP/1.1 101'),b
  assert base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()) in b
  self.s.settimeout(None);threading.Thread(target=self.reader,daemon=True).start()
  self.init=self.call('initialize',{'clientInfo':{'name':'codex_session_lab','version':'0.1'},'capabilities':{'experimentalApi':experimental}})
  self.send({'method':'initialized'})
 def send(self,x,opcode=1):
  d=json.dumps(x).encode() if opcode==1 else x;n=len(d);mask=os.urandom(4)
  h=bytes([128|opcode,128|n]) if n<126 else bytes([128|opcode,254])+struct.pack('!H',n) if n<65536 else bytes([128|opcode,255])+struct.pack('!Q',n)
  with self.lock:self.s.sendall(h+mask+bytes(v^mask[i%4] for i,v in enumerate(d)))
 def exact(self,n):
  b=b''
  while len(b)<n:
   x=self.s.recv(n-len(b))
   if not x:raise EOFError()
   b+=x
  return b
 def reader(self):
  fragments=b''
  try:
   while True:
    a,b=self.exact(2);n=b&127
    if n==126:n=struct.unpack('!H',self.exact(2))[0]
    elif n==127:n=struct.unpack('!Q',self.exact(8))[0]
    mask=self.exact(4) if b&128 else None;data=self.exact(n)
    if mask:data=bytes(v^mask[i%4] for i,v in enumerate(data))
    op=a&15
    if op==8:break
    if op==9:self.send(data,10);continue
    if op not in [0,1]:continue
    fragments+=data
    if not a&128:continue
    x=json.loads(fragments);fragments=b''
    with self.cv:self.messages.append(x);self.cv.notify_all()
  except Exception as e:self.reader_error=str(e)
  finally:
   with self.cv:self.dead=True;self.cv.notify_all()
 def wait(self,pred,timeout=30,start=0):
  end=time.monotonic()+timeout
  with self.cv:
   while True:
    for x in self.messages[start:]:
     if pred(x):return x
    if self.dead:raise EOFError(getattr(self,'reader_error','closed'))
    left=end-time.monotonic()
    if left<=0:raise TimeoutError('waiting for message')
    self.cv.wait(left)
 def request(self,m,p):
  self.counter+=1;i=self.counter;self.send({'id':i,'method':m,'params':p});return i
 def call(self,m,p,timeout=30):
  i=self.request(m,p);return self.wait(lambda x:x.get('id')==i and ('result'in x or 'error'in x),timeout)
 def ok(self,m,p,timeout=30):
  r=self.call(m,p,timeout)
  if 'error'in r:raise RuntimeError((m,r['error']))
  return r['result']
 def close(self):
  try:self.s.shutdown(socket.SHUT_RDWR)
  except OSError:pass
  self.s.close()
class Server:
 def __init__(self,name='a',binary='codex'):
  self.name=name;self.sock=ROOT/(name+'.sock');self.binary=binary
 def start(self):
  if self.sock.exists():self.sock.unlink()
  env=dict(os.environ,CODEX_HOME=str(HOME));env.pop('CODEX_THREAD_ID',None)
  self.log=(ROOT/(self.name+'.stderr')).open('a')
  self.p=subprocess.Popen([self.binary,'app-server','--listen','unix://'+str(self.sock)],cwd=WORK,env=env,stdout=subprocess.DEVNULL,stderr=self.log,start_new_session=True)
  for _ in range(200):
   if self.sock.exists():return self
   if self.p.poll() is not None:raise RuntimeError('server exited '+str(self.p.returncode))
   time.sleep(.05)
  raise TimeoutError('server startup')
 def stop(self,crash=False):
  if self.p.poll() is None:
   if crash:self.p.kill()
   else:self.p.terminate()
   try:self.p.wait(timeout=8)
   except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
  self.log.close()
def brief(t):return {k:t.get(k) for k in ['id','sessionId','forkedFromId','parentThreadId','historyMode','status','ephemeral','cwd','model','path']}
def start(c,**kw):
 p={'cwd':str(WORK),'sandbox':'workspace-write','approvalPolicy':'never',**kw};return c.ok('thread/start',p)
def turn(c,tid,prompt,timeout=90,**kw):
 pos=len(c.messages);r=c.ok('turn/start',{'threadId':tid,'input':[{'type':'text','text':prompt}],**kw});uid=r['turn']['id']
 done=c.wait(lambda x:x.get('method')=='turn/completed' and x.get('params',{}).get('turn',{}).get('id')==uid,timeout,pos)
 msgs=[x for x in c.messages[pos:] if x.get('method')=='item/completed' and x.get('params',{}).get('threadId')==tid and x.get('params',{}).get('item',{}).get('type')=='agentMessage']
 return {'turn':done['params']['turn'],'answers':[x['params']['item'].get('text') for x in msgs],'events':[x.get('method') for x in c.messages[pos:] if 'method'in x]}
if __name__=='__main__':
 auth=HOME/'auth.json'
 if not auth.exists():auth.symlink_to(pathlib.Path.home()/'.codex/auth.json')
 (HOME/'config.toml').write_text('model_reasoning_effort = "low"\n[analytics]\nenabled = false\n')
 s=Server().start()
 try:
  c=Client(s.sock);record('initialize',c.init)
  models=c.ok('model/list',{'limit':50});record('models',[{'model':m['model'],'default':m.get('isDefault')}for m in models['data']])
  t=start(c);record('start',{'thread':brief(t['thread']),'settings':{k:t.get(k)for k in ['model','approvalPolicy','sandbox','reasoningEffort']}})
  (ROOT/'ids.json').write_text(json.dumps({'main':t['thread']['id']}))
  record('initial_turn',turn(c,t['thread']['id'],'Session lifecycle experiment. Remember the exact marker BLUE-ORCHID-741. Reply with just that marker; do not call any tools.',timeout=90))
 finally:s.stop()
