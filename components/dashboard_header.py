import streamlit as st
from utils.metrics import export_csv


def render_header(name,frame,total,analysis_date,dates,selections):
    title,meta=st.columns([3,2],gap='large')
    with title:
        st.caption('REVENUE WORKSPACE  /  CSV ANALYTICS')
        st.title('Sales Pipeline & Revenue Analytics')
        st.write('Revenue intelligence across your pipeline, forecasts, sales teams, and opportunities.')
    with meta:
        with st.container(border=True):
            st.caption('ACTIVE DATASET')
            st.write(name)
            st.caption(f'Analysis date · {analysis_date:%b %d, %Y} · {len(frame) if frame is not None else 0:,} filtered opportunities')
            if frame is not None:
                st.download_button('Export Dashboard Data',export_csv(frame.drop(columns=['csv_row'],errors='ignore')),'dashboard_opportunities.csv','text/csv',width='stretch',key='dashboard_export')
    count=sum(bool(values) for values in selections.values()) + int(st.session_state.get('date_preset','All Dates')!='All Dates')
    range_label=f'{dates[0]:%b %d, %Y} – {dates[1]:%b %d, %Y}' if dates and len(dates)==2 else 'Select a complete date range'
    st.caption(f'{len(frame) if frame is not None else 0:,} of {total:,} valid opportunities  ·  {count} active global filters  ·  Close dates: {range_label}')
