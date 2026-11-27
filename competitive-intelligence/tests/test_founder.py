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
    next(b for b in app.button if b.label=="Open profile").click().run()
    assert app.sidebar.radio[0].value=="Competitor Explorer"
    assert not app.exception
    for page in ["Market Positioning","Competitive Advantage","Intelligence Monitor","Competitor Explorer","Command Centre"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception,f"{page}: {app.exception}"

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
