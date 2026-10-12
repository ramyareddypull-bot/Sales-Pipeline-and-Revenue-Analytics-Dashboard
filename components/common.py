"""Theme-aware native cards, tables and reusable chart presentation."""
import pandas as pd
import plotly.express as px
import streamlit as st

BLUE='#2563EB'; INDIGO='#6366F1'; GREEN='#16A34A'; RED='#DC2626'; AMBER='#F59E0B'; SLATE='#64748B'
STAGE_COLORS={'Prospecting':'#93B4F9','Qualification':'#6B96F3','Discovery':BLUE,'Proposal':INDIGO,'Negotiation':'#8172CF','Closed Won':GREEN,'Closed Lost':RED}
LABELS={'owner':'Sales Rep','sales_team':'Sales Team','region':'Region','industry':'Industry','segment':'Customer Segment',
        'opportunity_type':'Opportunity Type','lead_source':'Lead Source','opportunity_id':'Opportunity ID','account_name':'Account Name',
        'opportunity_name':'Opportunity Name','stage':'Stage','amount_usd':'Amount USD','close_date':'Close Date',
        'created_date':'Created Date','forecast_category':'Forecast Category','probability_pct':'Probability %',
        'weighted_amount':'Weighted Amount','days_in_stage':'Days in Current Stage','days_since_activity':'Days Since Last Activity',
        'next_step':'Next Step','loss_reason':'Loss Reason','product':'Product','risk_reason':'Risk Reason',
        'last_activity_date':'Last Activity','stage_entered_date':'Stage Entered'}
CURRENCY={'Open Pipeline','Closed Won Opportunity Value','Closed Lost Value','Weighted Pipeline','Average Won Deal Size',
          'Overdue Pipeline Value','At-Risk Pipeline Value','Commit Pipeline','Best Case Pipeline','Amount USD','Weighted Amount',
          'Total Amount','Total Pipeline Amount','Weighted Pipeline Amount','Pipeline Amount','Total Lost Value'}
HELP={'Open Pipeline':'Sum of amounts for open opportunities. Closed Won and Closed Lost are excluded.',
      'Closed Won Opportunity Value':'Booked opportunity value for Closed Won deals; not recognized accounting revenue or ARR.',
      'Weighted Pipeline':'Open deal amount × source probability / 100. N/A if any open probability is missing.',
      'Win Rate %':'Won opportunity count divided by won + lost count. Open deals are excluded.',
      'Average Won Deal Size':'Mean amount of Closed Won opportunities.',
      'Average Won Sales Cycle':'Mean days between creation and actual close for Closed Won deals.',
      'Median Won Sales Cycle':'Median days between creation and actual close for Closed Won deals.',
      'Overdue Pipeline Value':'Open deals with expected close before the analysis date.',
      'At-Risk Pipeline Value':'Unique open deals that are overdue, inactive >14 days, or stalled >30 days. Counted once.',
      'Commit Pipeline':'Open opportunities whose forecast category is Commit.',
      'Best Case Pipeline':'Open opportunities whose forecast category is Best Case.',
      'Pipeline Coverage':'Open pipeline / your explicit revenue target for this cohort.'}


def fmt(value,name,compact=False):
    if value is None or pd.isna(value): return 'N/A'
    if name in CURRENCY:
        if compact and abs(value)>=1e6: return f'${value/1e6:,.2f}M'
        if compact and abs(value)>=1e3: return f'${value/1e3:,.1f}K'
        return f'${value:,.0f}'
    if '%' in name: return f'{value:,.2f}%'
    if 'Cycle' in name or 'Days' in name: return f'{value:,.1f} days'
    if name=='Pipeline Coverage': return f'{value:,.2f}×'
    return f'{value:,.0f}'


def pair():
    return [st.container(),st.container()] if st.session_state.get('compact_layout') else st.columns(2,gap='large')


def cards(metrics,names):
    width=2 if st.session_state.get('compact_layout') else min(5,len(names))
    for offset in range(0,len(names),width):
        for col,name in zip(st.columns(width),names[offset:offset+width]):
            with col.container(border=True):
                st.metric(name,fmt(metrics.get(name),name,True),help=HELP.get(name,f'Calculated from the {metrics.get("Total Opportunities",0):,} selected opportunities.'))
                if name=='Open Pipeline': st.caption(f'{metrics["Open Opportunity Count"]:,} open opportunities')
                elif name=='Win Rate %': st.caption(f'{metrics["Closed Won Deals"]:,} won / {metrics["Closed Won Deals"]+metrics["Closed Lost Deals"]:,} closed')
                elif name in CURRENCY: st.caption('Exact value: '+fmt(metrics.get(name),name))


