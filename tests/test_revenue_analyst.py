from datetime import date
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from utils.revenue_context import build_revenue_context, ContextError
from utils.revenue_analyst import AnalystConfig, RevenueAnalystError, respond, synchronize_scope, load_config


def context(data,**kwargs):
    args=dict(analysis_date=date(2026,10,11),close_range=(date(2026,1,1),date(2026,12,31)),selections={},dataset_id='test')
    args.update(kwargs)
    return build_revenue_context(data,**args)


def test_grounded_filtered_metrics_and_risks(data):
    result=json.loads(context(data).json_data)
    assert result['metrics']['Open Pipeline']==30000
    assert result['metrics']['Weighted Pipeline']==14000
    assert result['weighted_pipeline_explanation']['open_minus_weighted_usd']==16000
    assert result['metrics']['At-Risk Opportunity Count']==2
    assert sum(row['Opportunity Count'] for row in result['risk_categories_ranked_by_amount'])==6
    filtered=data.loc[data.region.eq('East')]
    result=json.loads(context(filtered,selections={'region':['East']}).json_data)
    assert result['metrics']['Open Pipeline']==10000
    assert {row['region'] for row in result['opportunities']}=={'East'}
    assert result['rankings']['sales_team']['rows'][0]['Win Rate %']==100


def test_missing_probabilities_and_empty_context(data):
    data.loc[0,'probability_pct']=float('nan')
    result=json.loads(context(data).json_data)
    assert result['metrics']['Weighted Pipeline'] is None
    assert result['weighted_pipeline_explanation']['open_minus_weighted_usd'] is None
    empty=json.loads(context(data.iloc[0:0]).json_data)
    assert empty['metrics']['Total Opportunities']==0
    assert empty['opportunities']==[]
    assert empty['rankings']['industry']['rows']==[]


def test_client_grounding_success_history_and_no_credentials(data):
    client=MagicMock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Open pipeline is $30,000.'))])
    config=AnalystConfig('test-secret-key','test-model')
    state={}
    ctx=context(data)
    answer=respond(ctx,'Summarize pipeline.',state,config=config,client=client)
    assert answer=='Open pipeline is $30,000.'
    args=client.chat.completions.create.call_args.kwargs
    assert args['model']=='test-model'
    sent=json.loads(args['messages'][1]['content'].split('\n',1)[1])
    assert sent['metrics']==json.loads(ctx.json_data)['metrics']
    assert 'test-secret-key' not in json.dumps(args)
    assert 'test-secret-key' not in repr(config)
    assert len(state['revenue_ai_messages'])==2
    respond(ctx,'Explain that.',state,config=config,client=client)
    assert len(state['revenue_ai_messages'])==4
    assert client.chat.completions.create.call_args.kwargs['messages'][2]['content']=='Summarize pipeline.'


def test_failures_sanitized_and_no_failed_turn(data):
    client=MagicMock()
    client.chat.completions.create.side_effect=RuntimeError('credential-leak')
    state={}
    with pytest.raises(RevenueAnalystError) as error:
        respond(context(data),'Summarize.',state,config=AnalystConfig('credential-leak','test'),client=client)
    assert 'credential-leak' not in str(error.value)
    assert state['revenue_ai_messages']==[]


def test_scope_changes_clear_chat_but_question_changes_do_not(data):
    state={}
    first=context(data)
    synchronize_scope(state,first)
    state['revenue_ai_messages']=['old']
    assert context(data,question='new question').scope_id==first.scope_id
    synchronize_scope(state,context(data.iloc[:1]))
    assert not state['revenue_ai_messages']
    assert context(data,dataset_id='new-file').scope_id!=first.scope_id
    assert context(data,analysis_date=date(2026,10,12)).scope_id!=first.scope_id
    assert context(data,revenue_target=100000).scope_id!=first.scope_id


def test_configuration_and_context_limits(monkeypatch,tmp_path,data):
    pytest.importorskip('dotenv',reason='Optional AI configuration test requires uv sync --extra ai.')
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.delenv('GROQ_MODEL',raising=False)
    path=tmp_path/'.env'
    path.write_text('GROQ_API_KEY=test-key\nGROQ_MODEL=test-model\n')
    assert load_config(path).model=='test-model'
    monkeypatch.setenv('GROQ_MODEL','override-model')
    assert load_config(path).model=='override-model'
    path.write_text('GROQ_API_KEY=\n')
    with pytest.raises(RevenueAnalystError): load_config(path)
    with pytest.raises(ContextError): context(data,question='x'*4001)
    data['account_name']='x'*70000
    with pytest.raises(ContextError,match='size limit'): context(data)


def test_supplied_dataset_context_is_bounded():
    from utils.data_loader import DEFAULT_DATASET,load_data
    frame,_=load_data(DEFAULT_DATASET.read_bytes(),date(2026,10,11),'ai-test')
    result=context(frame)
    payload=json.loads(result.json_data)
    assert payload['metrics']['Open Pipeline']==26237000
    assert payload['metrics']['Weighted Pipeline']==12023875
    assert len(result.json_data)<=60000
    assert len(payload['opportunities'])<=40


def test_month_changes_are_calculated_and_no_gap_is_compared(data):
    data.loc[0,'stage']='Closed Won'; data.loc[0,'close_date']=__import__('pandas').Timestamp('2026-08-01')
    data.loc[1,'stage']='Closed Won'; data.loc[1,'close_date']=__import__('pandas').Timestamp('2026-09-01')
    rows=json.loads(context(data).json_data)['monthly_closed_won']
    assert rows[1]['change_pct_vs_previous_calendar_month']==100
    assert rows[-1]['change_pct_vs_previous_calendar_month'] is None  # October is incomplete.
    data.loc[1,'close_date']=__import__('pandas').Timestamp('2026-06-01')
    rows=json.loads(context(data).json_data)['monthly_closed_won']
    assert all(row['change_pct_vs_previous_calendar_month'] is None for row in rows)


@pytest.mark.parametrize('model', ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'other-model'])
def test_model_specific_completion_budget(data, model):
    client=MagicMock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='Summary.'))])
    respond(context(data), 'Summarize.', {}, config=AnalystConfig('secret',model), client=client)
    options=client.chat.completions.create.call_args.kwargs
    if model.startswith('openai/gpt-oss-'):
        assert options['max_completion_tokens']==2200
        assert options['reasoning_effort']=='low'
    else:
        assert options['max_completion_tokens']==1100
        assert 'reasoning_effort' not in options


@pytest.mark.parametrize('choices,expected', [
    ([], 'no answer'),
    ([SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=None))], 'empty answer'),
    ([SimpleNamespace(finish_reason='length',message=SimpleNamespace(content='Partial'))], 'response token limit'),
    ([SimpleNamespace(finish_reason='length',message=SimpleNamespace(content=None))], 'response token limit'),
])
def test_incomplete_completions_are_actionable_and_not_saved(data,choices,expected):
    client=MagicMock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=choices)
    state={}
    with pytest.raises(RevenueAnalystError,match=expected):
        respond(context(data),'Summarize.',state,config=AnalystConfig('secret','test'),client=client)
    assert state['revenue_ai_messages']==[]
