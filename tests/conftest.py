from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import date
import pandas as pd
import pytest
from utils.data_cleaning import COLUMNS,clean_data,calculate_derived_columns

@pytest.fixture
def raw():
    rows=[]
    for i,(stage,amount,probability) in enumerate([('Prospecting',10000,20),('Proposal',20000,60),('Closed Won',15000,100),('Closed Lost',5000,0)]):
        row=dict.fromkeys(COLUMNS,'Example')
        row.update(opportunity_id=f'00{i}',account_id=f'000{i}',stage=stage,amount_usd=amount,probability_pct=probability,
                   created_date='2026-01-01',close_date='2026-10-01',stage_entered_date='2026-08-01',last_activity_date='2026-09-01',
                   forecast_category='Commit' if i==1 else 'Pipeline',region='West' if i%2 else 'East',owner='Alice',sales_team='Commercial')
        rows.append(row)
    return pd.DataFrame(rows)

@pytest.fixture
def data(raw):
    return calculate_derived_columns(clean_data(raw)[0],date(2026,10,11))
