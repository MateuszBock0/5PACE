import copy
import pandas as pd
from core import normalize_sheet,validate
from demo import fixture
from analytics import matrix
from product_intelligence import mappings,criterion_matrix,function_profile
from strategic import commercial_mcda,convergence,transitions,opportunity_register,integration_candidates,stale_evidence

def mapped_fixture():
    d=fixture()
    d["AIT-VISTA Capabilities"]=normalize_sheet("AIT-VISTA Capabilities",[
        ["Criterion ID","Product criterion","Type","Related market capability IDs"],
        ["CR1","Presence","Capability","DEMO-C1; DEMO-C3"]])
    d["AIT-VISTA System Functions"]=normalize_sheet("AIT-VISTA System Functions",[
        ["Function ID","Functionality","Consolidated Capability ID","Comparison criterion IDs",None,"Capability ID","Functionality"],
        ["F1","Detect object","CON1","CR1",None,"CON1","Inspect object"],
        ["F2","Unmapped",None,None,None,None,None]])
    return d

def test_side_by_side_mapping():
    d=mapped_fixture()
    assert not validate(d)[0]
    f=mappings(d)
    assert len(f)==2
    assert f.iloc[0]["Market capability IDs"]=="DEMO-C1; DEMO-C3"
    assert f.iloc[1]["Mapping status"]=="Unmapped"
    m=matrix(d)
    cm=criterion_matrix(d,m)
    row=cm[(cm["Product ID"]=="DEMO-P1")].iloc[0]
    assert row["Supported"]==1 and row["Unresolved"]==1
    assert function_profile(d,m,"DEMO-P1").iloc[0]["AIT-VISTA maturity"]=="Unknown"
    d["AIT-VISTA Capabilities"]["rows"][0]["Related market capability IDs"]="BAD"
    assert validate(d)[0]

def test_commercial_bounds_and_unknown():
    d=mapped_fixture(); m=matrix(d)
    s=commercial_mcda(d,m,{"DEMO-C1":1},{"Functional overlap":1,"Documented adoption":1}).set_index("Product ID")
    assert s.loc["DEMO-P1","Lower"]==.5 and s.loc["DEMO-P1","Upper"]==1
    assert s.loc["DEMO-P2","Upper"]==.5

def test_history_and_opportunity():
    d=mapped_fixture(); m=matrix(d)
    new=copy.deepcopy(d)
    new["Capability Assessment"]["rows"][1]["Availability Status"]="Supported"
    t=transitions(d,new)
    assert len(t)==1
    c=convergence(d,new,["DEMO-C1","DEMO-C3"]).set_index("Product ID")
    assert c.loc["DEMO-P1","Newly determinate"]==1
    opp=opportunity_register(d,m,["DEMO-C1","DEMO-C3"],{"DEMO-C1":{"status":"Validated","reference":""}})
    assert set(opp.Demand)=={"Unvalidated"}
    assert not integration_candidates(d,m,["DEMO-C1"]).empty
    assert not stale_evidence(d).empty
