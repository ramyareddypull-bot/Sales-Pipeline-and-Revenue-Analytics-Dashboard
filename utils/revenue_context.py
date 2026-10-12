"""Bounded, JSON-safe facts for a future Revenue Analyst tab; no external calls."""
from dataclasses import dataclass
from hashlib import sha256
import json
import pandas as pd
from utils.data_cleaning import calculate_derived_columns
from utils.metrics import (compute_pipeline_metrics, compute_sales_performance,
                           compute_forecast_metrics, stage_summary, revenue_trend)
from utils.dashboard_metrics import risk_summary, closed_won_comparison

MAX_CONTEXT_CHARS = 60000
GROUP_LIMIT = 20
RECORD_LIMIT = 40
RECORD_COLUMNS = ['opportunity_id','account_name','opportunity_name','owner','sales_team',
                  'region','industry','stage','amount_usd','probability_pct','weighted_amount',
                  'forecast_category','close_date','days_in_stage','days_since_activity',
                  'risk_reason','risk_checks_incomplete']
GROUP_METRICS = ['Total Opportunities','Closed Won Deals','Closed Lost Deals','Win Rate %',
                 'Closed Won Opportunity Value','Open Pipeline','Weighted Pipeline']


class ContextError(ValueError):
    """The requested scope cannot be safely represented within the context budget."""


@dataclass(frozen=True)
class RevenueContext:
    """Opaque scope token invalidates chat when data, filters or analysis date change."""
    scope_id: str
    json_data: str


def records(frame):
    # Pandas emits proper nulls for NaN/NaT rather than non-standard JSON NaN.
    return json.loads(frame.to_json(orient='records',date_format='iso'))


def build_revenue_context(filtered, *, analysis_date, close_range, selections,
                          dataset_id, question='', revenue_target=None):
    """Accept ONLY the current globally filtered, validated opportunity dataframe.

    Selection metadata is descriptive, not a replacement for filtering. Rankings,
    rates, comparisons and risk unions are calculated here with existing functions.
    No whole-CSV fallback or global session cache is used.
    """
    if len(question)>4000:
        raise ContextError('Please keep the question within 4,000 characters.')
    frame=calculate_derived_columns(filtered,analysis_date)
    metrics=compute_pipeline_metrics(frame,revenue_target)
    weighted=metrics['Weighted Pipeline']
    gap=None if weighted is None else metrics['Open Pipeline']-weighted
    scope={'dataset_id':str(dataset_id),'analysis_date':str(analysis_date),
           'close_date_range':[str(d) for d in close_range],
           'filters':{k:list(v) for k,v in selections.items()},'record_count':len(frame),
           'revenue_target':revenue_target}
    scope_id=sha256((json.dumps(scope,sort_keys=True)+frame.sort_values('opportunity_id').to_json(orient='records',date_format='iso')).encode()).hexdigest()
    rankings={}
    for dimension,sort_by in [('sales_team','Win Rate %'),('owner','Closed Won Opportunity Value'),
                               ('industry','Closed Won Opportunity Value'),('region','Closed Won Opportunity Value'),
                               ('lead_source','Win Rate %')]:
        dims=('owner','sales_team') if dimension=='owner' else (dimension,)
        grouped=compute_sales_performance(frame,dims)
        if grouped.empty:
            rankings[dimension]={'groups_total':0,'groups_included':0,'rows':[]}; continue
        ranked=grouped.sort_values(sort_by,ascending=False,na_position='last',kind='stable')
        included=ranked.head(GROUP_LIMIT)
        rankings[dimension]={'ranked_by':sort_by,'groups_total':len(grouped),'groups_included':len(included),
                             'rows':records(included[list(dims)+GROUP_METRICS])}
    risks=risk_summary(frame).sort_values('Pipeline Amount',ascending=False,kind='stable')
    monthly=revenue_trend(frame,'Closed Won Opportunity Value','Monthly').tail(24)
    monthly_rows=records(monthly)
    for index,row in enumerate(monthly_rows):
        row['change_pct_vs_previous_calendar_month']=None
        if index:
            previous=monthly.iloc[index-1]; current=monthly.iloc[index]
            this_period=current.Period.to_period('M'); prior_period=previous.Period.to_period('M')
            complete=(len(close_range)==2 and pd.Timestamp(close_range[0])<=prior_period.start_time
                      and pd.Timestamp(close_range[1])>=this_period.end_time.normalize()
                      and this_period<pd.Timestamp(analysis_date).to_period('M'))
            if complete and this_period.ordinal-prior_period.ordinal==1 and previous.Value>0:
                row['change_pct_vs_previous_calendar_month']=float((current.Value/previous.Value-1)*100)
    # Retrieve explicit IDs/names mentioned in this question, then highest-value risk
    # and largest deals. Never read opportunities outside the caller's cohort.
    query=question.casefold()
    matching=pd.Series(False,index=frame.index)
    if query:
        for col in ('opportunity_id','account_name','owner','sales_team','industry','lead_source'):
            matching |= frame[col].map(lambda value: str(value).casefold() in query if str(value) not in ('','Unknown') else False)
    relevant=frame.loc[matching].sort_values('amount_usd',ascending=False).head(20)
    risky=frame.loc[frame.at_risk].sort_values('amount_usd',ascending=False).head(20)
    largest=frame.sort_values('amount_usd',ascending=False).head(20)
    selected=pd.concat([relevant,risky,largest]).drop_duplicates('opportunity_id').head(RECORD_LIMIT)
    payload={'scope':scope,'metrics':metrics,'weighted_pipeline_explanation':{'open_minus_weighted_usd':gap,
             'weighted_share_of_open_pct':weighted/metrics['Open Pipeline']*100 if weighted is not None and metrics['Open Pipeline']>0 else None,
             'formula':'Sum of open opportunity amount × supplied probability / 100; closed deals excluded.'},
             'rankings':rankings,'open_stages':records(stage_summary(frame,True)),
             'forecast_categories':records(compute_forecast_metrics(frame)),
             'risk_categories_ranked_by_amount':records(risks),
             'monthly_closed_won':monthly_rows,
             'latest_complete_month_comparison':closed_won_comparison(frame,analysis_date,close_range),
             'opportunities':records(selected[RECORD_COLUMNS]),
             'detail_coverage':{'cohort_records':len(frame),'included_records':len(selected),
                                'selection':'Mentioned IDs/names first, then largest at-risk deals, then largest deals; at most 40 records.',
                                'monthly_limit':24,'ranking_group_limit':GROUP_LIMIT},
             'limitations':['Current CSV snapshot, not live Salesforce or historical pipeline snapshots.',
                            'Closed Won value is not recognized accounting revenue or ARR.',
                            'Risk categories overlap; unique risk totals are in metrics. Missing risk dates do not imply safety.',
                            'Rates exclude open deals; group win-rate denominators are supplied. Small samples are not evidence of causation.',
                            'No external news, causal explanations, probability predictions, targets or marketing costs may be inferred.',
                            'Monthly comparisons cover recorded outcomes only; missing months are not imputed and export completeness is unknown.']}
    try:
        serialized=json.dumps(payload,allow_nan=False,default=str)
    except ValueError:
        raise ContextError('Context contains unsupported non-finite metrics.') from None
    if len(serialized)>MAX_CONTEXT_CHARS:
        raise ContextError('This filtered context exceeds the AI size limit. Narrow the filters before requesting analysis.')
    return RevenueContext(scope_id,serialized)
