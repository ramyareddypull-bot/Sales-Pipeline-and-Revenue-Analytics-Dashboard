import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from components.common import cards,table,chart,bar,BLUE,fmt,AMBER,RED,INDIGO
from components.drilldown import render_drilldown
from utils.dashboard_metrics import risk_summary
from utils.metrics import stage_summary,compute_forecast_metrics
from utils.risk_analysis import identify_at_risk_deals,pipeline_aging


def render_tab_pipeline_forecast(frame,metrics):
    cards(metrics,['Open Pipeline','Weighted Pipeline','Commit Pipeline','Best Case Pipeline','At-Risk Pipeline Value'])
    st.caption('These measures overlap and must not be added together. Commit/Best Case use the source forecast categories; risk is a rule-based subset of open pipeline.')
    st.subheader('Current Pipeline by Stage')
    selected=st.selectbox('Stage measure',['Opportunity Count','Total Pipeline Amount','Weighted Pipeline Amount'])
    stages=stage_summary(frame,True)
    fig=go.Figure(go.Funnel(y=stages.Stage,x=stages[selected],text=[fmt(v,selected) for v in stages[selected]],textinfo='text',marker=dict(color=BLUE),hovertemplate='%{y}<br>%{text}<extra></extra>'))
    chart(fig,selected,True)
    st.caption('Current stage snapshot only. Funnel widths are not historical stage conversion rates.')
    st.subheader('Forecast by category')
    forecasts=compute_forecast_metrics(frame)
    chart(px.bar(forecasts,x='Forecast Category',y=['Total Amount','Weighted Amount'],barmode='group',color_discrete_sequence=[BLUE,'#9ABCFB']),'Total Amount')
    table(forecasts)
    st.caption('Closed Won value is shown separately in Executive Overview. Any open deals classified Closed, Omitted or Unknown remain visible here for reconciliation.')
    st.subheader('Pipeline risk analysis')
    st.caption(f"{metrics['At-Risk Opportunity Count']:,} unique at-risk deals · {metrics['Incomplete Risk Checks']:,} open deals have incomplete activity/stage dates; absence of a flag does not establish low risk.")
    risk_measure=st.radio('Risk breakdown measure',['Opportunity Count','Pipeline Amount'],horizontal=True)
    risks=risk_summary(frame)
    chart(px.bar(risks,x='Risk Category',y=risk_measure,color='Risk Category',color_discrete_map={'Overdue':RED,'Inactive':AMBER,'Stalled':INDIGO}),risk_measure)
    st.caption('Risk categories overlap: one deal can be overdue, inactive and stalled. The unique at-risk KPI counts it only once.')
    render_drilldown(frame,'risk','Risk category','risk')
    risk=identify_at_risk_deals(frame)
    if risk.empty: st.info('No open deals meet the available overdue, inactive or stalled rules.')
    else:
        order=st.selectbox('Sort risk table by',['Opportunity value','Inactivity','Expected close date'])
        field,ascending={'Opportunity value':('amount_usd',False),'Inactivity':('days_since_activity',False),'Expected close date':('close_date',True)}[order]
        table(risk.sort_values(field,ascending=ascending)[['opportunity_id','account_name','opportunity_name','owner','stage','amount_usd','close_date','days_in_stage','days_since_activity','risk_reason']],risk=True)
    st.subheader('Pipeline aging')
    measure=st.radio('Aging measure',['Opportunity Count','Pipeline Amount'],horizontal=True)
    bar(pipeline_aging(frame),'Age Band',measure)
    unknown=frame.loc[frame.status.eq('Open'),'opportunity_age_days'].isna().sum()
    if unknown: st.caption(f'{unknown} opportunities created after the analysis date are excluded from age bands. This override does not reconstruct an earlier snapshot.')
