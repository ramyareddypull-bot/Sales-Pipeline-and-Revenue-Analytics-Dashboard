import streamlit as st
from components.common import cards,table,bar
from components.drilldown import render_drilldown
from utils.metrics import compute_sales_performance


def render_tab_sales_performance(frame,metrics):
    cards(metrics,['Closed Won Opportunity Value','Win Rate %','Closed Won Deals','Average Won Deal Size','Average Won Sales Cycle'])
    st.subheader('Sales rep leaderboard & top performers')
    a,b=st.columns([3,1])
    measure=a.selectbox('Sales rep chart metric',['Closed Won Opportunity Value','Win Rate %','Open Pipeline','Weighted Pipeline','Average Won Deal Size','Closed Won Deals'])
    limit=b.selectbox('Show performers',['Top 5','Top 10','All'],index=1)
    reps=compute_sales_performance(frame).sort_values(measure,ascending=False,na_position='last',kind='stable')
    cols=['owner','sales_team','Total Opportunities','Closed Won Deals','Closed Lost Deals','Win Rate %','Closed Won Opportunity Value','Open Pipeline','Weighted Pipeline','Average Won Deal Size']
    table(reps[cols],highlight=True)
    st.caption(f'Leaderboard and chart ranked by {measure}. Owners are grouped with their team. Missing values are unranked; table headers also support sorting.')
    ranked=reps.loc[reps[measure].notna()].copy()
    if limit!='All': ranked=ranked.head(int(limit.split()[1]))
    ranked['Sales Rep / Team']=ranked.owner+' · '+ranked.sales_team
    bar(ranked,'Sales Rep / Team',measure,horizontal=True)
    render_drilldown(frame,'owner_team','Sales owner / team','owner')
    st.subheader('Regional performance')
    st.caption('Use the global Customer Segment filter to compare regions for a selected segment across all views.')
    region_metric=st.selectbox('Regional metric',['Open Pipeline','Closed Won Opportunity Value','Weighted Pipeline'])
    regions=compute_sales_performance(frame,('region',)).sort_values(region_metric,ascending=False,na_position='last')
    bar(regions,'region',region_metric)
    render_drilldown(frame,'region','Region','region')
    with st.expander('Regional scorecard'):
        table(regions[['region','Open Pipeline','Closed Won Opportunity Value','Win Rate %','Weighted Pipeline','Average Won Deal Size']])
    st.subheader('Win rate by sales team')
    teams=compute_sales_performance(frame,('sales_team',)).sort_values('Win Rate %',ascending=False)
    bar(teams,'sales_team','Win Rate %')
    st.caption('Won / (won + lost) within each selected team. Open opportunities are excluded from the denominator.')
    st.subheader('Industry, segment & opportunity type')
    selection=st.selectbox('Performance breakdown',['Closed Won by industry','Open pipeline by segment','Win rate by opportunity type'])
    dimension,value={'Closed Won by industry':('industry','Closed Won Opportunity Value'),'Open pipeline by segment':('segment','Open Pipeline'),'Win rate by opportunity type':('opportunity_type','Win Rate %')}[selection]
    data=compute_sales_performance(frame,(dimension,))
    bar(data,dimension,value)
    render_drilldown(frame,dimension,{'industry':'Industry','segment':'Customer segment','opportunity_type':'Opportunity type'}[dimension],'industry')
    with st.expander('Breakdown scorecard'):
        table(data[[dimension,'Total Opportunities','Closed Won Deals','Closed Lost Deals','Win Rate %','Closed Won Opportunity Value','Open Pipeline']])
    st.subheader('Lead source effectiveness')
    leads=compute_sales_performance(frame,('lead_source',))
    bar(leads,'lead_source','Closed Won Opportunity Value')
    render_drilldown(frame,'lead_source','Lead source','lead_source')
    with st.expander('Lead source scorecard'):
        table(leads[['lead_source','Total Opportunities','Closed Won Deals','Closed Lost Deals','Win Rate %','Closed Won Opportunity Value','Open Pipeline']])
    st.caption('This source has no marketing spend, CAC or ROI inputs; lead-source charts describe opportunity outcomes only.')
