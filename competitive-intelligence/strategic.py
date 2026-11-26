"""Decision-support methods with explicit evidence coverage and uncertainty."""
from collections import defaultdict
from datetime import date
import numpy as np
import pandas as pd
from core import records,value
from analytics import matrix,current_assessments,score_bounds,KNOWN,EVIDENCE_RANK
from product_intelligence import target_ids

SPACE_STRONG={"Space manufacturing deployment","Space AIT deployment"}
SPACE_OFFER={"Space offering","Space manufacturing adoption signal","Space AIT R&D","Space AIT R&D heritage","Space industry only","Planned space application"}
IMPLEMENTED={"Reported implementation","Documented implementation"}
CRITERIA=["Functional overlap","Space relevance","Commercial availability","Documented adoption"]

def commercial_mcda(data, mat, capability_weights, criterion_weights):
    """Scenario scoring convention, not calibrated threat probability.
    Positive observations imply a documented lower bound only; no undocumented
    adoption, negative evidence or commercial absence is invented."""
    overlap=score_bounds(mat,capability_weights).set_index("Product ID")
    products={value(r,"Product ID"):r for r in records(data,"Products")}
    deployments=defaultdict(list)
    for r in records(data,"Deployments"):
        if value(r,"Deployment Status") in IMPLEMENTED:
            deployments[value(r,"Product ID")].append(r)
    rows=[]
    for pid in mat.index:
        p=products[pid]
        o=overlap.loc[pid]
        functional=(float(o.Lower),float(o.Upper)) if pd.notna(o.Lower) else (0.,1.)
        space=value(p,"Space Industry Applicability")
        space_interval=(1.,1.) if space in SPACE_STRONG else (.5,1.) if space in SPACE_OFFER else (0.,1.)
        commercial=value(p,"Commercial Status")
        commercial_interval=(1.,1.) if commercial=="Commercial" else (0.,.5) if commercial in {"Announced","Research","Historical","Internal / custom"} else (0.,1.)
        dep=deployments[pid]
        adoption=(1.,1.) if any(value(r,"Deployment Status")=="Documented implementation" for r in dep) else (.5,1.) if dep else (0.,1.)
        intervals=dict(zip(CRITERIA,[functional,space_interval,commercial_interval,adoption]))
        w={k:max(0.,float(criterion_weights.get(k,0))) for k in CRITERIA}
        total=sum(w.values())
        lo=sum(w[k]*intervals[k][0] for k in CRITERIA)/total if total else np.nan
        hi=sum(w[k]*intervals[k][1] for k in CRITERIA)/total if total else np.nan
        rows.append({"Product ID":pid,"Product":value(p,"Product Name"),"Lower":lo,"Upper":hi,
                     "Uncertainty width":hi-lo,"Space evidence":space,"Commercial status":commercial,
                     "Implementation records":len(dep),**{k+" lower":v[0] for k,v in intervals.items()},
                     **{k+" upper":v[1] for k,v in intervals.items()}})
    return pd.DataFrame(rows)

def convergence(before,after,cap_ids,weights=None):
    """Fixed shared product/capability cohort and common weights.
    Change in observed overlap is not evidence of product introduction."""
    old=matrix(before); new=matrix(after)
    p=sorted(set(old.index)&set(new.index))
    c=sorted(set(old.columns)&set(new.columns)&set(cap_ids))
    if not p or not c: return pd.DataFrame()
    old=old.loc[p,c]; new=new.loc[p,c]
    w={k:1 for k in c} if weights is None else {k:weights.get(k,0) for k in c}
    a=score_bounds(old,w).set_index("Product ID"); b=score_bounds(new,w).set_index("Product ID")
    rows=[]
    for pid in p:
        shared=old.loc[pid].isin(KNOWN)&new.loc[pid].isin(KNOWN)
        count=int(shared.sum())
        common=[k for k in c if shared[k] and w[k]>0]
        denom=sum(w[k] for k in common)
        change=sum(w[k]*(KNOWN[new.loc[pid,k]]-KNOWN[old.loc[pid,k]]) for k in common)/denom if denom else np.nan
        rows.append({"Product ID":pid,"Common capabilities":len(c),"Jointly determinate":count,
                     "Baseline lower":a.loc[pid,"Lower"],"Baseline upper":a.loc[pid,"Upper"],
                     "Current lower":b.loc[pid,"Lower"],"Current upper":b.loc[pid,"Upper"],
                     "Baseline known weight":a.loc[pid,"Known weight"],"Current known weight":b.loc[pid,"Known weight"],
                     "Change on jointly determinate proxies":change,
                     "Newly determinate":int((~old.loc[pid].isin(KNOWN)&new.loc[pid].isin(KNOWN)).sum())})
    return pd.DataFrame(rows)

