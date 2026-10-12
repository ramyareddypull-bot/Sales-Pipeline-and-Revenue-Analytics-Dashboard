import plotly.express as px
import streamlit as st
from components.common import chart,GREEN,BLUE,RED
from utils.metrics import TREND_METRICS,revenue_trend


def render_trend(frame,key):
    a,b=st.columns([2,1])
    metric=a.selectbox('Trend metric',list(TREND_METRICS),key=key+'_metric')
    frequency=b.selectbox('Group dates by',['Daily','Weekly','Monthly','Quarterly'],index=2,key=key+'_frequency')
    data=revenue_trend(frame,metric,frequency)
    if data.empty:
        st.info('No recorded outcomes for this trend in the selected cohort.'); return
    color=RED if metric=='Closed Lost Value' else GREEN if metric.startswith('Closed Won') else BLUE
    fig=px.line(data,x='Period',y='Value',markers=True,color_discrete_sequence=[color],labels={'Value':metric,'Period':'Period start'})
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(rangeslider_visible=True)
    money='Value' in metric or 'Amount' in metric
    fig.update_traces(hovertemplate='%{x|%b %d, %Y}<br>'+('$' if money else '')+'%{y:,.0f}<extra></extra>')
    chart(fig,metric,height=400,key=key+'_chart')
    st.caption('Close Date Range defines this cohort. Created metrics group it by creation date; closed outcomes use actual close date. The range slider zooms this chart only. This is not historical pipeline value.')
