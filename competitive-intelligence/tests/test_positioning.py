import copy
import numpy as np
from test_command import comparison_fixture
from command_engine import direct_matrix
from positioning import *

def test_shared_axes_and_declared_baseline():
    d=comparison_fixture();m=direct_matrix(d)
    l,h,s,e=interval_arrays(d,m,{},"As-Is","Technical documentation or stronger")
    assert l.loc[VISTA,"CR1"]==h.loc[VISTA,"CR1"]==1
    assert l.loc["DEMO-P1","CR1"]==1
    assert h.loc["DEMO-P2","CR1"]==0
    t=taxonomy(d,{})
    p=positioning_table(d,l,h,axis_groups(t),{},{},"As-Is")
    own=p[p["Product ID"]==VISTA].iloc[0]
    assert own[ALL+" lower"]==1
    assert own["Commercial readiness lower"]==0 and own["Commercial readiness upper"]==1
    assert p["Product ID"].nunique()==3

def test_evidence_scenario_unknown_and_na():
    d=comparison_fixture()
    d["Comparison Assessment"]["rows"][0]["Evidence level"]="Vendor claim"
    m=direct_matrix(d)
    a,b,_,_=interval_arrays(d,m,{},evidence_mode="All recorded verdicts")
    assert a.loc["DEMO-P1","CR1"]==b.loc["DEMO-P1","CR1"]==1
    a,b,_,_=interval_arrays(d,m,{},evidence_mode="Technical documentation or stronger")
    assert a.loc["DEMO-P1","CR1"]==0 and b.loc["DEMO-P1","CR1"]==1
    m.loc["DEMO-P2","CR1"]="Not applicable"
    a,b,_,_=interval_arrays(d,m,{})
    assert bounds(a,b,["CR1"]).loc["DEMO-P2","Upper"]==1

def test_proximity_and_planning():
    d=comparison_fixture();m=direct_matrix(d)
    l,h,_,_=interval_arrays(d,m,{})
    p=proximity(l,h,{ALL:["CR1"]}).set_index("Product ID")
    assert p.loc["DEMO-P1","Similarity lower"]==1
    assert p.loc["DEMO-P2","Similarity upper"]==0
    l,h,_,_=interval_arrays(d,m,{},"MVP")
    assert l.loc[VISTA,"CR1"]==0 and h.loc[VISTA,"CR1"]==1
    cfg={"command_profiles":{"CR1":{"mvp":"Excluded"}}}
    l,h,_,_=interval_arrays(d,m,cfg,"MVP")
    assert h.loc[VISTA,"CR1"]==0

def test_company_family_no_union_and_advantage():
    d=comparison_fixture();m=direct_matrix(d)
    l,h,s,_=interval_arrays(d,m,{})
    pos=positioning_table(d,l,h,{ALL:["CR1"]},{},{},"As-Is")
    company=company_positions(pos)
    assert company["Portfolio lower"].max()==1
    a=advantage_portfolio(d,l.loc[[VISTA,"DEMO-P2"]],h.loc[[VISTA,"DEMO-P2"]],s.loc[[VISTA,"DEMO-P2"]],{},"As-Is")
    assert a.iloc[0].Finding=="Substantiated functional advantage"
    d["Comparison Assessment"]["rows"][1]["Verdict"]="Unknown"
    l,h,s,_=interval_arrays(d,direct_matrix(d,["DEMO-P2"]),{})
    a=advantage_portfolio(d,l,h,s,{},"As-Is")
    assert a.iloc[0].Finding!="Substantiated functional advantage"
    assert a.iloc[0]["Rarity lower"]==0
    a=advantage_portfolio(d,l,h,s,{},"Target")
    assert a.iloc[0].Finding=="Planning scenario"

def test_taxonomy_workflow_and_sensitivity():
    d=comparison_fixture();m=direct_matrix(d)
    cfg={"positioning_dimensions":{"CR1":"QA / PA"},"positioning_workflows":{"CR1":["Review & approve","Execute & capture"]}}
    tax=taxonomy(d,cfg)
    assert tax.iloc[0].Dimension=="QA / PA"
    l,h,_,_=interval_arrays(d,m,cfg)
    stages,b=workflow_benchmark(l,h,tax)
    assert set(stages.Stage)=={"Review & approve","Execute & capture"}
    assert b["All-stage integration"].str.startswith("Not established").all()
    r,detail=sensitivity_analysis(d,m,cfg,"As-Is",{"CR1":1},10)
    assert len(detail)==18
    assert (r["Best possible rank"]<=r["Worst possible rank"]).all()
    assert r["Worst possible rank"].max()<=2
    assert r.equals(sensitivity_analysis(d,m,cfg,"As-Is",{"CR1":1},10)[0])

def test_weak_negative_does_not_substantiate_advantage():
    d=comparison_fixture()
    d["Comparison Assessment"]["rows"][1]["Evidence level"]="Vendor claim"
    l,h,s,_=interval_arrays(d,direct_matrix(d,["DEMO-P2"]),{})
    result=advantage_portfolio(d,l,h,s,{},"As-Is").iloc[0]
    assert result.Finding=="Scenario advantage — weaker competitor evidence"
    assert result.Decision!="Protect / validate value"

def test_portfolio_does_not_combine_complementary_products():
    d=comparison_fixture()
    for r in d["Products"]["rows"]: r["Company ID"]="DEMO-CO-1"
    p=pd.DataFrame([
        {"Product ID":VISTA,"Company ID":"__5PACE__","Company":"5PACE","Product":"Reference","Role":"Reference","Family ID":VISTA,ALL+" lower":1.,ALL+" upper":1.},
        {"Product ID":"p1","Company ID":"co","Company":"Company","Product":"P1","Role":"Direct","Family ID":"f",ALL+" lower":.5,ALL+" upper":.5},
        {"Product ID":"p2","Company ID":"co","Company":"Company","Product":"P2","Role":"Direct","Family ID":"f",ALL+" lower":.5,ALL+" upper":1.}])
    r=company_positions(p).iloc[0]
    assert r["Portfolio lower"]==.5 and r["Portfolio upper"]==1.
    assert r["Explicit families"]==1
    assert r["Potential product ID"]=="p2"

def test_workflow_minimum_is_not_average():
    l=pd.DataFrame([[1,1],[1,0]],index=[VISTA,"p"],columns=["a","b"])
    h=l.copy()
    t=pd.DataFrame({"Criterion ID":["a","b"],"Workflow stages":["Execute & capture","Execute & capture"]})
    w,b=workflow_benchmark(l,h,t)
    r=w[w["Product ID"]=="p"].iloc[0]
    assert r.Lower==.5 and r["All mapped criteria lower"]==0
    assert r["Delta vs AIT-VISTA lower"]==-.5

def test_cross_cutting_scope_remains_visible():
    l=pd.DataFrame([[1,1],[.5,0]],index=[VISTA,"p"],columns=["a","b"])
    h=l.copy()
    t=pd.DataFrame({"Criterion ID":["a","b"],"Workflow stages":["Execute & capture",""]})
    d=workflow_context(l,h,t)
    assert d.loc[d["Product ID"]=="p","Upper"].iloc[0]==0
    assert set(d["Criterion IDs"])=={"b"}
