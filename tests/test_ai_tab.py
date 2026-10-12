from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from streamlit.testing.v1 import AppTest
from components import ai_revenue_analyst as ui
from utils import revenue_analyst as service

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_fifth_tab_without_configuration(monkeypatch):
    def unavailable():
        raise service.RevenueAnalystError('Set GROQ_API_KEY and GROQ_MODEL.')
    monkeypatch.setattr(ui,'load_config',unavailable)
    app=AppTest.from_file(APP).run(timeout=45)
    assert not app.exception
    assert len(app.tabs)==5 and app.tabs[4].label=='AI Revenue Analyst'
    assert app.chat_input[0].disabled
    assert any('GROQ_API_KEY' in warning.value for warning in app.warning)


def test_chat_grounding_history_filter_reset_and_errors(monkeypatch):
    config=service.AnalystConfig('unit-test-secret','test-model')
    client=MagicMock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Open pipeline is $26,237,000.'))])
    monkeypatch.setattr(ui,'load_config',lambda:config)
    monkeypatch.setattr(ui,'respond',lambda context,question,state:service.respond(context,question,state,config=config,client=client))
    app=AppTest.from_file(APP).run(timeout=45)
    assert not app.exception and not client.chat.completions.create.called
    app.chat_input[0].set_value('Summarize the current pipeline.').run(timeout=30)
    assert not app.exception
    assert len(app.session_state['revenue_ai_messages'])==2
    assert '26237000' in client.chat.completions.create.call_args.kwargs['messages'][1]['content']
    assert 'unit-test-secret' not in str(client.chat.completions.create.call_args)
    app.run(timeout=30)
    assert len(app.session_state['revenue_ai_messages'])==2
    assert client.chat.completions.create.call_count==1
    app.multiselect(key='filter_region').set_value(['West']).run(timeout=30)
    assert not app.exception and app.session_state['revenue_ai_messages']==[]
    client.chat.completions.create.side_effect=RuntimeError('secret failure detail')
    app.chat_input[0].set_value('Summarize West.').run(timeout=30)
    assert not app.exception and len(app.error)>0
    assert 'secret failure detail' not in app.error[0].value
    assert app.session_state['revenue_ai_messages']==[]
