"""Fifth-tab chat, grounded exclusively in the active global opportunity cohort."""
from importlib.util import find_spec
import streamlit as st
from utils.revenue_context import build_revenue_context, ContextError
from utils.revenue_analyst import load_config, respond, synchronize_scope, RevenueAnalystError


def clear_history():
    st.session_state['revenue_ai_messages']=[]


def render_tab_ai_revenue_analyst(frame, *, analysis_date, close_range, selections,
                                   dataset_id, revenue_target=None):
    st.subheader('AI Revenue Analyst')
    st.caption('Ask about pipeline, sales performance and risk using your current dashboard filters.')
    st.info('Submitting a question sends filtered metrics, selected opportunity details and recent chat messages to Groq. Credentials remain on the server.')
    if frame is None or frame.empty:
        clear_history()
        st.session_state.pop('revenue_ai_scope',None)
        st.info('Select a nonempty, valid opportunity cohort to ask the analyst a question.')
        return
    arguments=dict(analysis_date=analysis_date,close_range=close_range,selections=selections,
                   dataset_id=dataset_id,revenue_target=revenue_target)
    try:
        context=build_revenue_context(frame,**arguments)
    except ContextError as exc:
        clear_history()
        st.session_state.pop('revenue_ai_scope',None)
        st.warning(str(exc))
        return
    old_scope=st.session_state.get('revenue_ai_scope')
    history=synchronize_scope(st.session_state,context)
    if old_scope is not None and old_scope!=context.scope_id:
        st.caption('Chat was cleared because the dataset, filters, planning target or analysis date changed.')
    st.caption(f'{len(frame):,} filtered opportunities · Analysis date: {analysis_date} · Python calculates all supplied metrics.')
    st.button('Clear analyst chat',key='clear_analyst_chat',on_click=clear_history)
    with st.expander('Example questions'):
        st.write('• Which sales team has the highest win rate?\n• Which opportunities are most at risk?\n• Why is weighted pipeline lower than total pipeline?\n• How is Closed Won value trending month over month?')
    available=True
    try:
        if find_spec('groq') is None:
            raise RevenueAnalystError('Install AI dependencies with uv sync --extra ai, then launch with uv run --extra ai python -m streamlit run app.py --server.port 8503.')
        # Validate on the server only; never place credentials into session state.
        load_config()
    except RevenueAnalystError as exc:
        available=False
        st.warning(str(exc))
    for message in history:
        with st.chat_message(message['role']):
            st.write(message['content'])
    question=st.chat_input('Ask about this filtered sales pipeline…',key='revenue_ai_input',max_chars=4000,disabled=not available)
    if question:
        with st.chat_message('user'):
            st.write(question)
        try:
            with st.spinner('Analyzing the calculated opportunity facts…'):
                context=build_revenue_context(frame,question=question,**arguments)
                answer=respond(context,question,st.session_state)
            with st.chat_message('assistant'):
                st.write(answer)
        except (ContextError,RevenueAnalystError) as exc:
            st.error(str(exc))
    st.caption('AI explanations can be mistaken. Check them against the dashboard. No live Salesforce access, causal inference or historical pipeline snapshots are available.')
