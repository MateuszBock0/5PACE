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
