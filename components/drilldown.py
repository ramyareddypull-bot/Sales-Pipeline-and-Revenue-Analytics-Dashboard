"""Keyboard-accessible summary-to-record exploration shared by all charts."""
import streamlit as st
from components.common import table
from utils.filters import select_drilldown,canonical_options
from utils.metrics import export_csv


def clear_drilldown(key):
    st.session_state[key]=None


def render_drilldown(frame,field,label,key):
    if field=='risk': options=['Overdue','Inactive','Stalled']
    elif field=='owner_team': options=sorted(set(zip(frame.owner,frame.sales_team)))
    else: options=canonical_options(frame[field])
    state_key='drill_'+key
    field_key='drill_dimension_'+key
    if st.session_state.get(field_key)!=field:
        st.session_state[state_key]=None
        st.session_state[field_key]=field
    old=st.session_state.get(state_key)
    if old is not None and old not in options:
        st.session_state[state_key]=None
        st.caption(f'Cleared the {label.lower()} drill-down because it is outside the current filters.')
    with st.expander('Explore '+label.lower()+' opportunities',expanded=st.session_state.get(state_key) is not None):
        chosen=st.selectbox('Drill into '+label,options,index=None,placeholder='Choose a category',key=state_key,
                            format_func=(lambda item:' · '.join(item)) if field=='owner_team' else str)
        if chosen is None:
            st.caption('Choose a category to inspect and download its underlying opportunities. Global filters remain in effect.')
            return
        st.button('Clear selection',key='clear_'+state_key,on_click=clear_drilldown,args=(state_key,))
        selected=select_drilldown(frame,field,chosen)
        st.markdown('**Selected Opportunities**')
        st.caption(f'{label}: {chosen} · {len(selected):,} matching records · This selection narrows only this detail table.')
        if selected.empty: st.info('No opportunities match this drill-down in the current global cohort.')
        else:
            cols=['opportunity_id','account_name','opportunity_name','owner','stage','amount_usd','close_date','risk_reason','overdue','stale']
            table(selected[cols],opportunities=True)
        st.download_button('Download selected opportunities',export_csv(selected.drop(columns=['csv_row'],errors='ignore')),f'{key}_opportunities.csv','text/csv',key='download_'+key)
