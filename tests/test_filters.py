import pandas as pd
from utils.filters import apply_filters
from utils.metrics import compute_pipeline_metrics,stage_summary,compute_sales_performance


def test_all_empty_means_all_and_and_logic(data):
    bounds=('2026-01-01','2026-12-31')
    assert len(apply_filters(data,bounds,{'region':[]}))==4
    filtered=apply_filters(data,bounds,{'region':['East'],'stage':['Closed Won']})
    assert len(filtered)==1
    assert compute_pipeline_metrics(filtered)['Closed Won Opportunity Value']==15000
    assert stage_summary(filtered)['Total Pipeline Amount'].sum()==15000
    assert compute_sales_performance(filtered)['Total Opportunities'].sum()==1
    assert apply_filters(data,bounds,{'region':['missing']}).empty
    assert apply_filters(data,('2026-11-01','2026-12-31'),{}).empty
    assert apply_filters(data,(),{}).empty


def test_each_global_dimension(data):
    from utils.filters import FILTER_FIELDS
    for field in FILTER_FIELDS:
        choices=[data[field].iloc[0]]
        result=apply_filters(data,('2026-01-01','2026-12-31'),{field:choices})
        assert not result.empty
        assert set(result[field])==set(choices)
        assert result.opportunity_id.tolist()==data.loc[data[field].isin(choices),'opportunity_id'].tolist()
