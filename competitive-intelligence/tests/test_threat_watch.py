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

def test_axis_union_all_16_combinations_and_no_family_or_role_filter():
    from founder import strategic_map_cohort,DEFAULT_MAP_SCOPE,map_exclusions
    from decision import CUSTOMER_LANES,FUNCTION_LANES
    d=pd.DataFrame([{"Product ID":f"{i}-{j}","Family ID":"same","Role":"Unresolved role","Order":4,"Customer position":y,"Functional overlap":x} for i,y in enumerate(CUSTOMER_LANES) for j,x in enumerate(FUNCTION_LANES)])
    included=strategic_map_cohort(d,limit=0)
    assert len(included)==12
    assert set(included["Product ID"])=={f"{i}-{j}" for i in range(4) for j in range(4) if i>=2 or j>=2}
    assert len(map_exclusions(d,included,DEFAULT_MAP_SCOPE))==4
    assert len(strategic_map_cohort(d,"All products"))==16

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
