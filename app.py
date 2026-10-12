"""Sales Pipeline & Revenue Analytics — enhanced read-only snapshot exploration."""
from datetime import datetime
from hashlib import sha256
from uuid import uuid4
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from utils.data_loader import load_data,DEFAULT_DATASET
from utils.metrics import compute_pipeline_metrics
from components.sidebar import render_sidebar,active_filters
from components.dashboard_header import render_header
from components.overview import render_tab_overview
from components.pipeline_forecast import render_tab_pipeline_forecast
from components.sales_performance import render_tab_sales_performance
from components.deal_deep_dive import render_tab_deal_deep_dive
from components.ai_revenue_analyst import render_tab_ai_revenue_analyst

st.set_page_config(page_title='Sales Pipeline & Revenue Analytics',page_icon='📊',layout='wide')
header=st.container()
with st.sidebar:
    st.header('Revenue workspace')
    with st.expander('Dataset & analysis date',expanded=True):
        uploaded=st.file_uploader('Upload opportunity CSV',type=['csv'])
        analysis_date=st.date_input('Analysis date',value=datetime.now(ZoneInfo('America/Los_Angeles')).date(),help='Controls aging and date presets, not historical stage reconstruction.')
        st.caption('CSV source · Analysis date defaults to America/Los_Angeles.')
        if DEFAULT_DATASET.exists(): st.download_button('Download default CSV',DEFAULT_DATASET.read_bytes(),DEFAULT_DATASET.name,'text/csv',width='stretch')
name=uploaded.name if uploaded is not None else DEFAULT_DATASET.name
st.session_state.setdefault('cache_session',str(uuid4()))
frame=None; report=None; error=None
try:
    content=uploaded.getvalue() if uploaded is not None else DEFAULT_DATASET.read_bytes()
    fingerprint=sha256(content).hexdigest()
    with st.spinner('Preparing your opportunity workspace…'):
        frame,report=load_data(content,analysis_date,st.session_state.cache_session)
except (ValueError,OSError) as exc:
    error=str(exc)

filtered=None; metrics=None; dates=(); selections={}; target=None
if frame is not None and not frame.empty:
    filtered,target,dates,selections=render_sidebar(frame,fingerprint,analysis_date)
    st.session_state['view_analysis_date']=analysis_date
    st.session_state['view_close_range']=dates
    if not filtered.empty: metrics=compute_pipeline_metrics(filtered,target)
with header:
    render_header(name,filtered,len(frame) if frame is not None else 0,analysis_date,dates,selections)
if error: st.error(error)
active_filters(selections)
if report:
    with st.expander('Data quality summary',expanded=bool(report['issues'])):
        cols=st.columns(4)
        for col,label,key in zip(cols,['CSV records','Valid records','Rejected records','Duplicate IDs'],['total_records','valid_records','rejected_records','duplicate_ids']):
            value=report[key]; col.metric(label,len(value) if isinstance(value,list) else value)
        if report['issues']:
            st.warning('Some records or fields are excluded from affected calculations.')
            st.dataframe(pd.DataFrame(report['issues']),hide_index=True,width='stretch')
        else: st.success('All critical fields passed validation.')
        if report['missing_fields']: st.caption('Missing source values: '+', '.join(f'{k}: {v}' for k,v in report['missing_fields'].items()))
if metrics:
    if metrics['Missing Open Probabilities']:
        st.warning(f"Weighted pipeline is unavailable: {metrics['Missing Open Probabilities']} open opportunities lack a valid probability. Unweighted values remain available.")
    future=(filtered.created_date>pd.Timestamp(analysis_date)).sum()
    if future: st.warning(f'{future} records were created after the analysis date. The override changes aging and date presets, not snapshot stage assignments.')

names=['Executive Overview','Pipeline & Forecast','Sales Team Performance','Deal Deep-Dive & Revenue Trends','AI Revenue Analyst']
tabs=st.tabs(names)
renderers=[render_tab_overview,render_tab_pipeline_forecast,render_tab_sales_performance,render_tab_deal_deep_dive]
for tab,render in zip(tabs[:4],renderers):
    with tab:
        if filtered is None: st.info('Upload a valid opportunity CSV to see sales analytics.')
        elif filtered.empty: st.info('No opportunities match the selected filters. Try adjusting or resetting your filters.')
        else: render(filtered,metrics)
with tabs[4]:
    render_tab_ai_revenue_analyst(filtered,analysis_date=analysis_date,close_range=dates,
                                selections=selections,dataset_id=fingerprint if frame is not None else '',
                                revenue_target=target)
st.divider()
st.caption('CSV snapshot · Closed Won value is not recognized accounting revenue · Current stages do not reveal historical stage conversions · Read-only analysis')
