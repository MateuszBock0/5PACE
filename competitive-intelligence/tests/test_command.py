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
    assert profile({},"CR1","As-Is")=="Unknown"
    assert profile({},"CR1","Target")=="Target"
    t=threat_table(d,m,{"CR1":1})
    assert t.iloc[0].Role=="Direct"
    assert (t["Threat lower"]<=t["Threat upper"]).all()
    assert advantages(d,m,{},"As-Is").iloc[0].Assessment=="Insufficient evidence"
    cfg={"command_profiles":{"CR1":{"status":"Supported","stage":"Verified","reference":"test","demand":"Validated","demand_reference":"interview"}}}
    assert advantages(d,m.loc[["DEMO-P2"]],cfg,"As-Is").iloc[0].Assessment.startswith("Evidence-backed")
    d[ASSESS]["rows"].pop()
    assert advantages(d,direct_matrix(d),cfg,"As-Is").iloc[0].Assessment!="Evidence-backed advantage (selected cohort)"
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
