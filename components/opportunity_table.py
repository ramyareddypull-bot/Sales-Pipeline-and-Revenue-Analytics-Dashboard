import pandas as pd
import streamlit as st
from components.common import table,fmt
from utils.filters import search_opportunities
from utils.metrics import export_csv


def render_opportunity_explorer(frame):
    search=st.text_input('Search opportunity ID, name, account or owner',key='deal_search',placeholder='Search this filtered cohort…')
    left,right=st.columns([3,1])
    sort=left.selectbox('Default table sort',['Opportunity Amount','Expected / Actual Close Date','Probability','Days in Stage','Days Since Last Activity'])
    ascending=right.toggle('Ascending',value=False)
    fields={'Opportunity Amount':'amount_usd','Expected / Actual Close Date':'close_date','Probability':'probability_pct','Days in Stage':'days_in_stage','Days Since Last Activity':'days_since_activity'}
    matches=search_opportunities(frame,search).sort_values(fields[sort],ascending=ascending,na_position='last',kind='stable')
    columns=['opportunity_id','opportunity_name','account_name','owner','region','segment','product','lead_source','opportunity_type','stage','probability_pct','amount_usd','weighted_amount','forecast_category','created_date','close_date','stage_entered_date','last_activity_date','days_in_stage','days_since_activity','risk_reason','next_step','loss_reason','overdue','stale']
    st.caption(f'{len(matches):,} table matches. Search and sort affect this table and download. Global metrics retain the sidebar-selected cohort.')
    if matches.empty: st.info('No opportunities match your search.')
    else: table(matches[columns],opportunities=True)
    st.download_button('Download filtered opportunities CSV',export_csv(matches.drop(columns=['csv_row'],errors='ignore')),'filtered_opportunities.csv','text/csv')
    return matches


def render_opportunity_details(frame):
    if frame.empty: return
    ids=frame.opportunity_id.tolist()
    if st.session_state.get('selected_opportunity') not in ids: st.session_state.pop('selected_opportunity',None)
    names=frame.set_index('opportunity_id').opportunity_name.to_dict()
    selected=st.selectbox('Select an opportunity',ids,format_func=lambda value:f'{value} · {names[value]}',key='selected_opportunity')
    row=frame.loc[frame.opportunity_id.eq(selected)].iloc[0]
    with st.expander('Opportunity details',expanded=True):
        st.subheader(row.opportunity_name)
        st.write(f'Account: {row.account_name} · Owner: {row.owner} · Team: {row.sales_team}')
        st.write(f'Stage: {row.stage} · Forecast: {row.forecast_category}')
        st.write(f"Amount: {fmt(row.amount_usd,'Amount USD')} · Probability: {fmt(row.probability_pct,'Probability %')}")
        st.write(f'Created: {row.created_date:%Y-%m-%d}')
        date_label='Expected close' if row.status=='Open' else 'Actual close'
        st.write(f'{date_label}: {row.close_date:%Y-%m-%d}')
        st.write(f"Current stage age: {fmt(row.days_in_stage,'Days')} · Last activity: {row.last_activity_date.date() if pd.notna(row.last_activity_date) else 'Unknown'}")
        st.write(f'Next step: {row.next_step}')
        if row.stage=='Closed Lost': st.write(f'Loss reason: {row.loss_reason}')
        if row.risk_reason: st.warning('Risk indicators: '+row.risk_reason)
