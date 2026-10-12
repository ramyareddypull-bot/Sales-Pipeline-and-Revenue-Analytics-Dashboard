import streamlit as st
from utils.filters import FILTER_FIELDS,DATE_PRESETS,apply_filters,cascade_filters,date_preset_range


def reset_filters(frame):
    st.session_state['date_preset']='All Dates'
    st.session_state['close_range']=(frame.close_date.min().date(),frame.close_date.max().date())
    for field in FILTER_FIELDS: st.session_state['filter_'+field]=[]
    st.session_state['deal_search']=''
    for key in list(st.session_state):
        if key.startswith('drill_') or key=='selected_opportunity': st.session_state.pop(key,None)


def clear_field(field):
    st.session_state['filter_'+field]=[]


def render_sidebar(frame,fingerprint,analysis_date):
    if st.session_state.get('filter_dataset')!=fingerprint:
        reset_filters(frame)
        st.session_state['filter_dataset']=fingerprint
    with st.sidebar:
        st.subheader('Explore your pipeline')
        st.button('Reset All Filters',on_click=reset_filters,args=(frame,),width='stretch',type='primary')
        preset=st.selectbox('Close date preset',DATE_PRESETS,key='date_preset')
        if preset=='Custom Range':
            dates=st.date_input('Close Date Range',key='close_range',help='You may select dates beyond the file’s current range.')
        else:
            dates=date_preset_range(preset,analysis_date,frame)
        st.caption('Actual close dates for closed deals; expected dates for open deals. All Dates includes future expected closes.')
        if dates and len(dates)==2: st.caption(f'{dates[0]:%b %d, %Y} → {dates[1]:%b %d, %Y}')
        selections={field:st.session_state.get('filter_'+field,[]) for field in FILTER_FIELDS}
        available,valid,removed=cascade_filters(frame,dates,selections)
        for field in FILTER_FIELDS:
            if st.session_state.get('filter_'+field,[])!=valid[field]: st.session_state['filter_'+field]=valid[field]
        if removed:
            st.warning('Cleared selections unavailable under the new filters: '+ '; '.join(f'{FILTER_FIELDS[k]}: {", ".join(v)}' for k,v in removed.items()))
        for field,label in FILTER_FIELDS.items():
            valid[field]=st.multiselect(label,available[field],key='filter_'+field,placeholder='All')
        st.caption('Options cascade from top to bottom. Region narrows team and owner choices. Empty selections mean All.')
        with st.expander('Display & revenue planning'):
            st.toggle('Compact layout',key='compact_layout',help='Stack charts and use fewer KPI columns for narrower windows.')
            enabled=st.checkbox('Supply a revenue target')
            target=st.number_input('Revenue target for this filtered cohort (USD)',min_value=0.0,value=0.0,step=10000.0,disabled=not enabled)
            st.caption('Match the target period and scope to your selected cohort.')
    if not dates or len(dates)!=2: st.info('Select both a start and end close date.')
    return apply_filters(frame,dates,valid),target if enabled and target>0 else None,dates,valid


def active_filters(selections):
    active={field:values for field,values in selections.items() if values}
    if active:
        with st.expander(f'Active category filters · {len(active)}',expanded=True):
            for field,values in active.items():
                left,right=st.columns([5,1])
                left.write(f'**{FILTER_FIELDS[field]}:** '+', '.join(values))
                right.button('Clear',key='clear_'+field,on_click=clear_field,args=(field,),help='Clear '+FILTER_FIELDS[field])
