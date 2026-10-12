import pandas as pd
import pytest
from utils.data_cleaning import clean_data,calculate_derived_columns


def test_strings_currency_dates(raw):
    raw['amount_usd']=raw['amount_usd'].astype(object)
    raw.loc[0,'amount_usd']='$10,000.00'
    result,report=clean_data(raw)
    assert result.loc[0,'opportunity_id']=='000'
    assert result.loc[0,'account_id']=='0000'
    assert result.loc[0,'amount_usd']==10000
    assert report['rejected_records']==0
    assert pd.api.types.is_datetime64_any_dtype(result.close_date)


def test_duplicate_ids_exclude_all_versions(raw):
    raw.loc[1,'opportunity_id']='000'
    result,report=clean_data(raw)
    assert len(result)==2
    assert report['duplicate_ids']==['000']
    assert report['duplicate_records']==2

@pytest.mark.parametrize('field,value',[('amount_usd',-1),('amount_usd','invalid'),('created_date','bad'),('created_date','2027-01-01'),('close_date',None),('opportunity_id',None),('stage','Invented Stage')])
def test_bad_critical_record_only(raw,field,value):
    raw[field]=raw[field].astype(object)
    raw.loc[0,field]=value
    result,report=clean_data(raw)
    assert len(result)==3 and report['rejected_records']==1


def test_optional_invalid_fields_do_not_remove_revenue(raw):
    raw.loc[0,'probability_pct']=110
    raw.loc[0,'last_activity_date']='bad'
    result,report=clean_data(raw)
    assert len(result)==4 and report['rejected_records']==0
    assert pd.isna(result.loc[0,'probability_pct'])
    assert pd.isna(result.loc[0,'last_activity_date'])


def test_missing_schema_fails_clearly(raw):
    with pytest.raises(ValueError,match='Missing required columns'):
        clean_data(raw.drop(columns=['owner']))


def test_null_categories_and_optional_dates(raw):
    raw.loc[0,'owner']=None
    raw.loc[0,'loss_reason']=None
    raw.loc[0,'stage_entered_date']='2025-01-01'
    result,_=clean_data(raw)
    assert result.loc[0,'owner']=='Unknown'
    assert result.loc[0,'loss_reason']=='Unknown'
    assert pd.isna(result.loc[0,'stage_entered_date'])
