import plotly.express as px
import streamlit as st
from components.common import cards,chart,BLUE,GREEN,INDIGO,STAGE_COLORS,pair,fmt
from components.drilldown import render_drilldown
from components.trend_chart import render_trend
from utils.metrics import stage_summary,compute_sales_performance
from utils.dashboard_metrics import key_insights,closed_won_comparison


def render_tab_overview(frame,metrics):
    cards(metrics,['Open Pipeline','Closed Won Opportunity Value','Weighted Pipeline','Win Rate %','Average Won Deal Size'])
    st.caption('Closed Won value is booked opportunity value, not recognized accounting revenue. Forecast weighting reflects supplied probabilities.')
    left,right=pair()
    with left:
        with st.container(border=True):
            st.subheader('Open pipeline by stage')
            measure=st.selectbox('Pipeline stage metric',['Total Pipeline Amount','Opportunity Count','Weighted Pipeline Amount'],key='overview_stage_measure')
            data=stage_summary(frame,True)
            data['% of Open Pipeline']=data['Total Pipeline Amount']/metrics['Open Pipeline']*100 if metrics['Open Pipeline'] else 0
            for field in ('Total Pipeline Amount','Weighted Pipeline Amount'):
                data[field+' label']=[fmt(v,field) for v in data[field]]
            fig=px.bar(data,y='Stage',x=measure,orientation='h',color='Stage',color_discrete_map=STAGE_COLORS,
                       custom_data=['Opportunity Count','Total Pipeline Amount label','Weighted Pipeline Amount label','% of Open Pipeline'])
            fig.update_traces(hovertemplate='%{y}<br>Opportunities: %{customdata[0]:,}<br>Amount: %{customdata[1]}<br>Weighted: %{customdata[2]}<br>Open pipeline share: %{customdata[3]:.1f}%<extra></extra>')
            fig.update_layout(showlegend=False); fig.update_yaxes(autorange='reversed')
            chart(fig,measure,True)
            render_drilldown(frame.loc[frame.status.eq('Open')],'stage','Pipeline stage','stage')
    with right:
        with st.container(border=True):
            st.subheader('Closed Won distribution')
            label=st.selectbox('Group distribution by',['Region','Customer Segment','Opportunity Type'])
            dimension={'Region':'region','Customer Segment':'segment','Opportunity Type':'opportunity_type'}[label]
            grouped=compute_sales_performance(frame,(dimension,))
            if grouped['Closed Won Opportunity Value'].sum()>0:
                fig=px.pie(grouped,names=dimension,values='Closed Won Opportunity Value',hole=.65,color_discrete_sequence=[BLUE,INDIGO,GREEN,'#F59E0B'],labels={dimension:label})
                fig.update_traces(textinfo='percent',hovertemplate='%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>')
                chart(fig)
            else: st.info('No positive Closed Won value available for this distribution.')
            render_drilldown(frame.loc[frame.stage.eq('Closed Won')],dimension,label,'distribution')
    st.subheader('Revenue trends')
    render_trend(frame,'overview_trend')
    comparison=closed_won_comparison(frame,st.session_state['view_analysis_date'],st.session_state['view_close_range'])
    if comparison:
        with st.expander('Complete-month Closed Won comparison'):
            st.metric(comparison['current_period'],fmt(comparison['current'],'Closed Won Opportunity Value'),delta=f"{comparison['change_pct']:+.1f}% vs {comparison['previous_period']}")
            st.caption(f"Baseline: {fmt(comparison['previous'],'Closed Won Opportunity Value')} in {comparison['previous_period']}. Both calendar months are fully selected and contain recorded wins. This compares observed values in the CSV, not historical pipeline snapshots or guaranteed export completeness.")
    with st.container(border=True):
        st.subheader('Key insights')
        for insight in key_insights(frame,metrics): st.write('• '+insight)
    with st.expander('Supporting operating metrics'):
        cards(metrics,['Open Opportunity Count','Closed Won Deals','Average Won Sales Cycle','Overdue Pipeline Value'])
        if metrics['Pipeline Coverage'] is not None: cards(metrics,['Pipeline Coverage'])
