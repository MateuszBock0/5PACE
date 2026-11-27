"""Evidence-first response triage. No calibrated threat score or new data store."""
from collections import defaultdict
import math
import pandas as pd
from core import value,digest
from command_engine import direct_current,registry,profile
from product_intelligence import CRITERIA
from analytics import EVIDENCE_RANK
from decision import importance_lane

LABELS={"003":"Physical configuration","004":"Observed AIT execution","002":"Automated documentation","005":"Passive recording","006":"Real-time feedback","008":"Mechanism dynamics","020":"Local / offline","021":"Standalone end-to-end","022":"Vendor independence","026":"No mandatory GenAI","029":"Step evidence links","034":"Report templates"}
STRATEGIC_IDS=["AV-CR-"+x for x in LABELS]
def selected_criteria(data):
    c=registry(data,CRITERIA,"Criterion ID")
    return [x for x in STRATEGIC_IDS if x in c] or list(c)[:12]

def short_criterion(cid,fallback):
    return LABELS.get(cid.removeprefix("AV-CR-"),fallback)

def exposure(data,cfg,ids,cids=None):
    """Strongest positive recorded verdict per criterion, not a union of products."""
    cids=selected_criteria(data) if cids is None else cids
    criteria=registry(data,CRITERIA,"Criterion ID");products=registry(data,"Products","Product ID")
    ledger=direct_current(data)
    out=[]
    for c in cids:
        if c not in criteria:continue
        found=[];unresolved=0
        for p in ids:
            e=ledger.get((p,c),{});s=e.get("status","Unassessed")
            if s in {"Supported","Partially supported","Explicitly unsupported"}:
                for r in e.get("rows",[]):
                    found.append((p,s,value(r,"Evidence level"),r))
            elif s!="Not applicable":unresolved+=1
        positives=[x for x in found if x[1] in {"Supported","Partially supported"}]
        positives.sort(key=lambda x:(x[1]=="Supported",EVIDENCE_RANK.get(x[2],-1),value(x[3],"Assessment date")),reverse=True)
        negatives=[x for x in found if x[1]=="Explicitly unsupported"]
        negatives.sort(key=lambda x:EVIDENCE_RANK.get(x[2],-1),reverse=True)
        best=(positives or negatives or [(None,"Unresolved","",{})])[0]
        p,s,e,r=best
        overlap="Full recorded" if s=="Supported" else "Partial recorded" if s=="Partially supported" else "No positive record / unresolved"
        imp=importance_lane(cfg,c)
        strong=EVIDENCE_RANK.get(e,-1)>=3
        if s=="Supported":
            action="React" if imp=="High" and strong else "Benchmark"
            why="Compare operating conditions and measured performance; do not claim uniqueness."
        elif s=="Partially supported":
            action="React" if imp=="High" and strong else "Research"
            why="Verify the full scope, limitations and customer value."
        elif unresolved or not ids or (s=="Explicitly unsupported" and not strong):
            action="Research";why="Resolve missing or disputed assessments before inferring differentiation."
        else:
            action="Monitor";why="Review bounded non-support and applicability; do not extrapolate to market-wide absence."
        out.append({"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"Short criterion":short_criterion(c,value(criteria[c],"Product criterion")),"AIT-VISTA":profile(cfg,c,"As-Is"),"Overlap":overlap,"Importance":imp,"Action":action,"Next decision":why,"Product ID":p or "","Product":value(products.get(p,{}),"Product Name"),"Verdict":s,"Evidence":e,"Assessment date":value(r,"Assessment date"),"Comparison ID":value(r,"Comparison ID"),"Source":value(r,"Source URLs"),"Unresolved":unresolved})
    result=pd.DataFrame(out)
    if result.empty:return result
    ranked=priority_records(exposure_records(data,cfg,ids,cids))
    if ranked.empty:return result
    for i,r in result.iterrows():
        g=ranked[ranked["Criterion ID"]==r["Criterion ID"]]
        # A stronger partial claim with high customer importance must not
        # disappear behind a weak full claim. Preserve existing unresolved
        # summary when there is no positive or explicit negative record.
        actionable=g[g.Verdict.isin(["Supported","Partially supported","Explicitly unsupported"])]
        if not actionable.empty:
            best=actionable.iloc[0]
            if best.Action=="React":
                for k in ["Overlap","Action","Next decision","Product ID","Product","Verdict","Evidence","Assessment date","Comparison ID","Source"]:
                    result.loc[i,k]=best[k]
    return result

def threat_cohort(data,rows):
    from founder import strategic_map_cohort
    return strategic_map_cohort(rows)

def spread_points(rows,x="X",y="Y",radius=.27,reference=None):
    """Display-only grid offsets, including exact co-location. Original axes unchanged."""
    d=rows.copy();d["Display X"]=d[x].astype(float);d["Display Y"]=d[y].astype(float)
    for (a,b),g in d.groupby([x,y],sort=False):
        n=len(g);with_ref=reference is not None and abs(a-reference[0])<1e-9 and abs(b-reference[1])<1e-9
        if n==1 and not with_ref:continue
        # Multiple rings / square grid, deterministic by ID. Reserve centre for reference.
        side=max(3,math.ceil(math.sqrt(n+int(with_ref))))
        if side%2==0:side+=1
        slots=[(i,j) for i in range(side) for j in range(side) if not(with_ref and i==side//2 and j==side//2)]
        slots.sort(key=lambda q:((q[0]-side//2)**2+(q[1]-side//2)**2,q))
        for idx,(i,j) in zip(g.sort_values("Product ID").index,slots):
            d.loc[idx,"Display X"]=a+radius*(i-side//2)/(side//2)
            d.loc[idx,"Display Y"]=b+radius*(j-side//2)/(side//2)
    return d

def report_provenance(data,mode,captured="",snapshot_hash="",source=""):
    if str(mode).upper().startswith("SYNTHETIC"):
        return "Not applicable (synthetic)", "synthetic-"+digest(data), "Synthetic fixture"
    return captured,snapshot_hash or digest(data),source

def exposure_records(data,cfg,ids,cids=None):
    """Every active record (including disputed raw verdicts), plus explicit unresolved pairs.
    Each action uses its own record evidence, never the strongest grade of a different verdict.
    """
    criteria=registry(data,CRITERIA,"Criterion ID");products=registry(data,"Products","Product ID")
    ledger=direct_current(data);out=[]
    for c in selected_criteria(data) if cids is None else cids:
        if c not in criteria:continue
        imp=importance_lane(cfg,c)
        for pid in ids:
            pair=ledger.get((pid,c),{})
            status=pair.get("status","Unassessed")
            for r in pair.get("rows",[]) or [{}]:
                grade=value(r,"Evidence level")
                strong=EVIDENCE_RANK.get(grade,-1)>=3
                positive=status in {"Supported","Partially supported"}
                action="React" if positive and strong and imp=="High" else "Benchmark" if status=="Supported" else "Monitor" if status=="Not applicable" or (status=="Explicitly unsupported" and strong) else "Research"
                reason={"React":"Review competitive response with customer-value evidence; benchmark actual performance.","Benchmark":"Compare operating conditions and measured performance; no uniqueness claim.","Research":"Resolve scope, limitations, evidence and customer value before claiming differentiation.","Monitor":"Track bounded non-support or applicability; do not infer market-wide absence."}[action]
                out.append({"Product ID":pid,"Product":value(products.get(pid,{}),"Product Name"),"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"Short criterion":short_criterion(c,value(criteria[c],"Product criterion")),"Verdict":status,"Record verdict":value(r,"Verdict") or "Unassessed","Evidence":grade,"Assessment date":value(r,"Assessment date"),"Comparison ID":value(r,"Comparison ID"),"Source":value(r,"Source URLs"),"Limitations":value(r,"Limitations"),"Importance":imp,"Action":action,"Next decision":reason,"Overlap":"Full recorded" if status=="Supported" else "Partial recorded" if status=="Partially supported" else "No positive record / unresolved"})
    return pd.DataFrame(out)

def priority_records(records,changed_pairs=()):
    """Provisional review ordering, no numerical threat score.
    A material recorded change is a verdict/evidence change, not a verified market event.
    """
    if records.empty:return records.copy()
    d=records.copy()
    changed=set(changed_pairs)
    d["Material recorded change"]=[(p,c) in changed for p,c in zip(d["Product ID"],d["Criterion ID"])]
    d["_action"]=d.Action.map({"React":0,"Benchmark":1,"Research":2,"Monitor":3})
    d["_importance"]=d.Importance.map({"High":0,"Medium":1,"Low":2,"Unresolved":3})
    d["_positive"]=d.Verdict.map({"Supported":0,"Partially supported":1}).fillna(2)
    d["_evidence"]=d.Evidence.map(EVIDENCE_RANK).fillna(-1)
    return d.sort_values(["_action","_importance","_positive","_evidence","Material recorded change","Assessment date","Criterion ID","Product ID","Comparison ID"],ascending=[True,True,True,False,False,False,True,True,True]).drop(columns=["_action","_importance","_positive","_evidence"])

def headline_records(records,changed_pairs=()):
    """Separate confirmed overlap from a positive but incomplete/ emerging research question."""
    ranked=priority_records(records,changed_pairs)
    if ranked.empty:return ranked
    parity=ranked[ranked.Action.isin(["React","Benchmark"])].head(2)
    partial=ranked[(ranked.Action=="Research") & (ranked.Verdict=="Partially supported")].head(1)
    unresolved=ranked[ranked.Action=="Research"].head(1)
    focus=partial if not partial.empty else unresolved
    return pd.concat([parity,focus]).drop_duplicates(["Product ID","Criterion ID","Comparison ID"])

def material_pairs(before,after):
    if before is None:return set()
    a=direct_current(before);b=direct_current(after)
    return {pair for pair,r in b.items() if (r["status"],r["evidence"])!=(a.get(pair,{}).get("status","Unassessed"),a.get(pair,{}).get("evidence",""))}
