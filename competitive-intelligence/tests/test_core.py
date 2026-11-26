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
