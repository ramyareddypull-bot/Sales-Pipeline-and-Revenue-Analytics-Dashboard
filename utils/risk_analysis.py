import pandas as pd

AGE_LABELS=['0–30 days','31–60 days','61–90 days','91–180 days','Over 180 days']


def identify_at_risk_deals(frame):
    return frame.loc[frame.at_risk & frame.status.eq('Open')].sort_values('amount_usd',ascending=False).copy()


def pipeline_aging(frame):
    opened=frame.loc[frame.status.eq('Open')].copy()
    opened['Age Band']=pd.cut(opened.opportunity_age_days,bins=[-1,30,60,90,180,float('inf')],labels=AGE_LABELS)
    return opened.groupby('Age Band',observed=False).agg(**{'Opportunity Count':('opportunity_id','nunique'),'Pipeline Amount':('amount_usd','sum')}).reset_index()
