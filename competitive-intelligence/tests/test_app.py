from pathlib import Path
from streamlit.testing.v1 import AppTest
import core

def test_app_opens_without_network(monkeypatch,tmp_path):
    original=core.connect
    monkeypatch.setattr(core,"connect",lambda:original(tmp_path/"app.db"))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=30)
    app.run()
    assert not app.exception
    app.sidebar.checkbox[0].check().run()
    assert not app.exception
    assert any("SYNTHETIC DEMO" in w.value for w in app.warning)
