from lab import *
from collections import Counter
h=pathlib.Path.home()/'.codex';c=Client(h/'app-server-control/app-server-control.sock')
try:
 kinds=['cli','vscode','exec','appServer','subAgent','subAgentReview','subAgentCompact','subAgentThreadSpawn','subAgentOther','unknown']
 data=[];cursor=None
 while True:
  p={'limit':100,'sourceKinds':kinds,'useStateDbOnly':True}
  if cursor:p['cursor']=cursor
  r=c.ok('thread/list',p);data+=r['data'];cursor=r['nextCursor']
  if not cursor:break
 ids={x['id']for x in data};d=sqlite3.connect((h/'state_5.sqlite').as_uri()+'?mode=ro',uri=True);d.row_factory=sqlite3.Row
 rows=list(d.execute('select id,source,has_user_event,archived,history_mode from threads'))
 def category(r):
  src=r['source']
  if src.startswith('{'):
   x=json.loads(src).get('subagent',{});src='subagent:'+('other:'+str(x['other'])if'other'in x else next(iter(x),'unknown'))
  return (src,r['has_user_event'],r['archived'])
 record('inventory_reconciliation',{'apiCount':len(ids),'dbCount':len(rows),'missingGroups':[(list(k),v)for k,v in Counter(category(r)for r in rows if r['id']not in ids).items()],'includedGroups':[(list(k),v)for k,v in Counter(category(r)for r in rows if r['id']in ids).items()]})
 # compare scan and repair is deliberately avoided in the real home
finally:c.close()
