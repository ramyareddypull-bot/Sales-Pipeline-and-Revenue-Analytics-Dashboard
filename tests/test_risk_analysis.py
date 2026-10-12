from datetime import date
from utils.data_cleaning import calculate_derived_columns,clean_data
from utils.risk_analysis import identify_at_risk_deals,pipeline_aging
from utils.metrics import compute_pipeline_metrics


def test_overdue_only_open_no_double_count(data):
    assert data.overdue.tolist()==[True,True,False,False]
    assert data.stale.tolist()==[True,True,False,False]
    assert data.stalled.tolist()==[True,True,False,False]
    assert len(identify_at_risk_deals(data))==2
    m=compute_pipeline_metrics(data)
    assert m['At-Risk Opportunity Count']==2
    assert m['At-Risk Pipeline Value']==30000
    assert pipeline_aging(data)['Pipeline Amount'].sum()==30000


def test_strict_boundary_and_future_optional_dates(raw):
    raw.loc[0,'stage_entered_date']='2026-09-11'
    raw.loc[0,'last_activity_date']='2026-09-27'
    raw.loc[0,'close_date']='2026-10-11'
    data=calculate_derived_columns(clean_data(raw)[0],date(2026,10,11))
    assert not data.loc[0,'at_risk']
    assert data.loc[0,'days_in_stage']==30
    assert data.loc[0,'days_since_activity']==14
