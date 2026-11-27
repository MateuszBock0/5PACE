from test_command import comparison_fixture
from threat_watch import exposure,spread_points,report_provenance
from core import digest
import pandas as pd

def test_reference_and_colocated_rivals():
    d=pd.DataFrame({"Product ID":["a","b","c","d"],"X":[3.]*4,"Y":[2.]*4})
    z=spread_points(d,reference=(3,2))
    assert len(set(zip(z["Display X"],z["Display Y"])))==4
    assert (3,2) not in set(zip(z["Display X"],z["Display Y"]))
    assert z[["X","Y"]].equals(d[["X","Y"]])

def test_synthetic_metadata_isolation():
    d=comparison_fixture()
    stamp,h,source=report_provenance(d,"SYNTHETIC DEMO","REAL DATE","REAL HASH","Google Sheets")
    assert stamp=="Not applicable (synthetic)" and h=="synthetic-"+digest(d) and source=="Synthetic fixture"
    assert report_provenance(d,"LOCAL SNAPSHOT","date","hash","Google Sheets")==("date","hash","Google Sheets")

def test_exposure_does_not_treat_missing_as_absence():
    d=comparison_fixture()
    e=exposure(d,{},["missing"]).iloc[0]
    assert e.Verdict=="Unresolved" and e.Action=="Research" and e.Importance=="Unresolved"

def test_record_specific_evidence_level():
    import copy
    d=comparison_fixture()
    r=d["Comparison Assessment"]["rows"][0]
    r["Evidence level"]="Vendor claim"
    other=copy.deepcopy(r);other["Comparison ID"]="CMP-STRONG";other["Evidence level"]="Official technical documentation"
    d["Comparison Assessment"]["rows"].append(other)
    e=exposure(d,{},[r["Product ID"]],[r["Criterion ID"]]).iloc[0]
    assert e["Comparison ID"]=="CMP-STRONG"
    assert e.Evidence=="Official technical documentation"

def test_40_60_boundary_and_no_family_or_role_filter():
    from founder import strategic_map_cohort,DEFAULT_MAP_SCOPE,map_exclusions,eligible,SPACE_WATCH
    from decision import CUSTOMER_LANES
    for y in CUSTOMER_LANES:
        assert eligible(.3999,y)==False
        assert eligible(.4,y)==(y in CUSTOMER_LANES[2:])
        assert eligible(.5999,y)==(y in CUSTOMER_LANES[2:])
        assert eligible(.6,y)
    assert not eligible(.4,"Space offering")
    d=pd.DataFrame([{"Product ID":f"{i}-{j}","Family ID":"same","Role":"Research / emerging entrant","Order":4,"Customer position":y,"Recorded overlap fraction":x} for i,y in enumerate(CUSTOMER_LANES) for j,x in enumerate([.3999,.4,.5999,.6])])
    included=strategic_map_cohort(d,limit=0)
    assert set(included["Product ID"])=={f"{i}-{j}" for i in range(4) for j in range(4) if j==3 or (i>=2 and j>=1)}
    assert len(map_exclusions(d,included,DEFAULT_MAP_SCOPE))==8
    assert len(strategic_map_cohort(d,"All products"))==16
    assert not set(strategic_map_cohort(d,SPACE_WATCH)["Product ID"])&set(included["Product ID"])

def test_fixed_eight_core_score_and_missing_evidence():
    import copy
    from founder import summaries,CORE_IDS
    d=comparison_fixture()
    r=d["Comparison Assessment"]["rows"][0]
    d["Comparison Assessment"]["rows"]=[dict(r,**{"Comparison ID":f"X{i}","Criterion ID":c,"Verdict":v}) for i,(c,v) in enumerate(zip(CORE_IDS,["Supported","Supported","Supported","Partially supported","Partially supported","Unknown","Announced","Explicitly unsupported"]))]
    # Add the actual criterion registry so ledger validation recognises IDs.
    base=d["AIT-VISTA Capabilities"]["rows"][0]
    d["AIT-VISTA Capabilities"]["rows"]=[dict(base,**{"Criterion ID":c}) for c in CORE_IDS]
    s=summaries(d).set_index("Product ID")
    assert s.loc["DEMO-P1","Recorded overlap fraction"]==.5
    assert s.loc["DEMO-P1","Core evidence coverage"]==1
    assert s.loc["DEMO-P1","Core determinate coverage"]==.75
    assert s.loc["DEMO-P2","Recorded overlap fraction"]==0

def test_record_priorities_preserve_alternate_evidence_and_disputes():
    import copy
    from threat_watch import exposure_records,headline_records,material_pairs
    d=comparison_fixture()
    r=copy.deepcopy(d["Comparison Assessment"]["rows"][0]);r["Comparison ID"]="ALTERNATE";r["Verdict"]="Partially supported"
    d["Comparison Assessment"]["rows"].append(r)
    e=exposure_records(d,{},["DEMO-P1","DEMO-P2"],["CR1"])
    assert len(e[e["Product ID"]=="DEMO-P1"])==2
    assert set(e[e["Product ID"]=="DEMO-P1"].Verdict)=={"Disputed"}
    assert not (e.Action=="React").any()
    assert "ALTERNATE" in set(e["Comparison ID"])
    assert material_pairs(comparison_fixture(),d)=={("DEMO-P1","CR1")}

def test_headlines_include_partial_and_provenance_gates_react():
    from threat_watch import exposure_records,headline_records
    d=comparison_fixture()
    d["Comparison Assessment"]["rows"][1]["Verdict"]="Partially supported"
    e=exposure_records(d,{},["DEMO-P1","DEMO-P2"],["CR1"])
    assert set(headline_records(e).Verdict)=={"Supported","Partially supported"}
    assert not (e.Action=="React").any()

def test_strong_partial_react_not_hidden_by_weak_full():
    from threat_watch import exposure,exposure_records
    d=comparison_fixture()
    d["Comparison Assessment"]["rows"][0]["Evidence level"]="Vendor claim"
    d["Comparison Assessment"]["rows"][1]["Verdict"]="Partially supported"
    d["Comparison Assessment"]["rows"][1]["Evidence level"]="Official technical documentation"
    cfg={"command_profiles":{"CR1":{"customer_importance":"High","customer_importance_reference":"customer-interview-reference"}}}
    records=exposure_records(d,cfg,["DEMO-P1","DEMO-P2"],["CR1"])
    assert records[records["Product ID"]=="DEMO-P2"].iloc[0].Action=="React"
    assert exposure(d,cfg,["DEMO-P1","DEMO-P2"],["CR1"]).iloc[0]["Product ID"]=="DEMO-P2"
