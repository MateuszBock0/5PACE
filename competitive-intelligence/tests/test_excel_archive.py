import copy
from io import BytesIO
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
import core
import sync
from demo import fixture
from excel_archive import *

def test_xlsx_literal_data_and_types():
    data={"Test":{"headers":["ID","Text","Boolean","Value"],"rows":[{"ID":"001","Text":"=HYPERLINK(\"https://example.invalid\")","Boolean":False,"Value":12.5},{"ID":"002","Text":"#REF!","Boolean":True,"Value":None}]}}
    wb=load_workbook(BytesIO(workbook_bytes(data,"example")))
    assert wb.properties.identifier=="example"
    s=wb["Test"]
    assert s["A2"].value=="001" and s["A2"].data_type=="s"
    assert s["B2"].value.startswith("=") and s["B2"].data_type=="s"
    assert s["B3"].data_type=="s"
    assert s["C2"].value is False and s["D2"].value==12.5
    assert s["D3"].value is None
    wb.close()
    w=load_workbook(BytesIO(dataframe_bytes(pd.DataFrame({"Text":["=1+1"],"Number":[float("nan")]}))))
    assert w.active["A2"].data_type=="s" and w.active["B2"].value is None
    w.close()

def test_rebuild_history_latest_not_restored(tmp_path):
    db=tmp_path/"test.db";root=tmp_path/"Excel Archive"
    a=fixture();b=copy.deepcopy(a)
    b["Companies"]["rows"][0]["Company Name"]="Changed"
    with core.connect(db) as conn:
        h1=core.store(conn,a)
        h2=core.store(conn,b)
        core.restore(conn,h1)
        result=rebuild(conn,root)
        assert result["snapshots"]==2 and not result["errors"]
        assert core.state(conn,"current_hash")==h1
        assert core.state(conn,"latest_hash")==h2
        assert len(list(root.glob("*/*.xlsx")))==2
        assert matches(root/LATEST,h2)
        old=next(r for r in core.history(conn) if r[0]==h1)
        p=archive_path(root,old[1],h1)
        before=p.stat().st_mtime_ns
        assert not rebuild(conn,root)["errors"]
        assert p.stat().st_mtime_ns==before
        p.write_bytes(b"broken")
        assert not rebuild(conn,root)["errors"] and matches(p,h1)
        payload,_=export_snapshot(conn,h1)
        w=load_workbook(BytesIO(payload))
        assert set(w.sheetnames)==set(a)
        assert w.properties.identifier==h1
        w.close()

def test_sync_archive_failure_retains_new_data(monkeypatch,tmp_path):
    db=tmp_path/"test.db";root=tmp_path/"Excel Archive"
    monkeypatch.setattr(sync,"DATA",tmp_path)
    monkeypatch.setattr(sync,"ARCHIVE_ROOT",root)
    monkeypatch.setattr(sync,"connect",lambda:core.connect(db))
    monkeypatch.setattr(sync,"config",lambda:{"refresh_interval_hours":24})
    monkeypatch.setattr(sync,"download",lambda cfg:fixture())
    def fail(*args,**kwargs): raise PermissionError("locked")
    monkeypatch.setattr(sync,"archive_one",fail)
    result=sync.run(force=True)
    assert result.startswith("Synchronised") and "Excel archive warning" in result
    with core.connect(db) as conn:
        assert core.read_snapshot(conn)==fixture()
        assert core.state(conn,"last_successful_sync")
        assert conn.execute("SELECT status FROM sync_log ORDER BY rowid DESC LIMIT 1").fetchone()[0]=="archive_warning"

def test_sync_auto_archive_and_deduplicate(monkeypatch,tmp_path):
    db=tmp_path/"test.db";root=tmp_path/"Excel Archive"
    monkeypatch.setattr(sync,"DATA",tmp_path)
    monkeypatch.setattr(sync,"ARCHIVE_ROOT",root)
    monkeypatch.setattr(sync,"connect",lambda:core.connect(db))
    monkeypatch.setattr(sync,"config",lambda:{"refresh_interval_hours":24})
    monkeypatch.setattr(sync,"download",lambda cfg:fixture())
    assert sync.run(force=True).startswith("Synchronised")
    assert sync.run(force=True).startswith("Synchronised")
    assert len(list(root.glob("*/*.xlsx")))==1
    assert matches(root/LATEST,core.digest(fixture()))
    (root/LATEST).unlink()
    assert sync.run()=="Local data is fresh."
    assert matches(root/LATEST,core.digest(fixture()))
    assert sync.rebuild_excel_archive()["snapshots"]==1
