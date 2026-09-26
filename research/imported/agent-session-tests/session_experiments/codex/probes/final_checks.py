from lab import *
rows=[json.loads(x)for x in EVENTS.read_text().splitlines()]
def last(k):return next(x['data']for x in reversed(rows)if x['test']==k)
parent=last('descendant_delete_effects')['parent']['result']['thread']['id'];child=last('descendant_before_archive')[0]['id'];ephemeral=last('ephemeral_start')['id']
checks={}
for dbname,table in [('state_5.sqlite','threads'),('thread_history_1.sqlite','thread_turns'),('thread_history_1.sqlite','thread_items')]:
 db=sqlite3.connect((HOME/dbname).as_uri()+'?mode=ro',uri=True)
 cols=[x[1]for x in db.execute('pragma table_info('+table+')')];key='id'if table=='threads'else'thread_id'
 if key in cols:checks[dbname+':'+table]={label:db.execute('select count(*) from '+table+' where '+key+'=?',(ident,)).fetchone()[0]for label,ident in [('deletedParent',parent),('deletedChild',child),('ephemeral',ephemeral)]}
record('logical_rows_after_delete',checks)
source=last('usage_rollout_source');fork=last('usage_rollout_fork');own=sum(x['usage']['total_tokens']for x in source);new=sum(x['usage']['total_tokens']for x in fork)
record('usage_reconciliation',{'sourceResponses':own,'sourceLatestTotal':source[-1]['thread_token_usage']['total_tokens'],'forkNewResponses':new,'forkLatestTotal':fork[-1]['thread_token_usage']['total_tokens'],'correctCombinedNewWork':own+new,'incorrectSumThreadTotals':source[-1]['thread_token_usage']['total_tokens']+fork[-1]['thread_token_usage']['total_tokens']})
# Confirm final queue order using persisted history, without resuming it.
s=Server().start();c=Client(s.sock)
try:
 tid=last('true_crash_status')['id'];r=c.ok('thread/turns/list',{'threadId':tid,'limit':50,'itemsView':'full','sortDirection':'asc'})
 record('queue_final_history',{'turns':[{'id':t['id'],'status':t['status'],'answers':[i.get('text')for i in t['items']if i['type']=='agentMessage']}for t in r['data']],'remaining':c.ok('thread/queue/list',{'threadId':tid})})
finally:c.close();s.stop()
