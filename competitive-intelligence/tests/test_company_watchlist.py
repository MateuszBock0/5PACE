from copy import deepcopy
from test_company_portfolio import fixture
from founder import CORE_IDS,summaries,strategic_map_cohort
from company_watchlist import watchlist,watchlist_changes
from core import digest
from pdf_reports import render_report

def test_technology_strict_threshold_distinct_gap_and_readonly():
    d=fixture()
    for c in d["Companies"]["rows"]:
        c.update({"Target Industries":"","Space Industry Presence":"","Space Industry Evidence":""})
    for p in d["Products"]["rows"]:
        p.update({"Target Customers":"","Space Industry Applicability":"","Space Deployment Evidence":""})
    d["Deployments"]["rows"]=[]
    h=digest(d)
    w,detail=watchlist(d)
    assert len(w)==1
    r=w.iloc[0]
    assert r["Priority"]=="P2" and r["Watch Reason"]=="Technology exposure"
    assert r["Portfolio Overlap"]==3.5/8
    assert 3<=r["Gap criteria"]<=8
    assert r["Gap criteria"]==detail[r["Company ID"]].loc[lambda x:x["Gap reason"]!="","Criterion ID"].nunique()
    assert watchlist(d,threshold=3.5/8)[0].empty
    assert digest(d)==h
    # Another product with no positive overlap or space evidence cannot inflate technology qualification.
    extra=deepcopy(d["Products"]["rows"][0]);extra["Product ID"]="UNRELATED";extra["Product Name"]="Unrelated"
    d["Products"]["rows"].append(extra)
    assert watchlist(d)[0].iloc[0]["Gap criteria"]==r["Gap criteria"]

def test_space_target_and_company_presence_without_inheritance():
    d=fixture()
    p=d["Products"]["rows"][0]
    p.update({"Product URL":"https://example.invalid/target","Target Customers":"Spacecraft manufacturing teams"})
    cid=p["Company ID"]
    d["Comparison Assessment"]["rows"]=[]
    w,detail=watchlist(d,threshold=1)
    r=w[w["Company ID"]==cid].iloc[0]
    assert "Space Target" in r["Watch Reason"]
    assert r["Best Product Overlap"]==0 and r["Priority"]=="P1"
    assert r["Space Confirmed"]==""
    assert set(detail[cid]["Product ID"])=={"DEMO-P1"}
    company=next(c for c in d["Companies"]["rows"] if c["Company ID"]==cid)
    company.update({"Space Industry Presence":"Documented presence","Source URL":"https://example.invalid/space"})
    p["Target Customers"]=""
    w,detail=watchlist(d,threshold=1)
    r=w[w["Company ID"]==cid].iloc[0]
    assert r["Space Confirmed"].startswith("Company-level") and r["Priority"]=="P0"
    assert "product relevance unconfirmed" in r["Research basis"]
    assert "DEMO-P1" not in r["Space Confirmed"]

def test_reported_not_documented_and_weak_claims():
    d=fixture()
    d["Deployments"]["rows"]=[{"Deployment ID":"D-1","Product ID":"DEMO-P1","Industry":"Space manufacturing","Use Case":"Assembly","Customer Organisation":"Example","Deployment Status":"Reported implementation","Source URL":"https://example.invalid/case"}]
    a=d["Comparison Assessment"]["rows"][0]
    a["Evidence level"]="Vendor claim"
    w,details=watchlist(d)
    r=w.iloc[0]
    assert "Reported space implementation" in r["Watch Reason"]
    assert "DEMO-P1" in r["Reported space implementation"]
    assert "DEMO-P1" not in r["Space Confirmed"]
    assert r["Unverified Claims"]>=1
    assert "Positive claim below technical documentation" in details[r["Company ID"]].loc[lambda x:x["Comparison IDs"]=="A","Gap reason"].iloc[0]

def test_watchlist_changes_exports_and_core_independence():
    d=fixture();h=digest(d)
    old,_=watchlist(d)
    assert not old.empty
    new=deepcopy(d)
    new["Comparison Assessment"]["rows"]=[]
    for c in new["Companies"]["rows"]:
        c.update({"Target Industries":"","Space Industry Presence":"","Space Industry Evidence":""})
    for p in new["Products"]["rows"]:
        p.update({"Target Customers":"","Space Industry Applicability":"","Space Deployment Evidence":""})
    new["Deployments"]["rows"]=[]
    after,_=watchlist(new)
    assert not watchlist_changes(old,after).empty
    before=strategic_map_cohort(summaries(d))["Product ID"].tolist()
    w,_=watchlist(d,threshold=0,min_gaps=1)
    assert strategic_map_cohort(summaries(d))["Product ID"].tolist()==before
    pdf=render_report(d,{},"Intelligence monitor",watchlist_selection=w["Company ID"].tolist(),watchlist_threshold=0,watchlist_min_gaps=1)
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-100:]
    assert digest(d)==h
