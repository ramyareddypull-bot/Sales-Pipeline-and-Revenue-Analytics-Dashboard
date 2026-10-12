"""Validate snapshot data without inventing missing financial or timing inputs."""
import numpy as np
import pandas as pd

STAGES = ['Prospecting','Qualification','Discovery','Proposal','Negotiation','Closed Won','Closed Lost']
OPEN_STAGES = STAGES[:5]
FORECASTS = ['Pipeline','Best Case','Commit','Closed','Omitted']
COLUMNS = ['opportunity_id','account_id','account_name','opportunity_name','owner','sales_team','region','industry','segment','product','lead_source','opportunity_type','created_date','close_date','stage','probability_pct','amount_usd','forecast_category','stage_entered_date','last_activity_date','next_step','loss_reason']
DATES = ['created_date','close_date','stage_entered_date','last_activity_date']


def validate_data(frame):
    missing = [c for c in COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))
    if frame.columns.duplicated().any():
        raise ValueError('CSV headers must be unique.')


def clean_data(raw):
    """Reject ambiguous identities/core financial records, isolate optional failures.

    All occurrences of duplicate opportunity IDs are rejected; choosing one could
    silently double count revenue or select an unsupported snapshot version.
    Invalid probability only excludes weighted calculations. Missing optional
    timestamps only exclude their respective age/risk checks.
    """
    frame = raw.copy()
    frame.columns = frame.columns.str.strip()
    validate_data(frame)
    frame['csv_row'] = np.arange(len(frame)) + 2
    for col in COLUMNS:
        frame[col] = frame[col].astype('string').str.strip().replace('', pd.NA)
    missing_fields = frame[COLUMNS].isna().sum()
    duplicate = frame.opportunity_id.notna() & frame.opportunity_id.duplicated(keep=False)
    duplicate_ids = sorted(frame.loc[duplicate,'opportunity_id'].unique().tolist())
    for col in DATES:
        frame[col] = pd.to_datetime(frame[col],errors='coerce',format='mixed',utc=True).dt.tz_convert(None).dt.normalize()
    for col in ('amount_usd','probability_pct'):
        text = frame[col].str.replace(r'[$,]', '', regex=True) if col=='amount_usd' else frame[col]
        frame[col] = pd.to_numeric(text,errors='coerce').astype(float).replace([np.inf,-np.inf],np.nan)
    rejected = pd.Series(False,index=frame.index)
    issues=[]
    def flag(mask,field,message,critical=False):
        nonlocal rejected
        mask=mask.fillna(False)
        issues.extend({'CSV Row':int(frame.at[i,'csv_row']),'Opportunity ID':str(frame.at[i,'opportunity_id']),
                       'Field':field,'Issue':message,'Impact':'Record rejected' if critical else 'Affected calculation unavailable'} for i in frame.index[mask])
        if critical:
            rejected |= mask
    flag(frame.opportunity_id.isna(),'opportunity_id','Missing opportunity ID',True)
    flag(duplicate,'opportunity_id','Duplicate ID; all occurrences excluded',True)
    flag(frame.amount_usd.isna() | (frame.amount_usd<0),'amount_usd','Missing, nonnumeric or negative amount',True)
    flag(~frame.stage.isin(STAGES),'stage','Missing or unrecognized stage',True)
    for col in ('created_date','close_date'):
        flag(frame[col].isna(),col,'Missing or invalid required date',True)
    flag(frame.created_date>frame.close_date,'close_date','Close date precedes created date',True)
    bad_probability=frame.probability_pct.isna() | ~frame.probability_pct.between(0,100)
    flag(bad_probability,'probability_pct','Missing or invalid probability; excluded from weighted amounts')
    frame.loc[bad_probability,'probability_pct']=np.nan
    for col in ('stage_entered_date','last_activity_date'):
        bad=frame[col].isna() | (frame[col]<frame.created_date) | (frame.stage.isin(STAGES[-2:]) & (frame[col]>frame.close_date))
        flag(bad,col,'Missing, invalid or inconsistent optional date')
        frame.loc[bad,col]=pd.NaT
    flag(~frame.forecast_category.isin(FORECASTS),'forecast_category','Unknown forecast category; retained as Unknown')
    frame.loc[~frame.forecast_category.isin(FORECASTS),'forecast_category']='Unknown'
    text_cols=[c for c in COLUMNS if c not in DATES+['amount_usd','probability_pct']]
    for col in text_cols:
        frame[col]=frame[col].fillna('Not provided' if col=='next_step' else 'Unknown')
    report={'total_records':len(raw),'valid_records':int((~rejected).sum()),'rejected_records':int(rejected.sum()),
            'duplicate_ids':duplicate_ids,'duplicate_records':int(duplicate.sum()),
            'missing_fields':{k:int(v) for k,v in missing_fields.items() if v},'issues':issues}
    return frame.loc[~rejected].reset_index(drop=True),report


def calculate_derived_columns(frame,analysis_date):
    data=frame.copy()
    as_of=pd.Timestamp(analysis_date).normalize()
    opened=data.stage.isin(OPEN_STAGES)
    closed=data.stage.isin(STAGES[-2:])
    data['status']=data.stage.where(~opened,'Open')
    data['weighted_amount']=data.amount_usd*data.probability_pct/100
    data['sales_cycle_days']=(data.close_date-data.created_date).dt.days.where(closed)
    data['opportunity_age_days']=(as_of-data.created_date).dt.days.where(opened)
    data.loc[data.opportunity_age_days<0,'opportunity_age_days']=np.nan
    data['days_in_stage']=(as_of-data.stage_entered_date).dt.days
    data['days_since_activity']=(as_of-data.last_activity_date).dt.days
    for col in ('days_in_stage','days_since_activity'):
        data.loc[data[col]<0,col]=np.nan
    data['days_until_close']=(data.close_date-as_of).dt.days.where(opened)
    data['overdue']=opened & (data.close_date<as_of)
    data['stale']=opened & (data.days_since_activity>14)
    data['stalled']=opened & (data.days_in_stage>30)
    data['at_risk']=data[['overdue','stale','stalled']].any(axis=1)
    data['risk_reason']=[', '.join(label for flag,label in zip(flags,['Overdue','Inactive','Stalled']) if flag)
                         for flags in data[['overdue','stale','stalled']].itertuples(index=False,name=None)]
    data['risk_checks_incomplete']=opened & (data.days_since_activity.isna() | data.days_in_stage.isna())
    return data
