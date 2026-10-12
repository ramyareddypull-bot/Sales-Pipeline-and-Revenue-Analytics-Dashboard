from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from utils.filters import date_preset_range,cascade_filters,apply_filters,select_drilldown,search_opportunities
from utils.metrics import compute_pipeline_metrics,export_csv
from utils.dashboard_metrics import closed_won_comparison,risk_summary
from components.common import style_chart
import plotly.graph_objects as go


@pytest.mark.parametrize('preset,expected',[
    ('Last 30 Days',(date(2026,9,12),date(2026,10,11))),
    ('Last 90 Days',(date(2026,7,14),date(2026,10,11))),
    ('This Quarter',(date(2026,10,1),date(2026,12,31))),
    ('Last Quarter',(date(2026,7,1),date(2026,9,30))),
    ('This Year',(date(2026,1,1),date(2026,12,31))),
])
def test_presets(data,preset,expected):
    assert date_preset_range(preset,date(2026,10,11),data)==expected


def test_all_dates_keeps_future_and_quarter_rollover(data):
    data.loc[0,'close_date']=pd.Timestamp('2027-04-01')
    dates=date_preset_range('All Dates',date(2026,10,11),data)
    assert len(apply_filters(data,dates,{}))==4
    assert date_preset_range('Last Quarter',date(2026,1,1),data)==(date(2025,10,1),date(2025,12,31))


def test_cascade_normalization_and_visible_removed(data):
    data.loc[data.region.eq('East'),'owner']='East Owner'
    data.loc[data.region.eq('West'),'owner']='West Owner'
    available,valid,removed=cascade_filters(data,('2026-01-01','2026-12-31'),{'region':['west'],'owner':['East Owner']})
    assert available['owner']==['West Owner']
    assert valid['region']==['West'] and valid['owner']==[]
    assert removed['owner']==['East Owner']
    filtered=apply_filters(data,('2026-01-01','2026-12-31'),valid)
    assert set(filtered.region)=={'West'}


def test_drilldown_respects_cohort_and_export(data):
    global_data=apply_filters(data,('2026-01-01','2026-12-31'),{'region':['East']})
    selected=select_drilldown(global_data,'stage','Prospecting')
    assert len(selected)==1 and selected.region.iloc[0]=='East'
    exported=pd.read_csv(__import__('io').BytesIO(export_csv(selected)),dtype={'opportunity_id':str})
    assert exported.opportunity_id.tolist()==selected.opportunity_id.tolist()
    assert select_drilldown(global_data,'stage','Closed Lost').empty
    assert len(select_drilldown(global_data,'risk','Overdue'))==1
    assert len(select_drilldown(global_data,'owner_team',('Alice','Commercial')))==2
    assert len(search_opportunities(global_data,'aLiCe'))==2
    assert len(global_data)==2


def test_risk_overlap_is_not_unique_total(data):
    risk=risk_summary(data)
    assert risk['Opportunity Count'].sum()==6
    assert compute_pipeline_metrics(data)['At-Risk Opportunity Count']==2


def test_calendar_comparison_requires_full_coverage_and_baseline(data):
    data.loc[0,'stage']='Closed Won'; data.loc[0,'close_date']=pd.Timestamp('2026-08-15')
    data.loc[1,'stage']='Closed Won'; data.loc[1,'close_date']=pd.Timestamp('2026-09-20')
    comparison=closed_won_comparison(data,date(2026,10,11),(date(2026,8,1),date(2026,9,30)))
    assert comparison['change_pct']==100
    assert comparison['current']==20000 and comparison['previous']==10000
    assert closed_won_comparison(data,date(2026,10,11),(date(2026,8,15),date(2026,9,30))) is None
    data.loc[0,'amount_usd']=0
    assert closed_won_comparison(data,date(2026,10,11),(date(2026,8,1),date(2026,9,30))) is None


def test_theme_neutral_figure():
    fig=style_chart(go.Figure(go.Bar(x=['West'],y=[100])),y='Open Pipeline')
    assert fig.layout.paper_bgcolor=='rgba(0,0,0,0)'
    assert fig.layout.plot_bgcolor=='rgba(0,0,0,0)'
    assert fig.layout.yaxis.tickprefix=='$'
    assert fig.layout.font.color is None


def test_global_drilldown_reset_and_compact_ui():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py').run(timeout=45)
    assert not app.exception
    app.multiselect(key='filter_region').set_value(['West']).run(timeout=30)
    app.selectbox(key='drill_stage').set_value('Proposal').run(timeout=30)
    assert not app.exception
    detail=[d.value for d in app.dataframe if 'Opportunity ID' in d.value and 'Region' not in d.value]
    assert any(set(d['Stage'])=={'Proposal'} for d in detail if len(d))
    app.multiselect(key='filter_segment').set_value(['Enterprise']).run(timeout=30)
    app.multiselect(key='filter_stage').set_value(['Proposal']).run(timeout=30)
    assert not app.exception
    explorer=next(d.value for d in app.dataframe if 'Opportunity ID' in d.value and 'Region' in d.value)
    assert set(explorer.Region)=={'West'}
    assert set(explorer['Customer Segment'])=={'Enterprise'}
    assert set(explorer.Stage)=={'Proposal'}
    app.toggle(key='compact_layout').set_value(True).run(timeout=30)
    assert not app.exception
    next(b for b in app.button if b.label=='Reset All Filters').click().run(timeout=30)
    assert not app.exception
    assert all(not m.value for m in app.multiselect)
    assert app.selectbox(key='date_preset').value=='All Dates'
    assert app.selectbox(key='drill_stage').value is None
    assert any(m.label=='Open Pipeline' and m.value=='$26.24M' for m in app.metric)


def test_cascade_notice_and_replacement_clears_drilldown(monkeypatch,raw):
    from types import SimpleNamespace
    import streamlit as st
    raw.loc[raw.region.eq('East'),'owner']='East Owner'
    raw.loc[raw.region.eq('West'),'owner']='West Owner'
    upload=SimpleNamespace(name='replacement.csv',getvalue=lambda:raw.to_csv(index=False).encode())
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:upload)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py').run(timeout=30)
    app.multiselect(key='filter_owner').set_value(['East Owner']).run(timeout=30)
    app.multiselect(key='filter_region').set_value(['West']).run(timeout=30)
    assert not app.exception
    assert app.multiselect(key='filter_owner').value==[]
    assert any('Cleared selections' in message.value for message in app.warning)
    app.selectbox(key='drill_risk').set_value('Overdue').run(timeout=30)
    assert not app.exception
    raw['opportunity_id']=['NEW-'+str(i) for i in range(len(raw))]
    raw['amount_usd']=100
    app.run(timeout=30)
    assert not app.exception
    assert all(not m.value for m in app.multiselect)
    assert app.selectbox(key='drill_risk').value is None
    assert any(m.label=='Open Pipeline' and m.value=='$200' for m in app.metric)
    for table in app.dataframe:
        if 'Opportunity ID' in table.value:
            assert table.value['Opportunity ID'].str.startswith('NEW-').all()
