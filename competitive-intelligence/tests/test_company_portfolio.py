from test_command import comparison_fixture
from founder import CORE_IDS,summaries
from company_portfolio import portfolio_data,filter_companies,selected_company,CORE_COMPANIES,PORTFOLIO_EXPOSURE,CUSTOM,NOTE
from core import digest
from pdf_reports import render_report

def fixture():
    d=comparison_fixture()
    p1,p2=d["Products"]["rows"]
    p1.update({"Product Name":"Alpha Inspection Module","Commercial Status":"Commercial","Target Customers":"Spacecraft manufacturing teams"})
    p2.update({"Company ID":p1["Company ID"],"Product Name":"Beta Records Module","Commercial Status":"Historical"})
    base=d["AIT-VISTA Capabilities"]["rows"][0]
    d["AIT-VISTA Capabilities"]["rows"]=[dict(base,**{"Criterion ID":c}) for c in CORE_IDS]
    r=d["Comparison Assessment"]["rows"][0]
    def a(i,p,c,s,old=""):return dict(r,**{"Comparison ID":i,"Product ID":p,"Criterion ID":c,"Verdict":s,"Supersedes Comparison ID":old})
    d["Comparison Assessment"]["rows"]=[a("A","DEMO-P1",CORE_IDS[0],"Supported"),a("B","DEMO-P1",CORE_IDS[1],"Supported"),a("C","DEMO-P2",CORE_IDS[0],"Supported"),a("D","DEMO-P2",CORE_IDS[2],"Supported"),a("E","DEMO-P2",CORE_IDS[3],"Partially supported"),a("F","DEMO-P2",CORE_IDS[4],"Unknown"),a("G","DEMO-P1",CORE_IDS[5],"Announced"),a("H","DEMO-P1",CORE_IDS[6],"Explicitly unsupported"),a("I","DEMO-P2",CORE_IDS[7],"Supported"),a("J","DEMO-P2",CORE_IDS[7],"Unknown")]
    return d

def test_union_max_no_double_count_and_ties_sources():
    d=fixture();h=digest(d);f,details=portfolio_data(d)
    r=f.iloc[0];detail=details[r["Company ID"]]
    assert len(f)==1 and r["Product count"]==2
    assert r["Portfolio coverage"]==3.5/8
    assert r["Best single product coverage"]==2.5/8
    assert r["Additional portfolio coverage"]==1/8
    assert r["Portfolio flag"]=="Portfolio-only exposure"
    assert r["Recorded coverage"]==1 and r["Determinate coverage"]==5/8
    assert r["Commercial-only coverage"]==2/8
    assert r["Integration status"]=="Compatibility unconfirmed"
    assert set(detail["criteria"].iloc[0]["Contributing product IDs"].split("; "))=={"DEMO-P1","DEMO-P2"}
    e=detail["records"]
    assert set(e[e["Criterion ID"]==CORE_IDS[7]]["Pair verdict"])=={"Disputed","Unassessed"}
    assert digest(d)==h
    assert filter_companies(f,CORE_COMPANIES).empty
    assert len(filter_companies(f,PORTFOLIO_EXPOSURE))==1
    assert filter_companies(f,CUSTOM,[]).empty

def test_single_product_and_zero_company_by_stable_id():
    d=fixture();d["Products"]["rows"][1]["Company ID"]="DEMO-CO-2"
    f,details=portfolio_data(d)
    assert len(f)==2 and (f["Additional portfolio coverage"]==0).all()
    assert (f["Portfolio coverage"]==f["Best single product coverage"]).all()
    d["Comparison Assessment"]["rows"]=[]
    f,details=portfolio_data(d)
    assert len(f)==2 and (f["Portfolio coverage"]==0).all()
    assert (f["Recorded coverage"]==0).all()
    cid=f.iloc[1]["Company ID"]
    assert selected_company({"selection":{"points":[{"customdata":[cid]}]}},list(f["Company ID"]))==cid

def test_named_integration_only_and_negative_claim():
    d=fixture();cid=d["Products"]["rows"][0]["Company ID"]
    d["Observations"]["rows"].append({"Company ID":cid,"Observation ID":"LINK","Observation":"Alpha Inspection Module integrates with Beta Records Module.","Evidence status":"Vendor claim","Source URL":"https://example.invalid/link"})
    f,details=portfolio_data(d)
    assert f.iloc[0]["Integration status"]=="Potential integration (source claim)"
    d["Observations"]["rows"][-1]["Evidence status"]="Official documentation"
    f,details=portfolio_data(d)
    assert f.iloc[0]["Integration status"]=="Documented integration (specific pairs only)"
    d["Observations"]["rows"][-1]["Observation"]="Alpha Inspection Module is not integrated with Beta Records Module."
    assert portfolio_data(d)[0].iloc[0]["Integration status"]=="Compatibility unconfirmed"

def test_portfolio_pdf_native_and_source_immutable():
    d=fixture();h=digest(d)
    for kind in ["Strategic overview","Combined strategic report"]:
        pdf=render_report(d,{},kind)
        assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-100:]
    assert digest(d)==h
