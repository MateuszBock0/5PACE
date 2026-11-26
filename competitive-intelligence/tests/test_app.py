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

def test_workspaces_with_mapping(monkeypatch,tmp_path):
    from test_advanced import mapped_fixture
    from core import store
    original=core.connect
    db=tmp_path/"mapped.db"
    with original(db) as conn:
        store(conn,mapped_fixture())
    monkeypatch.setattr(core,"connect",lambda:original(db))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=40)
    app.run()
    assert not app.exception
    for page in ["Overview","Companies & products","Capability matrix","Evidence & deployments","Landscape & threats","Knowledge graph","Research gaps","Similarity & clustering","Technology gaps","History & evolution","Product intelligence","Strategic intelligence","Reports","Synchronisation"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, f"{page}: {app.exception}"
