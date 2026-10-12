import plotly.express as px
import streamlit as st
from components.common import table,chart,cards,GREEN,RED,pair
from components.opportunity_table import render_opportunity_explorer,render_opportunity_details
from components.trend_chart import render_trend
from utils.metrics import cycle_summary,loss_summary


def render_tab_deal_deep_dive(frame,metrics):
    st.subheader('Opportunity explorer')
    matches=render_opportunity_explorer(frame)
    render_opportunity_details(matches)
    st.subheader('Revenue trends over time')
    render_trend(frame,'detail_trend')
    with st.expander('Won sales-cycle analysis',expanded=True):
        cards(metrics,['Average Won Sales Cycle','Median Won Sales Cycle'])
        won=frame.loc[frame.stage.eq('Closed Won')]
        if won.empty: st.info('No Closed Won opportunities available for sales-cycle analysis.')
        else:
            chart(px.histogram(won,x='sales_cycle_days',nbins=24,color_discrete_sequence=[GREEN],labels={'sales_cycle_days':'Sales cycle (days)'}))
            a,b=pair()
            with a:
                st.markdown('**By customer segment**'); table(cycle_summary(frame,'segment'))
            with b:
                st.markdown('**By sales owner**'); table(cycle_summary(frame,'owner'))
    with st.expander('Loss reason analysis'):
        losses=loss_summary(frame)
        if losses.empty: st.info('No Closed Lost opportunities in this cohort.')
        else:
            fig=px.bar(losses,x='Lost Opportunity Count',y='loss_reason',orientation='h',color_discrete_sequence=[RED],labels={'loss_reason':'Loss Reason'})
            fig.update_yaxes(autorange='reversed'); chart(fig)
            table(losses)
