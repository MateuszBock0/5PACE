from demo import fixture
from analytics import matrix,coverage,score_bounds,current_assessments,research_gaps,similarity,clusters,capability_gaps

def test_unknown_not_zero():
    d=fixture(); m=matrix(d)
    assert m.loc["DEMO-P1","DEMO-C2"]=="Unassessed"
    assert m.loc["DEMO-P1","DEMO-C3"]=="Unknown"
    assert coverage(m)["assessed"]==4
    s=score_bounds(m,{c:1 for c in m.columns}).set_index("Product ID")
    assert s.loc["DEMO-P1","Lower"]==1/3
    assert s.loc["DEMO-P1","Upper"]==1
    assert s.loc["DEMO-P2","Upper"]<1

def test_conflicting_assessment():
    d=fixture(); r=dict(d["Capability Assessment"]["rows"][0])
    r.update({"Assessment ID":"DEMO-CONFLICT","Availability Status":"Explicitly unsupported"})
    d["Capability Assessment"]["rows"].append(r)
    assert matrix(d).loc["DEMO-P1","DEMO-C1"]=="Disputed"

def test_sparse_similarity():
    d=fixture(); m=matrix(d)
    assert similarity(m,2).empty
    assert not similarity(m,1).empty
    assert clusters(m,2)[0].empty
    assert not research_gaps(d,m).empty
    assert not capability_gaps(d,m,{"DEMO-C1":"Planned"}).empty
