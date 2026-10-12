"""Global close-date filters, deterministic presets and hierarchical option cascades."""
import pandas as pd

# Upstream selections narrow downstream choices. Region therefore governs owners.
FILTER_FIELDS = {'region':'Region','sales_team':'Sales Team','owner':'Sales Owner',
                 'industry':'Industry','segment':'Customer Segment','product':'Product',
                 'opportunity_type':'Opportunity Type','stage':'Opportunity Stage',
                 'forecast_category':'Forecast Category','lead_source':'Lead Source'}
DATE_PRESETS = ['All Dates','Last 30 Days','Last 90 Days','This Quarter','Last Quarter','This Year','Custom Range']


def date_preset_range(preset, analysis_date, frame):
    day = pd.Timestamp(analysis_date).normalize()
    quarter = day.to_period('Q')
    if preset == 'Last 30 Days': return (day-pd.Timedelta(days=29)).date(), day.date()
    if preset == 'Last 90 Days': return (day-pd.Timedelta(days=89)).date(), day.date()
    if preset == 'This Quarter': return quarter.start_time.date(), quarter.end_time.date()
    if preset == 'Last Quarter': return (quarter-1).start_time.date(), (quarter-1).end_time.date()
    if preset == 'This Year': return day.replace(month=1,day=1).date(), day.replace(month=12,day=31).date()
    return frame.close_date.min().date(), frame.close_date.max().date()


def canonical_options(series):
    """One display label per case-insensitive value, without changing source data."""
    labels = {}
    for value in sorted(series.dropna().astype(str).unique()):
        labels.setdefault(value.strip().casefold(), value)
    return sorted(labels.values(), key=str.casefold)


def apply_filters(frame,close_range,selections):
    if not close_range or len(close_range)!=2:
        return frame.iloc[0:0].copy()
    mask=frame.close_date.between(pd.Timestamp(close_range[0]),pd.Timestamp(close_range[1]))
    for field,values in selections.items():
        if values:
            wanted={str(v).strip().casefold() for v in values}
            mask &= frame[field].astype('string').str.strip().str.casefold().isin(wanted)
    return frame.loc[mask].copy()


def cascade_filters(frame, close_range, selections):
    """Respect upstream priority and visibly report invalid downstream removals."""
    available, valid, removed = {}, {}, {}
    for field in FILTER_FIELDS:
        cohort = apply_filters(frame,close_range,valid)
        # Preserve category choices when date selection alone has no records.
        if apply_filters(frame,close_range,{}).empty:
            cohort = frame
        options = canonical_options(cohort[field])
        lookup = {v.casefold():v for v in options}
        old = selections.get(field,[])
        valid[field] = list(dict.fromkeys(lookup[str(v).casefold()] for v in old if str(v).casefold() in lookup))
        removed[field] = [v for v in old if str(v).casefold() not in lookup]
        available[field] = options
    return available,valid,{k:v for k,v in removed.items() if v}


def select_drilldown(frame, field, value):
    """Always start from the global cohort; drill-downs never modify global totals."""
    if value is None: return frame.iloc[0:0].copy()
    if field == 'risk':
        mapping={'Overdue':'overdue','Inactive':'stale','Stalled':'stalled'}
        return frame.loc[frame.status.eq('Open') & frame[mapping[value]]].copy() if value in mapping else frame.iloc[0:0].copy()
    if field == 'owner_team':
        owner,team=value
        return frame.loc[frame.owner.eq(owner) & frame.sales_team.eq(team)].copy()
    return frame.loc[frame[field].astype('string').str.casefold().eq(str(value).casefold())].copy()


def search_opportunities(frame, query):
    if not query.strip(): return frame.copy()
    mask=frame[['opportunity_id','opportunity_name','account_name','owner']].apply(
        lambda col:col.str.contains(query.strip(),case=False,regex=False,na=False)).any(axis=1)
    return frame.loc[mask].copy()
