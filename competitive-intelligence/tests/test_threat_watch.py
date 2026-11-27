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
