from datetime import date
import pandas as pd
import pytest
from utils.data_loader import load_data,DEFAULT_DATASET
from utils.metrics import compute_pipeline_metrics,compute_win_rate,compute_sales_performance,compute_forecast_metrics,revenue_trend,export_csv
from utils.data_cleaning import calculate_derived_columns,clean_data


def test_acceptance_pipeline_weighted(data):
    m=compute_pipeline_metrics(data)
    assert m['Open Pipeline']==30000
    assert m['Weighted Pipeline']==14000
    assert m['Closed Won Opportunity Value']==15000
    assert m['Closed Lost Value']==5000
    assert m['Win Rate %']==50
    assert m['Average Won Deal Size']==15000
    assert m['Pipeline Coverage'] is None
    assert compute_pipeline_metrics(data,10000)['Pipeline Coverage']==3


def test_win_rate_80_percent(data):
    rows=pd.concat([data.iloc[[2]]]*8+[data.iloc[[3]]]*2+[data.iloc[[0]]]*5,ignore_index=True)
    rows['opportunity_id']=[str(i) for i in range(15)]
    assert compute_win_rate(rows)==80


def test_partial_probability_and_empty(data):
    data.loc[0,'weighted_amount']=float('nan')
    assert compute_pipeline_metrics(data)['Weighted Pipeline'] is None
    assert compute_pipeline_metrics(data)['Open Pipeline']==30000
    empty=compute_pipeline_metrics(data.iloc[0:0])
    assert empty['Win Rate %'] is None and empty['Average Won Deal Size'] is None
    assert empty['Open Pipeline']==0


def test_owner_team_group_and_forecast_reconcile(data):
    data.loc[1,'sales_team']='Enterprise'
    grouped=compute_sales_performance(data)
    assert len(grouped)==2
    assert grouped['Open Pipeline'].sum()==30000
    forecast=compute_forecast_metrics(data)
    assert forecast['Total Amount'].sum()==30000
    assert forecast['Weighted Amount'].sum()==14000


def test_trend_date_dimensions(data):
    created=revenue_trend(data,'Created Opportunity Count','Monthly')
    assert created.Period.iloc[0]==pd.Timestamp('2026-01-01')
    assert created.Value.sum()==4
    won=revenue_trend(data,'Closed Won Opportunity Value','Quarterly')
    assert won.Period.iloc[0]==pd.Timestamp('2026-10-01')
    assert won.Value.sum()==15000


def test_default_reference_values():
    frame,report=load_data(DEFAULT_DATASET.read_bytes(),date(2026,10,11),'test-default')
    assert report['total_records']==650
    m=compute_pipeline_metrics(frame)
    for name,expected in {'Total Opportunities':650,'Open Opportunity Count':231,'Closed Won Deals':220,'Closed Lost Deals':199,
                          'Open Pipeline':26237000,'Weighted Pipeline':12023875,'Closed Won Opportunity Value':27683200}.items():
        assert m[name]==pytest.approx(expected)
    assert m['Win Rate %']==pytest.approx(52.51,abs=.01)


def test_safe_csv_export(data):
    data.loc[0,'next_step']='=HYPERLINK("bad")'
    assert b"'=HYPERLINK" in export_csv(data)
