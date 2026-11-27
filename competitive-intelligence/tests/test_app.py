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
    from test_command import comparison_fixture
    from core import store
    original=core.connect
    db=tmp_path/"mapped.db"
    with original(db) as conn:
        store(conn,comparison_fixture())
    monkeypatch.setattr(core,"connect",lambda:original(db))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=40)
    app.run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Advanced Analytics").run()
    for page in ["Command Centre","Overview","Companies & products","Capability matrix","Evidence & deployments","Landscape & threats","Knowledge graph","Research gaps","Similarity & clustering","Technology gaps","History & evolution","Product intelligence","Strategic intelligence","Reports","Excel Archive","Synchronisation"]:
        app.sidebar.radio[1].set_value(page).run()
        assert not app.exception, f"{page}: {app.exception}"

def test_command_workspaces(monkeypatch,tmp_path):
    from test_command import comparison_fixture
    original=core.connect
    db=tmp_path/"command.db"
    with original(db) as conn:
        core.store(conn,comparison_fixture())
    monkeypatch.setattr(core,"connect",lambda:original(db))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=40).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Advanced Analytics").run()
    next(r for r in app.sidebar.radio if r.label=="Advanced workspace").set_value("Command Centre").run()
    for view in ["Executive dashboard","Market Positioning","Benchmark & competitor profile","Product baseline & priorities","Watchlist & evolution","Research queue"]:
        next(r for r in app.radio if r.label=="Command workspace").set_value(view).run()
        assert not app.exception, f"{view}: {app.exception}"
    next(r for r in app.radio if r.label=="AIT-VISTA comparison baseline").set_value("As-Is").run()
    assert not app.exception

def test_positioning_workspaces(monkeypatch,tmp_path):
    from test_command import comparison_fixture
    original=core.connect
    db=tmp_path/"position.db"
    with original(db) as conn: core.store(conn,comparison_fixture())
    monkeypatch.setattr(core,"connect",lambda:original(db))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=45).run()
    app.sidebar.radio[0].set_value("Advanced Analytics").run()
    next(r for r in app.sidebar.radio if r.label=="Advanced workspace").set_value("Command Centre").run()
    next(r for r in app.radio if r.label=="Command workspace").set_value("Market Positioning").run()
    assert not app.exception
    for view in ["Positioning map","Capability profile","Competitive proximity","Company portfolios","Advantage portfolio","Evidence sensitivity","Workflow differentiation","Methodology & settings"]:
        next(r for r in app.radio if r.label=="Positioning workspace").set_value(view).run()
        assert not app.exception, f"{view}: {app.exception}"
    next(r for r in app.radio if r.label=="Positioning workspace").set_value("Positioning map").run()
    next(s for s in app.selectbox if s.label=="Y axis").set_value("Commercial readiness").run()
    assert not app.exception
    next(r for r in app.radio if r.label=="AIT-VISTA comparison baseline").set_value("MVP").run()
    assert not app.exception