def transitions(before,after):
    old=current_assessments(before); new=current_assessments(after)
    key=["Product ID","Capability ID"]
    a=old.set_index(key); b=new.set_index(key)
    rows=[]
    for pair in sorted(set(a.index)|set(b.index)):
        x=a.loc[pair] if pair in a.index else None; y=b.loc[pair] if pair in b.index else None
        s0=x["Status"] if x is not None else "Unassessed"; s1=y["Status"] if y is not None else "Unassessed"
        e0=x["Evidence Level"] if x is not None else ""; e1=y["Evidence Level"] if y is not None else ""
        if (s0,e0)==(s1,e1): continue
        rows.append({"Product ID":pair[0],"Capability ID":pair[1],"Before":s0,"After":s1,
                     "Evidence before":e0,"Evidence after":e1,
                     "Change type":"New recorded assessment" if s0=="Unassessed" else "Availability assessment changed" if s0!=s1 else "Evidence changed",
                     "Before assessment IDs":x["Assessment IDs"] if x is not None else "",
                     "After assessment IDs":y["Assessment IDs"] if y is not None else ""})
    return pd.DataFrame(rows)

def stale_evidence(data, days=90, today=None):
    today=pd.Timestamp(today or date.today())
    active=current_assessments(data)
    ids={v for s in active.get("Assessment IDs",[]) for v in str(s).split("; ")}
    rows=[]
    for r in records(data,"Capability Assessment"):
        if value(r,"Assessment ID") not in ids: continue
        checked=pd.to_datetime(value(r,"Source Checked Date"),errors="coerce",utc=True)
        age=(today.date()-checked.date()).days if pd.notna(checked) else None
        if age is None or age>=days or age<0:
            rows.append({"Assessment ID":value(r,"Assessment ID"),"Product ID":value(r,"Product ID"),
                         "Capability ID":value(r,"Capability ID"),"Checked":value(r,"Source Checked Date"),
                         "Age days":age,"Reason":"Missing/invalid date" if age is None or age<0 else "Review due",
                         "Source URL":value(r,"Source URL")})
    return pd.DataFrame(rows)

def opportunity_register(data,mat,targets,demand=None):
    """Hypothesis generator. No market validation from competitor absence."""
    demand=demand or {}
    a=current_assessments(data)
    rows=[]
    for cid in targets:
        if cid not in mat: continue
        s=mat[cid]; supported=int((s=="Supported").sum()); partial=int((s=="Partially supported").sum())
        unsupported=int((s=="Explicitly unsupported").sum())
        unresolved=int(s.isin(["Unassessed","Unknown","Announced","Proposed","Disputed"]).sum())
        eligible=len(s)-int((s=="Not applicable").sum())
        positive=a[(a["Capability ID"]==cid)&a["Product ID"].isin(s.index)&a["Status"].isin(["Supported","Partially supported"])]
        validated=demand.get(cid,{})
        demand_state=validated.get("status","Unvalidated") if isinstance(validated,dict) else "Unvalidated"
        demand_ref=validated.get("reference","") if isinstance(validated,dict) else ""
        if demand_state!="Validated" or not demand_ref: demand_state="Unvalidated"
        if unresolved: action="Research market coverage; test demand"
        elif supported+partial==0 and unsupported: action="Investigate differentiation and willingness to pay"
        elif supported+partial: action="Compare implementation; evaluate build / integrate / buy"
        else: action="Check applicability"
        rows.append({"Capability ID":cid,"Eligible products":eligible,"Supported":supported,"Partial":partial,
                     "Unsupported":unsupported,"Unresolved":unresolved,"Coverage":(supported+partial+unsupported)/eligible if eligible else None,
                     "Demand":demand_state,"Demand reference":demand_ref,
                     "Possible suppliers / integration candidates":"; ".join(sorted(set(positive["Product ID"]))),
                     "Next action":action})
    return pd.DataFrame(rows)

def integration_candidates(data,mat,targets):
    """Capability overlap only; no claim that integration is feasible or partner willing."""
    latest=current_assessments(data)
    products={value(r,"Product ID"):r for r in records(data,"Products")}
    rows=[]
    for pid in mat.index:
        subset=latest[(latest["Product ID"]==pid)&latest["Capability ID"].isin(targets)&latest["Status"].isin(["Supported","Partially supported"])]
        if subset.empty: continue
        p=products[pid]
        rows.append({"Product ID":pid,"Product":value(p,"Product Name"),"Competition Type":value(p,"Competition Type"),
                     "Matching proxies":len(subset),"Capability IDs":"; ".join(subset["Capability ID"]),
                     "Assessment IDs":"; ".join(subset["Assessment IDs"]),
                     "Deployment architecture":value(p,"Deployment Architecture"),
                     "Next diligence":"Verify API, deployment, security, licence, cost and supplier willingness"})
    return pd.DataFrame(rows)
