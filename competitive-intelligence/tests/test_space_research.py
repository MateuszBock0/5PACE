from test_command import comparison_fixture
from space_research import priority_queue,relevance
from founder import summaries,strategic_map_cohort
from core import digest

def test_space_product_zero_overlap_and_company_not_inherited():
    d=comparison_fixture()
    p,q=d["Products"]["rows"]
    p.update({"Space Industry Applicability":"Space AIT R&D heritage","Product URL":"https://example.invalid/heritage"})
    q.update({"Space Industry Applicability":"Not established","Target Customers":""})
    for c in d["Companies"]["rows"]:c["Space Industry Presence"]="Documented presence"
    assert relevance(p,{},[],{})[3]
    assert not relevance(q,{"Space Industry Presence":"Documented presence"},[],{})[3]
    queue=priority_queue(d,{},"hash","2026-11-27")
    assert "P0 — Space Priority" in set(queue[queue["Product ID"]=="DEMO-P1"]["Priority tier"]) or not len(queue[queue["Product ID"]=="DEMO-P1"])
    assert not (queue[queue["Product ID"]=="DEMO-P2"]["Priority tier"]=="P0 — Space Priority").any()
    assert strategic_map_cohort(summaries(d)).empty
    assert not queue.duplicated(["Product ID","Criterion ID"]).any()

def test_resolved_core_gap_leaves_queue():
    d=comparison_fixture();p=d["Products"]["rows"][0];p.update({"Space Industry Applicability":"Space offering","Product URL":"https://example.invalid/space"})
    c="AV-CR-003"
    base=d["AIT-VISTA Capabilities"]["rows"][0]
    d["AIT-VISTA Capabilities"]["rows"].append(dict(base,**{"Criterion ID":c}))
    before=digest(d)
    q=priority_queue(d,{},"hash","2026-11-27")
    assert ((q["Product ID"]=="DEMO-P1")&(q["Criterion ID"]==c)&(q["Priority tier"]=="P0 — Space Priority")).any()
    assert digest(d)==before
    r=dict(d["Comparison Assessment"]["rows"][0],**{"Comparison ID":"NEW","Criterion ID":c,"Verdict":"Supported","Evidence level":"Official technical documentation"})
    d["Comparison Assessment"]["rows"].append(r)
    q=priority_queue(d,{},"new","2026-11-27")
    assert not ((q["Product ID"]=="DEMO-P1")&(q["Criterion ID"]==c)).any()
