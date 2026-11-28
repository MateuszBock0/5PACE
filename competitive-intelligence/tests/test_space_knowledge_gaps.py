from copy import deepcopy
import pandas as pd
from core import digest
from founder import CORE_IDS
from test_company_portfolio import fixture
from space_knowledge_gaps import space_knowledge_gaps

def clean():
    d=fixture()
    for c in d["Companies"]["rows"]:
        c.update({"Target Industries":"","Space Industry Presence":"","Space Industry Evidence":"","Source URL":""})
    for p in d["Products"]["rows"]:
        p.update({"Target Industries":"","Target Customers":"","Space Industry Applicability":"","Space Deployment Evidence":""})
    d["Deployments"]["rows"]=[]
    return d

def test_zero_overlap_space_target_included_and_unrelated_excluded():
    d=clean()
    p=d["Products"]["rows"][0]
    p.update({"Target Industries":"Space manufacturing","Product URL":"https://example.invalid/space"})
    d["Comparison Assessment"]["rows"]=[]
    h=digest(d)
    f,detail=space_knowledge_gaps(d)
    assert len(f)==1 and f.iloc[0]["Best recorded overlap"]==0
    assert f.iloc[0]["Gap criteria"]==8
    assert f.iloc[0]["Technical determinate coverage"]==0
    assert set(detail[p["Company ID"]]["Product ID"])=={"DEMO-P1"}
    assert digest(d)==h

def test_company_presence_without_product_mapping_and_without_inventory():
    d=clean()
    cid=d["Products"]["rows"][0]["Company ID"]
    co=next(c for c in d["Companies"]["rows"] if c["Company ID"]==cid)
    co.update({"Space Industry Presence":"Documented presence","Source URL":"https://example.invalid/space"})
    f,detail=space_knowledge_gaps(d,8)
    r=f[f["Company ID"]==cid].iloc[0]
    assert r["Product count"]==2 and r["Space product count"]==0
    assert pd.isna(r["Gap criteria"]) and pd.isna(r["Technical determinate coverage"])
    assert detail[cid].empty
    d["Products"]["rows"]=[];d["Comparison Assessment"]["rows"]=[]
    f,_=space_knowledge_gaps(d)
    assert f.iloc[0]["Reason"]=="No registered products"

def test_technical_threshold_and_weak_claims():
    d=clean()
    p=d["Products"]["rows"][0]
    p.update({"Target Industries":"Space","Product URL":"https://example.invalid/space"})
    base=d["Comparison Assessment"]["rows"][0]
    d["Comparison Assessment"]["rows"]=[dict(base,**{"Comparison ID":"X"+str(i),"Criterion ID":c,"Product ID":"DEMO-P1","Verdict":"Supported","Evidence level":"Official technical documentation","Supersedes Comparison ID":""}) for i,c in enumerate(CORE_IDS)]
    assert space_knowledge_gaps(d)[0].empty
    for a in d["Comparison Assessment"]["rows"][:3]:a["Evidence level"]="Vendor claim"
    f,_=space_knowledge_gaps(d)
    assert f.iloc[0]["Gap criteria"]==3 and f.iloc[0]["Weak evidence pairs"]==3
    assert f.iloc[0]["Technical determinate coverage"]==5/8
    assert space_knowledge_gaps(d,4)[0].empty
