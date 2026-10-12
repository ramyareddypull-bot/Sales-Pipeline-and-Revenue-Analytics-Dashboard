"""Single financial definition used by all groupings, charts, and tables."""
import pandas as pd
from utils.data_cleaning import STAGES, FORECASTS


def compute_win_rate(frame):
    wins=frame.loc[frame.stage.eq('Closed Won'),'opportunity_id'].nunique()
    losses=frame.loc[frame.stage.eq('Closed Lost'),'opportunity_id'].nunique()
    return wins/(wins+losses)*100 if wins+losses else None


def mean_or_none(series):
    value=series.mean()
    return None if pd.isna(value) else float(value)


def weighted_total(frame):
    # Incomplete probability coverage must not masquerade as a complete forecast.
    return None if frame.weighted_amount.isna().any() else float(frame.weighted_amount.sum())


def compute_pipeline_metrics(frame,revenue_target=None):
    opened=frame.loc[frame.status.eq('Open')]
    won=frame.loc[frame.stage.eq('Closed Won')]
    lost=frame.loc[frame.stage.eq('Closed Lost')]
    total=float(opened.amount_usd.sum())
    return {'Total Opportunities':frame.opportunity_id.nunique(),'Open Opportunity Count':opened.opportunity_id.nunique(),
            'Closed Won Deals':won.opportunity_id.nunique(),'Closed Lost Deals':lost.opportunity_id.nunique(),
            'Open Pipeline':total,'Closed Won Opportunity Value':float(won.amount_usd.sum()),
            'Closed Lost Value':float(lost.amount_usd.sum()),'Weighted Pipeline':weighted_total(opened),
            'Win Rate %':compute_win_rate(frame),'Average Won Deal Size':mean_or_none(won.amount_usd),
            'Average Won Sales Cycle':mean_or_none(won.sales_cycle_days),'Median Won Sales Cycle':None if won.empty else float(won.sales_cycle_days.median()),
            'Overdue Pipeline Value':float(opened.loc[opened.overdue,'amount_usd'].sum()),
            'At-Risk Pipeline Value':float(opened.loc[opened.at_risk,'amount_usd'].sum()),
            'At-Risk Opportunity Count':opened.loc[opened.at_risk,'opportunity_id'].nunique(),
            'Commit Pipeline':float(opened.loc[opened.forecast_category.eq('Commit'),'amount_usd'].sum()),
            'Best Case Pipeline':float(opened.loc[opened.forecast_category.eq('Best Case'),'amount_usd'].sum()),
            'Pipeline Coverage':total/revenue_target if revenue_target and revenue_target>0 else None,
            'Missing Open Probabilities':int(opened.probability_pct.isna().sum()),
            'Incomplete Risk Checks':int(opened.risk_checks_incomplete.sum())}


def compute_sales_performance(frame,dimensions=('owner','sales_team')):
    records=[]
    for keys,group in frame.groupby(list(dimensions),dropna=False,sort=True):
        keys=keys if isinstance(keys,tuple) else (keys,)
        records.append({**dict(zip(dimensions,keys)),**compute_pipeline_metrics(group)})
    return pd.DataFrame(records).sort_values('Closed Won Opportunity Value',ascending=False) if records else pd.DataFrame()


def compute_forecast_metrics(frame):
    opened=frame.loc[frame.status.eq('Open')]
    total=opened.amount_usd.sum()
    records=[]
    for category in FORECASTS+['Unknown']:
        group=opened.loc[opened.forecast_category.eq(category)]
        if category not in FORECASTS[:3] and group.empty:
            continue
        records.append({'Forecast Category':category,'Opportunity Count':len(group),'Total Amount':float(group.amount_usd.sum()),
                        'Weighted Amount':weighted_total(group),'% of Open Pipeline':float(group.amount_usd.sum()/total*100) if total else None})
    return pd.DataFrame(records)


def stage_summary(frame,open_only=False):
    stages=STAGES[:5] if open_only else STAGES
    records=[]
    for stage in stages:
        group=frame.loc[frame.stage.eq(stage)]
        records.append({'Stage':stage,'Opportunity Count':len(group),'Total Pipeline Amount':float(group.amount_usd.sum()),'Weighted Pipeline Amount':weighted_total(group)})
    return pd.DataFrame(records)


TREND_METRICS={'Closed Won Opportunity Value':('Closed Won','close_date','amount_usd'),
               'Closed Won Deal Count':('Closed Won','close_date',None),
               'Created Opportunity Count':(None,'created_date',None),
               'Created Opportunity Amount':(None,'created_date','amount_usd'),
               'Closed Lost Value':('Closed Lost','close_date','amount_usd')}


def revenue_trend(frame,metric,frequency):
    stage,date_col,value=TREND_METRICS[metric]
    data=frame.loc[frame.stage.eq(stage)].copy() if stage else frame.copy()
    if data.empty:
        return pd.DataFrame(columns=['Period','Value'])
    data['Period']=data[date_col].dt.to_period({'Daily':'D','Weekly':'W-SUN','Monthly':'M','Quarterly':'Q'}[frequency]).dt.start_time
    grouped=data.groupby('Period')
    result=grouped[value].sum() if value else grouped.opportunity_id.nunique()
    return result.rename('Value').reset_index()


def cycle_summary(frame,dimension):
    won=frame.loc[frame.stage.eq('Closed Won')]
    return won.groupby(dimension).agg(**{'Won Deals':('opportunity_id','nunique'),'Average Days':('sales_cycle_days','mean'),'Median Days':('sales_cycle_days','median')}).reset_index()


def loss_summary(frame):
    lost=frame.loc[frame.stage.eq('Closed Lost')]
    result=lost.groupby('loss_reason').agg(**{'Lost Opportunity Count':('opportunity_id','nunique'),'Total Lost Value':('amount_usd','sum')}).reset_index()
    result['% of Closed Lost Deals']=result['Lost Opportunity Count']/len(lost)*100 if len(lost) else pd.Series(dtype=float)
    return result.sort_values('Lost Opportunity Count',ascending=False)


def export_csv(frame):
    """Keep spreadsheet clients from executing user-controlled text as formulas."""
    output=frame.copy()
    for col in output.select_dtypes(include=['object','string']).columns:
        output[col]=output[col].map(lambda v: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v)
    return output.to_csv(index=False).encode('utf-8-sig')
