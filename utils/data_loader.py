"""Bounded CSV ingestion with in-memory, session-keyed preprocessing cache."""
from io import BytesIO
from pathlib import Path
import csv
import io
import pandas as pd
import streamlit as st
from utils.data_cleaning import clean_data, calculate_derived_columns

DEFAULT_DATASET=Path(__file__).resolve().parents[1]/'sales_pipeline_demo_650.csv'

@st.cache_data(ttl=600,max_entries=12,show_spinner=False)
def load_data(content:bytes,analysis_date,session_token):
    if len(content)>20_000_000:
        raise ValueError('CSV exceeds the 20 MB upload limit.')
    try:
        header=next(csv.reader(io.StringIO(content.decode('utf-8-sig'))))
        if len(set(h.strip() for h in header))!=len(header):
            raise ValueError('CSV headers must be unique.')
        raw=pd.read_csv(BytesIO(content),dtype='string',encoding='utf-8-sig')
    except (UnicodeError,pd.errors.ParserError,pd.errors.EmptyDataError,StopIteration,csv.Error):
        raise ValueError('Upload a UTF-8 CSV with a header and consistent columns.') from None
    cleaned,report=clean_data(raw)
    return calculate_derived_columns(cleaned,analysis_date),report
