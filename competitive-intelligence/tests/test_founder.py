from pathlib import Path
from streamlit.testing.v1 import AppTest
import core
from test_command import comparison_fixture
from founder import summaries,priority_families,strategic_criteria,advantage_summary,evidence_detail,timeline

def test_founder_uncertainty_and_roles():
    d=comparison_fixture()
    a,b=d["Products"]["rows"]
    a.update({"Product Category":"Automated Visual Inspection","Primary Use Case":"Visual inspection of spacecraft assembly","Space Industry Applicability":"Space offering"})
    b.update({"Product Category":"Digital Work Instructions","Primary Use Case":"Execute spacecraft assembly","Space Industry Applicability":"Space offering"})
    r=summaries(d).set_index("Product ID")
    assert r.loc["DEMO-P1","Order"]==0
    assert r.loc["DEMO-P2","Order"]==1
    assert r.loc["DEMO-P2","Buyer / procurement overlap"].startswith("Unconfirmed")
    d["Comparison Assessment"]["rows"].pop()
    assert evidence_detail(d,"DEMO-P2","CR1")[0]=="Unassessed"
    assert summaries(d).set_index("Product ID").loc["DEMO-P2","Functional overlap"]=="No positive record / unresolved"
    assert not advantage_summary(d,{},["DEMO-P2"]).Finding.str.startswith("Substantiated functional advantage").any()
    assert not timeline(d).empty

def test_founder_navigation(monkeypatch,tmp_path):
    original=core.connect;db=tmp_path/"founder.db"
    with original(db) as conn:core.store(conn,comparison_fixture())
    monkeypatch.setattr(core,"connect",lambda:original(db))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=45).run()
    assert not app.exception
    assert app.sidebar.radio[0].value=="Command Centre"
    from founder import DEFAULT_MAP_SCOPE
    assert app.selectbox(key="landing-map-scope").value=="All products"
    assert set(app.session_state["landing-products"])=={"DEMO-P1","DEMO-P2"}
    assert app.selectbox(key="landing-benchmark-scope").value==DEFAULT_MAP_SCOPE
    assert not app.session_state["threat-products"]
    app.selectbox(key="landing-benchmark-scope").set_value("All products").run()
    app.selectbox(key="landing-map-scope").set_value(DEFAULT_MAP_SCOPE).run()
    assert not app.exception
    assert not app.session_state["landing-products"]
    assert set(app.session_state["threat-products"])=={"DEMO-P1","DEMO-P2"}
    app.button(key="landing-map-scope-reset").click().run()
    assert app.selectbox(key="landing-map-scope").value=="All products"
    assert app.selectbox(key="landing-benchmark-scope").value=="All products"
    app.button(key="landing-benchmark-scope-reset").click().run()
    assert not app.session_state["threat-products"]
    next(b for b in app.button if b.label=="Open profile").click().run()
    assert app.sidebar.radio[0].value=="Competitor Explorer"
    assert not app.exception
    for page in ["Market Positioning","Competitive Advantage","Intelligence Monitor","Competitor Explorer","Command Centre"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception,f"{page}: {app.exception}"
        if page=="Market Positioning":
            assert app.selectbox(key="market-map-scope").value==DEFAULT_MAP_SCOPE
            assert not app.session_state["founder-map-products"]
            assert app.selectbox(key="workflow-benchmark-scope").value==DEFAULT_MAP_SCOPE
            assert not app.session_state["workflow-products"]
            app.selectbox(key="market-map-scope").set_value("All products").run()
            assert set(app.session_state["founder-map-products"])=={"DEMO-P1","DEMO-P2"}
            assert not app.session_state["workflow-products"]
            app.selectbox(key="workflow-benchmark-scope").set_value("All products").run()
            app.button(key="market-map-scope-reset").click().run()
            assert app.selectbox(key="market-map-scope").value==DEFAULT_MAP_SCOPE
            assert not app.session_state["founder-map-products"]
            assert app.selectbox(key="workflow-benchmark-scope").value=="All products"
            assert set(app.session_state["workflow-products"])=={"DEMO-P1","DEMO-P2"}
            app.button(key="workflow-benchmark-scope-reset").click().run()
            assert not app.session_state["workflow-products"]
            assert not app.exception
        if page=="Competitive Advantage":
            assert app.selectbox(key="adv-cohort-scope").value==DEFAULT_MAP_SCOPE
            assert not app.session_state["founder-adv-products"]
            app.selectbox(key="adv-cohort-scope").set_value("All products").run()
            assert set(app.session_state["founder-adv-products"])=={"DEMO-P1","DEMO-P2"}
            app.button(key="adv-cohort-scope-reset").click().run()
            assert not app.session_state["founder-adv-products"]
            assert not app.exception

def test_profile_strengths_and_commercial_changes():
    import copy
    from founder import profile_findings, recorded_market_changes
    d=comparison_fixture()
    f=profile_findings(d,{},"DEMO-P2")
    assert f["Documented relative functional differences"]
    d["Comparison Assessment"]["rows"][1]["Evidence level"]="Vendor claim"
    f=profile_findings(d,{},"DEMO-P2")
    assert not f["Documented relative functional differences"]
    assert f["Potential differences — weaker evidence"]
    b=copy.deepcopy(d)
    b["Products"]["rows"][0]["Commercial Status"]="Commercial"
    c=recorded_market_changes(d,b)
    assert c.iloc[0]["Recorded change"]=="Commercial Status"
    assert "not established" in c.iloc[0].Interpretation

def test_brief_search_and_lanes():
    from founder import search_companies,relationship_lane,commercial_summary,brief_criteria
    d=comparison_fixture()
    d["Companies"]["rows"][0]["Alternative Names"]="Alt Vision; AV"
    d["Products"]["rows"][1]["Alternative Names"]="Proc alias"
    assert search_companies(d,"alt vision")==["DEMO-CO-1"]
    assert search_companies(d,"proc alias")==["DEMO-CO-2"]
    assert relationship_lane({"Role":"Unresolved role"})=="Unresolved / other"
    assert brief_criteria(d)==["CR1"]
    assert "not recorded" in commercial_summary({})[0]
