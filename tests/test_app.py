from pathlib import Path
from types import SimpleNamespace
from datetime import date
import streamlit as st
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_tabs_global_filters_reset_and_controls():
    app=AppTest.from_file(APP).run(timeout=45)
    assert not app.exception
    assert len(app.tabs)==5
    assert any(m.value=='$26.24M' for m in app.metric)
    app.multiselect(key='filter_region').set_value(['West']).run(timeout=30)
    assert not app.exception
    assert not any(m.label=='Open Pipeline' and m.value=='$26.24M' for m in app.metric)
    app.multiselect(key='filter_stage').set_value(['Closed Won']).run(timeout=30)
    assert not app.exception
    assert any(m.label=='Open Pipeline' and m.value=='$0' for m in app.metric)
    next(b for b in app.button if b.label=='Reset All Filters').click().run(timeout=30)
    assert not app.exception
    assert any(m.value=='$26.24M' for m in app.metric)
    for selector in app.selectbox:
        if selector.label=='Trend metric':
            selector.set_value('Created Opportunity Amount'); break
    app.run(timeout=30)
    assert not app.exception
    app.text_input(key='deal_search').set_value('nothing matches this xyz').run(timeout=30)
    assert not app.exception


def test_new_csv_reset_and_empty_cohort(monkeypatch,raw):
    upload=SimpleNamespace(name='small.csv',getvalue=lambda:raw.to_csv(index=False).encode())
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:upload)
    app=AppTest.from_file(APP).run(timeout=30)
    assert not app.exception
    app.multiselect(key='filter_region').set_value(['East']).run(timeout=30)
    app.selectbox(key='date_preset').set_value('Custom Range').run(timeout=30)
    app.date_input(key='close_range').set_value((date(2027,1,1),date(2027,2,1))).run(timeout=30)
    assert not app.exception
    assert sum('No opportunities match the selected filters' in x.value for x in app.info)==4
    raw.loc[0,'owner']='New Owner'
    app.run(timeout=30)
    assert not app.exception
    assert app.multiselect(key='filter_region').value==[]
    upload.getvalue=lambda:b'invalid,headers\n1,2'
    app.run(timeout=30)
    assert not app.exception and len(app.error)>0


def test_optional_data_and_single_day_cohort(monkeypatch,raw):
    raw.loc[0,'probability_pct']=120
    raw.loc[1,'last_activity_date']='bad'
    raw['amount_usd']=0
    upload=SimpleNamespace(name='partial.csv',getvalue=lambda:raw.to_csv(index=False).encode())
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:upload)
    app=AppTest.from_file(APP).run(timeout=30)
    assert not app.exception
    assert any('Weighted pipeline is unavailable' in w.value for w in app.warning)
    for label,value in [('Stage measure','Weighted Pipeline Amount'),('Performance breakdown','Win rate by opportunity type'),('Trend metric','Closed Lost Value'),('Group dates by','Quarterly')]:
        next(s for s in app.selectbox if s.label==label).set_value(value)
    app.run(timeout=30)
    assert not app.exception
    raw['stage']='Invalid'
    app.run(timeout=30)
    assert not app.exception and len(app.tabs)==5