def table(frame,highlight=False,risk=False,opportunities=False):
    data=frame.rename(columns=LABELS)
    config={}
    for col in data:
        if col in CURRENCY: config[col]=st.column_config.NumberColumn(col,format='dollar')
        elif '%' in col: config[col]=st.column_config.NumberColumn(col,format='%.2f%%')
        elif pd.api.types.is_datetime64_any_dtype(data[col]): config[col]=st.column_config.DateColumn(col,format='YYYY-MM-DD')
        elif pd.api.types.is_numeric_dtype(data[col]): config[col]=st.column_config.NumberColumn(col,format='localized')
    styled=data.style
    if highlight:
        for col in ('Win Rate %','Closed Won Opportunity Value'):
            if col in data:
                peak=data[col].max()
                styled=styled.map(lambda value,p=peak:'background-color: rgba(22,163,74,0.18); font-weight:600' if pd.notna(value) and value==p else '',subset=[col])
    if opportunities and 'Stage' in data:
        styled=styled.map(lambda v:'background-color: rgba(22,163,74,0.18)' if v=='Closed Won' else 'background-color: rgba(220,38,38,0.18)' if v=='Closed Lost' else '',subset=['Stage'])
        if 'Amount USD' in data and len(data):
            cutoff=data['Amount USD'].quantile(.9)
            styled=styled.map(lambda v:'font-weight:700' if pd.notna(v) and v>=cutoff else '',subset=['Amount USD'])
    if risk or opportunities:
        if 'Risk Reason' in data:
            styled=styled.map(lambda v:'background-color: rgba(220,38,38,0.16)' if 'Overdue' in str(v) else 'background-color: rgba(245,158,11,0.18)' if v else '',subset=['Risk Reason'])
        if 'overdue' in frame and 'Close Date' in data:
            styled=styled.apply(lambda col:['background-color: rgba(220,38,38,0.16)' if flag else '' for flag in frame.overdue],subset=['Close Date'])
        if 'stale' in frame and 'Days Since Last Activity' in data:
            styled=styled.apply(lambda col:['background-color: rgba(245,158,11,0.18)' if flag else '' for flag in frame.stale],subset=['Days Since Last Activity'])
    visible=data.columns.difference(['overdue','stale','stalled','at_risk'],sort=False).tolist()
    st.dataframe(styled if highlight or risk or opportunities else data,hide_index=True,width='stretch',column_config=config,column_order=visible)


def style_chart(fig,y=None,horizontal=False,height=360):
    fig.update_layout(height=height,margin=dict(l=12,r=12,t=35,b=15),legend=dict(orientation='h',y=1.12,x=0),
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',hoverlabel=dict(namelength=-1))
    if y in CURRENCY:
        if horizontal: fig.update_xaxes(tickprefix='$',tickformat=',.0f')
        else: fig.update_yaxes(tickprefix='$',tickformat=',.0f')
    elif y and '%' in y:
        if horizontal: fig.update_xaxes(ticksuffix='%')
        else: fig.update_yaxes(ticksuffix='%')
    return fig


def chart(fig,y=None,horizontal=False,height=360,key=None):
    st.plotly_chart(style_chart(fig,y,horizontal,height),width='stretch',theme='streamlit',config={'displaylogo':False},key=key)


def bar(data,x,y,color=None,horizontal=False):
    if data.empty:
        st.info('No matching opportunities for this breakdown.'); return
    fig=px.bar(data,x=y if horizontal else x,y=x if horizontal else y,color=color,
               orientation='h' if horizontal else 'v',color_discrete_sequence=[BLUE,GREEN,INDIGO],labels=LABELS)
    axis='x' if horizontal else 'y'
    if y in CURRENCY:
        category_axis='y' if horizontal else 'x'
        fig.update_traces(hovertemplate=f'%{{{category_axis}}}<br>$%{{{axis}:,.0f}}<extra></extra>')
    elif '%' in y: fig.update_traces(hovertemplate=f'%{{{"y" if horizontal else "x"}}}<br>%{{{axis}:.2f}}%<extra></extra>')
    if horizontal: fig.update_yaxes(autorange='reversed')
    chart(fig,y,horizontal,height=max(330,min(800,len(data)*34+80)) if horizontal else 360)
