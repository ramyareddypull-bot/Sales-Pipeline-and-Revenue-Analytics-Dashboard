from datetime import date
from types import SimpleNamespace
import json
import pytest
from utils.data_loader import DEFAULT_DATASET,load_data
from utils.revenue_context import build_revenue_context
from utils.revenue_request import prepare_request_context,bounded_history,safe_provider_error


def test_sample_context_budget_and_grounding():
    frame,_=load_data(DEFAULT_DATASET.read_bytes(),date(2026,10,11),'request-test')
    context=build_revenue_context(frame,analysis_date=date(2026,10,11),close_range=(frame.close_date.min().date(),frame.close_date.max().date()),selections={},dataset_id='sample')
    original=json.loads(context.json_data)
    for question in ['Summarize the pipeline.','Which sales team has the highest win rate?','Which industries produce Closed Won value?','What are my biggest risks?']:
        sent=prepare_request_context(context,question)
        assert len(sent.encode())<=10000
        payload=json.loads(sent)
        assert payload['metrics']==original['metrics']
        assert payload['weighted_pipeline_explanation']==original['weighted_pipeline_explanation']
        assert payload['detail_coverage']['included_records']==len(payload['opportunities'])
        assert payload['metrics']['Open Pipeline']==26237000
        for name,group in payload['rankings'].items():
            assert group['groups_included']==len(group['rows'])
            assert all(row in original['rankings'][name]['rows'] for row in group['rows'])
        if 'sales team' in question: assert list(payload['rankings'])==['sales_team']
    assert len(context.json_data)>10000  # Full Python context remains intact.


@pytest.mark.parametrize('status,expected',[(413,'request size'),(401,'API key'),(403,'model'),(404,'model'),(429,'quota'),(500,'temporarily'),(400,'settings')])
def test_safe_error_mapping(status,expected):
    exc=SimpleNamespace(status_code=status,body={'error':{'message':'secret-key sensitive account details'}})
    result=safe_provider_error(exc)
    assert expected in result
    assert 'secret-key' not in result and 'sensitive' not in result


def test_history_budget_no_unpaired_assistant():
    messages=[{'role':'user','content':'question'},{'role':'assistant','content':'a'*5000},{'role':'user','content':'follow-up'}]
    result=bounded_history(messages)
    assert result==[messages[-1]]
    assert sum(len(m['content'].encode()) for m in result)<=2000
