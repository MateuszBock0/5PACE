from test_command import comparison_fixture
from pdf_reports import REPORTS,render_report
from founder import summaries,strategic_map_cohort,map_exclusions
from core import digest

def test_pdf_all_report_types_and_immutable_source():
    d=comparison_fixture();before=digest(d)
    for kind in REPORTS:
        result=render_report(d,{},kind,["DEMO-P1"],"SYNTHETIC DEMO","2026-11-27",before,"Synthetic QA")
        assert result.startswith(b"%PDF-") and b"%%EOF" in result[-100:]
    assert digest(d)==before

def test_research_entrant_is_visible_independently_of_commercial_rank():
    d=comparison_fixture()
    d["Products"]["rows"][0].update({"Commercial Status":"Research","Competition Type":"Potential entrant"})
    r=summaries(d)
    shown=strategic_map_cohort(r,"Strategic + research",limit=0)
    assert "DEMO-P1" in set(shown["Product ID"])
    assert "DEMO-P1" not in set(strategic_map_cohort(r,"Commercial shortlist")["Product ID"])
    assert set(strategic_map_cohort(r,"All products")["Product ID"])==set(r["Product ID"])
    assert "Reason not shown" in map_exclusions(r,shown)

def test_pdf_monitor_signals_obey_default_and_empty_cohort(monkeypatch):
    import pandas as pd
    import pdf_reports
    signals=pd.DataFrame([{"Product ID":"P1","Company ID":"C1"},{"Product ID":"P2","Company ID":"C2"},{"Product ID":"","Company ID":"C1"},{"Product ID":"","Company ID":"C2"}])
    monkeypatch.setattr(pdf_reports,"signals",lambda data:signals)
    assert pdf_reports.cohort_signals({},["P1"],["C1"]).index.tolist()==[0,2]
    assert pdf_reports.cohort_signals({},[],[]).empty
