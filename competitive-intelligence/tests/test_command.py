import copy
from test_advanced import mapped_fixture
from core import normalize_sheet, validate
from command_engine import *

def comparison_fixture():
    d=mapped_fixture()
    def row(i,p,s,e="Official technical documentation",old=""):
        return [i,p,"CR1",s,e,"Synthetic rationale","https://example.invalid/","","DEMO-O1","","2026-11-26",old,"Synthetic only",p+"|CR1","OK"]
    d[ASSESS]=normalize_sheet(ASSESS,[FIELDS,row("CMP1","DEMO-P1","Supported"),row("CMP2","DEMO-P2","Explicitly unsupported")])
    d[VIEW]=normalize_sheet(VIEW,[["Product ID","Company","Product","CR1"],["","","","Presence"],["DEMO-P1","Example","Vision","Supported"],["DEMO-P2","Example","Procedure","Explicitly unsupported"]])
    return d

def test_direct_ledger_and_conflict():
    d=comparison_fixture()
    assert not validate(d)[0]
    assert not matrix_audit(d)
    r=copy.deepcopy(d[ASSESS]["rows"][0]);r["Comparison ID"]="CMP3";r["Verdict"]="Unknown"
    d[ASSESS]["rows"].append(r)
    assert direct_matrix(d).loc["DEMO-P1","CR1"]=="Disputed"
    assert matrix_audit(d)
    r["Supersedes Comparison ID"]="CMP1"
    assert direct_matrix(d).loc["DEMO-P1","CR1"]=="Unknown"
    assert not validate(d)[0]
    r["Supersedes Comparison ID"]="CMP2"
    assert validate(d)[0]

def test_threat_and_advantage_bounds():
    d=comparison_fixture();m=direct_matrix(d)
    assert profile({},"CR1","As-Is")=="Supported"
    assert profile({},"CR1","Target")=="Target"
    t=threat_table(d,m,{"CR1":1})
    assert set(t.Role)=={"Direct","Adjacent / substitute"}
    assert t["Threat upper"].is_monotonic_decreasing
    assert (t["Threat lower"]<=t["Threat upper"]).all()
    assert advantages(d,m,{},"As-Is").iloc[0].Assessment=="Observed parity"
    cfg={"command_profiles":{"CR1":{"status":"Supported","stage":"Verified","reference":"test","demand":"Validated","demand_reference":"interview"}}}
    assert advantages(d,m.loc[["DEMO-P2"]],cfg,"As-Is").iloc[0].Assessment=="Functional advantage (selected cohort)"
    d[ASSESS]["rows"].pop()
    assert advantages(d,direct_matrix(d),cfg,"As-Is").iloc[0].Assessment!="Functional advantage (selected cohort)"
    assert direct_matrix(d).loc["DEMO-P2","CR1"]=="Unassessed"
    assert not research_queue(d,direct_matrix(d),cfg).empty

def test_append_only():
    d=comparison_fixture();b=copy.deepcopy(d)
    d[ASSESS]["rows"][0]["Assessment rationale"]="changed"
    assert any("modified" in x for x in validate(d,b)[0])
    assert comparison_changes(b,d).empty  # same verdict/evidence/id; immutable change rejected

def test_fixed_overlap_history():
    a=comparison_fixture(); b=copy.deepcopy(a)
    b[ASSESS]["rows"][1]["Verdict"]="Unknown"
    d=overlap_history([("old",a),("new",b)],["DEMO-P2"],["CR1"],{"CR1":1})
    assert d.Lower.tolist()==[0,0]
    assert d.Upper.tolist()==[0,1]

def test_declared_baseline_without_evidence():
    d=comparison_fixture()
    assert scope_ids(d,{},"As-Is")==["CR1"]
    a=advantages(d,direct_matrix(d,["DEMO-P2"]),{},"As-Is").iloc[0]
    assert a.Assessment=="Functional advantage (selected cohort)"
    assert a.Demand=="Unvalidated"
    assert a["AIT-VISTA basis"]=="Team-declared functionality"
    assert profile({"command_profiles":{"CR1":{"status":"Partially supported"}}},"CR1","As-Is")=="Partially supported"

def test_role_family_and_research_contract():
    from competitive_roles import classify, family_root, family_watchlist
    d=comparison_fixture()
    a,b=d["Products"]["rows"]
    a.update({"Product Category":"Automated Visual Inspection","Primary Use Case":"Visually inspect spacecraft assembly with cameras","Target Customers":"Satellite AIT engineers"})
    b.update({"Product Family":"DEMO-P1","Product Category":"Digital Work Instructions","Primary Use Case":"Execute spacecraft assembly procedures","Target Customers":"Spacecraft AIT teams"})
    assert classify(a)["Analytical role"]=="Direct visual AIT candidate"
    assert classify(b)["Analytical role"]=="Workflow / procurement substitute candidate"
    assert family_root(registry(d,"Products","Product ID"),"DEMO-P2")=="DEMO-P1"
    t=threat_table(d,direct_matrix(d),{"CR1":1})
    f=family_watchlist(t)
    assert len(f)==1 and f.iloc[0]["Family members"]==2
    assert f.iloc[0]["Family upper"]==t["Threat upper"].max()
    assert advantages(d,direct_matrix(d),{},"As-Is").iloc[0]["Eligible competitors"]==1
    q=research_queue(d,direct_matrix(d),{},"2026-11-26T23:00:00Z")
    assert list(q.columns)==["Product ID","Criterion ID","Research question","Strategic decision affected","Priority","Existing evidence IDs","Reason for uncertainty","Snapshot date"]
    assert set(q["Snapshot date"])=={"2026-11-26T23:00:00Z"}
    assert (q["Criterion ID"]=="").any()
    assert head_to_head(d,direct_matrix(d),{},"DEMO-P2","As-Is").iloc[0].Comparison=="AIT-VISTA functional superiority"
    assert head_to_head(d,direct_matrix(d),{},"DEMO-P2","Target").iloc[0].Comparison.startswith("Planned")
    d[ASSESS]["rows"][1]["Verdict"]="Unknown"
    assert head_to_head(d,direct_matrix(d),{},"DEMO-P2","As-Is").iloc[0].Comparison=="Insufficient evidence"

def test_uncertainty_does_not_reduce_upper_exposure():
    d=comparison_fixture()
    m=direct_matrix(d)
    initial=threat_table(d,m,{"CR1":1}).set_index("Product ID")
    m.loc["DEMO-P2","CR1"]="Unassessed"
    later=threat_table(d,m,{"CR1":1}).set_index("Product ID")
    assert later.loc["DEMO-P2","Threat upper"]>=initial.loc["DEMO-P2","Threat upper"]

def test_weak_evidence_does_not_confirm_inferiority():
    d=comparison_fixture()
    d[ASSESS]["rows"][0]["Evidence level"]="Vendor claim"
    cfg={"command_profiles":{"CR1":{"status":"Partially supported"}}}
    m=direct_matrix(d,["DEMO-P1"])
    assert advantages(d,m,cfg,"As-Is").iloc[0].Assessment.startswith("Potential disadvantage")
    assert head_to_head(d,m,cfg,"DEMO-P1","As-Is").iloc[0].Comparison.startswith("Provisional")
