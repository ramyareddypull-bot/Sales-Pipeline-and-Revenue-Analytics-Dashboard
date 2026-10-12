"""Compact existing Python facts for model request limits; never recompute values."""
from copy import deepcopy
import json

CONTEXT_BYTE_LIMIT = 10000
HISTORY_BYTE_LIMIT = 2000


def _dump(payload):
    return json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def prepare_request_context(context, question):
    """Select relevant existing sections and cap rows without changing totals.

    Coverage metadata reports every reduction. Full aggregates remain available
    in Python and the dashboard; the language model receives a focused subset.
    """
    source=json.loads(context.json_data)
    payload=deepcopy(source)
    q=question.casefold()
    terms={'sales_team':('team',),'owner':('owner','rep','executive'),
           'industry':('industr',),'region':('region',),'lead_source':('lead','source')}
    requested=[name for name,words in terms.items() if any(word in q for word in words)]
    dimensions=requested or ['sales_team','industry','lead_source']
    payload['rankings']={key:value for key,value in payload['rankings'].items() if key in dimensions}
    for group in payload['rankings'].values():
        group['rows']=group['rows'][:5]
        group['groups_included']=len(group['rows'])
    payload['monthly_closed_won']=payload['monthly_closed_won'][-6:]
    payload['opportunities']=payload['opportunities'][:5]
    # Include earlier conversation intent when called by the adapter, so follow-up
    # questions can retain the relevant ranking category without old factual totals.
    def update_coverage():
        coverage=payload['detail_coverage']
        coverage['included_records']=len(payload['opportunities'])
        coverage['monthly_periods_included']=len(payload['monthly_closed_won'])
        coverage['ranking_groups_included']={k:len(v['rows']) for k,v in payload['rankings'].items()}
        coverage['omitted_ranking_dimensions']=[key for key in source['rankings'] if key not in payload['rankings']]
        coverage['request_note']='Request subset of Python facts. Missing details are unavailable, not zero. All cohort KPIs are complete subject to their null values.'
    update_coverage()
    # Drop low-priority detail first; never truncate JSON text or financial totals.
    while len(_dump(payload).encode('utf-8'))>CONTEXT_BYTE_LIMIT:
        if payload['opportunities']:
            payload['opportunities'].pop()
        elif any(len(group['rows'])>1 for group in payload['rankings'].values()):
            largest=max(payload['rankings'].values(),key=lambda group:len(group['rows']))
            largest['rows'].pop(); largest['groups_included']=len(largest['rows'])
        elif len(payload['monthly_closed_won'])>2:
            payload['monthly_closed_won'].pop(0)
        else:
            from utils.revenue_analyst import RevenueAnalystError
            raise RevenueAnalystError('The calculated context is too large for a safe AI request. Narrow the dashboard filters and retry.')
        update_coverage()
    return _dump(payload)


def bounded_history(history):
    result=[]; remaining=HISTORY_BYTE_LIMIT
    for message in reversed(history[-4:]):
        if message.get('role') not in ('user','assistant'): continue
        text=message['content']
        size=len(text.encode('utf-8'))
        if size>remaining: break
        result.append({'role':message['role'],'content':text})
        remaining-=size
    result.reverse()
    # Avoid starting the retained conversation with a standalone assistant answer.
    if result and result[0]['role']=='assistant': result=result[1:]
    return result


def safe_provider_error(exc):
    """Map SDK status/type to actionable fixed messages; never expose raw body."""
    status=getattr(exc,'status_code',None)
    kind=type(exc).__name__
    body=getattr(exc,'body',None)
    detail=body.get('error',body) if isinstance(body,dict) else {}
    code=detail.get('code','') if isinstance(detail,dict) else ''
    text=str(detail.get('message','')).casefold() if isinstance(detail,dict) else ''
    if status==413 or code=='context_length_exceeded' or ('too large' in text and status in (400,429)):
        return 'Groq rejected the request size for this model or account token limit. Clear analyst chat, ask a shorter question, or narrow the dashboard filters and retry.'
    if status==401:
        return 'Groq rejected the API key. Check GROQ_API_KEY in the server environment or project .env.'
    if status in (403,404) or code in ('model_not_found','model_decommissioned','model_deprecated'):
        return 'Groq could not access the configured model. Check GROQ_MODEL and your account permissions.'
    if status==429:
        return 'Groq rate or quota limit reached. Wait for your account limits to reset, then retry; check usage in the Groq console if it persists.'
    if kind=='APITimeoutError':
        return 'The Groq request timed out. Retry shortly or narrow the selected context.'
    if kind=='APIConnectionError':
        return 'Could not connect to Groq. Check the server network, proxy and TLS connection, then retry.'
    if status is not None and status>=500:
        return 'Groq is temporarily unavailable. Please retry shortly.'
    if status==400:
        return 'Groq rejected the request settings. Check that GROQ_MODEL supports chat completions and the configured response options.'
    return 'Groq could not complete the request. Check model access, credentials, quota or connectivity and retry.'
