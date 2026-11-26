from demo import fixture
import core
import sync

def test_offline_fallback_and_stale(monkeypatch,tmp_path):
    db=tmp_path/"test.db"
    monkeypatch.setattr(sync,"DATA",tmp_path)
    monkeypatch.setattr(sync,"connect",lambda:core.connect(db))
    monkeypatch.setattr(sync,"config",lambda:{"refresh_interval_hours":24})
    monkeypatch.setattr(sync,"download",lambda cfg:fixture())
    assert sync.run(force=True).startswith("Synchronised")
    assert sync.run()=="Local data is fresh."
    def offline(cfg): raise OSError("offline")
    monkeypatch.setattr(sync,"download",offline)
    try: sync.run(force=True)
    except RuntimeError: pass
    else: raise AssertionError("Expected offline error")
    with core.connect(db) as conn:
        assert core.read_snapshot(conn)==fixture()
        assert len(core.history(conn))==1
        assert conn.execute("SELECT status FROM sync_log ORDER BY rowid DESC LIMIT 1").fetchone()[0]=="failed"
