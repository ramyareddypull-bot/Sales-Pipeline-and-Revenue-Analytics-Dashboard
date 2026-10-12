"""Additional descriptive insights; the financial engine remains unchanged."""
import pandas as pd
from utils.metrics import stage_summary,compute_sales_performance


def risk_summary(frame):
    opened=frame.loc[frame.status.eq('Open')]
    return pd.DataFrame([{'Risk Category':label,'Opportunity Count':int(opened[flag].sum()),
                          'Pipeline Amount':float(opened.loc[opened[flag],'amount_usd'].sum())}
                         for label,flag in [('Overdue','overdue'),('Inactive','stale'),('Stalled','stalled')]])


def key_insights(frame,metrics):
    insights=[]
    stages=stage_summary(frame,True)
    if metrics['Open Pipeline']>0:
        top=stages.loc[stages['Total Pipeline Amount'].idxmax()]
        insights.append(f"{top['Stage']} holds the largest open pipeline: ${top['Total Pipeline Amount']:,.0f}.")
        share=metrics['Overdue Pipeline Value']/metrics['Open Pipeline']*100
        insights.append(f"{share:.1f}% of open pipeline is overdue (${metrics['Overdue Pipeline Value']:,.0f}).")
    regions=compute_sales_performance(frame,('region',))
    if not regions.empty and regions['Closed Won Opportunity Value'].max()>0:
        top=regions.iloc[0]
        insights.append(f"{top['region']} leads Closed Won value at ${top['Closed Won Opportunity Value']:,.0f}.")
    if not frame.empty:
        deal=frame.loc[frame.amount_usd.idxmax()]
        insights.append(f"Largest opportunity in this cohort: {deal.opportunity_name} ({deal.opportunity_id}), ${deal.amount_usd:,.0f} — {deal.stage}.")
    return insights


def closed_won_comparison(frame,analysis_date,close_range):
    """Two complete calendar months only, both fully selected, with observed wins.

    A CSV cannot prove completeness of the export. This comparison describes
    recorded closed outcomes and never asserts an earlier pipeline balance.
    """
    if not close_range or len(close_range)!=2: return None
    current=pd.Timestamp(analysis_date).to_period('M')-1
    previous=current-1
    if pd.Timestamp(close_range[0])>previous.start_time or pd.Timestamp(close_range[1])<current.end_time.normalize(): return None
    won=frame.loc[frame.stage.eq('Closed Won')]
    periods=won.close_date.dt.to_period('M')
    now=won.loc[periods.eq(current)]
    before=won.loc[periods.eq(previous)]
    if now.empty or before.empty or before.amount_usd.sum()<=0: return None
    amount=float(now.amount_usd.sum()); baseline=float(before.amount_usd.sum())
    return {'current':amount,'previous':baseline,'change_pct':(amount/baseline-1)*100,
            'current_period':current.strftime('%B %Y'),'previous_period':previous.strftime('%B %Y')}
