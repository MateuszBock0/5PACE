import copy
from datetime import datetime,timezone,timedelta
import pytest
from core import connect,normalize,store,read_snapshot,validate,history,state,due,restore,diff
from demo import fixture

def test_normalize():
    assert normalize([["ID","Name"],["x"],["",""]])["rows"]==[{"ID":"x","Name":None}]
    with pytest.raises(ValueError): normalize([["ID","ID"],["a","b"]])

def test_validation():
    d=fixture()
    assert not validate(d)[0]
    d["Products"]["rows"][0]["Company ID"]="bad"
    assert validate(d)[0]

def test_transaction_and_history(tmp_path):
    d=fixture()
    with connect(tmp_path/"test.db") as c:
        h=store(c,d)
        assert read_snapshot(c)==d
        assert len(history(c))==1
        assert store(c,d)==h
        assert len(history(c))==1
        assert not due(c)
        assert due(c,24,datetime.now(timezone.utc)+timedelta(days=2))
        changed=copy.deepcopy(d)
        changed["Companies"]["rows"][0]["Company Name"]="Corrected"
        h2=store(c,changed)
        assert h!=h2 and len(history(c))==2
        assert diff(d,changed)[0]["Change"]=="Modified"
        restore(c,h)
        assert read_snapshot(c)==d
        assert state(c,"latest_hash")==h2
        invalid=copy.deepcopy(changed)
        invalid["Companies"]["rows"].pop()
        with pytest.raises(ValueError): store(c,invalid)
        assert read_snapshot(c)==d

def test_supersession_and_deletion():
    d=fixture(); bad=copy.deepcopy(d)
    bad["Capability Assessment"]["rows"][0]["Supersedes Assessment ID"]="DEMO-A1"
    assert any("cycle" in e for e in validate(bad)[0])
    bad=copy.deepcopy(d); bad["Capability Assessment"]["rows"].pop()
    assert any("disappeared" in e for e in validate(bad,d)[0])

def test_unchecked_checkbox_template_rows():
    from core import normalize_sheet
    headers=["Observation ID","Company ID","Observation","Space industry"]
    rows=[headers,["OBS1","CO1","Real observation","FALSE"],
          ["","","","FALSE"],[None,None,None,False],
          ["","","Incomplete real observation","FALSE"],
          ["","","","TRUE"]]
    for sheet in ("Observations","Main"):
        parsed=normalize_sheet(sheet,rows)
        assert len(parsed["rows"])==3
        assert parsed["rows"][0]["Observation ID"]=="OBS1"
        assert parsed["rows"][1]["Observation"]=="Incomplete real observation"
        assert parsed["rows"][2]["Space industry"]=="TRUE"
    assert len(normalize_sheet("Other tab",rows)["rows"])==5

def test_blank_checkbox_rows_do_not_mask_invalid_observations():
    from core import normalize_sheet
    d=fixture()
    headers=["Observation ID","Company ID","Observation","Space industry"]
    d["Observations"]=normalize_sheet("Observations",[headers,["DEMO-O1","DEMO-CO-1","Real record",False]]+[[None,None,None,False]]*1935)
    assert not validate(d)[0]
    d["Observations"]["rows"].append({"Observation ID":"","Company ID":"","Observation":"Unassigned source record","Space industry":False})
    errors,_=validate(d)
    assert any("blank or duplicate Observation ID" in e for e in errors)
    assert any("missing Company ID" in e for e in errors)
