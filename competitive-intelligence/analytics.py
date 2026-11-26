"""Pure analytical functions. Missing evidence is never an unsupported feature."""
from collections import defaultdict
from itertools import combinations
import numpy as np
import pandas as pd
from core import records, value, split_ids

KNOWN = {"Supported":1.0, "Partially supported":0.5, "Explicitly unsupported":0.0}
DISPLAY = ["Unassessed","Unknown","Explicitly unsupported","Announced","Partially supported","Supported","Not applicable","Disputed","Proposed"]
EVIDENCE_RANK = {"Insufficient evidence":0,"Inferred":1,"Vendor claim":2,"Official technical documentation":3,"Independently documented":4,"Independently verified":5}

def frame(data, tab):
    return pd.DataFrame(records(data,tab),columns=data[tab]["headers"])

def current_assessments(data):
    rows=records(data,"Capability Assessment")
    # Only a reviewed replacement may retire earlier evidence.
    superseded={value(r,"Supersedes Assessment ID") for r in rows if value(r,"Review Status")=="Reviewed"}
    grouped=defaultdict(list)
    for r in rows:
        if value(r,"Assessment ID") not in superseded and value(r,"Review Status")!="Superseded":
            grouped[(value(r,"Product ID"),value(r,"Capability ID"))].append(r)
    out=[]
    for (p,c), group in grouped.items():
        reviewed=[r for r in group if value(r,"Review Status")=="Reviewed"]
        statuses={value(r,"Availability Status") for r in reviewed}
        # Divergent conditions/versions are retained for inspection, not averaged.
        if any(value(r,"Review Status")=="Disputed" for r in group) or len(statuses)>1:
            status="Disputed"
        elif not reviewed:
            status="Proposed"
        else:
            status=next(iter(statuses))
        evidence=max((value(r,"Evidence Level") for r in reviewed),key=lambda x:EVIDENCE_RANK.get(x,-1),default="")
        out.append({"Product ID":p,"Capability ID":c,"Status":status,"Evidence Level":evidence,
                    "Assessment IDs":"; ".join(value(r,"Assessment ID") for r in group),
                    "Evidence count":len(group)})
    return pd.DataFrame(out,columns=["Product ID","Capability ID","Status","Evidence Level","Assessment IDs","Evidence count"])

def active_capabilities(data):
    return [r for r in records(data,"Capabilities") if value(r,"Taxonomy Status")=="Active"]

def matrix(data, product_ids=None, capability_ids=None):
    products=product_ids if product_ids is not None else [value(r,"Product ID") for r in records(data,"Products")]
    caps=capability_ids if capability_ids is not None else [value(r,"Capability ID") for r in active_capabilities(data)]
    a=current_assessments(data)
    if a.empty:
        return pd.DataFrame("Unassessed",index=products,columns=caps)
    return a.pivot(index="Product ID",columns="Capability ID",values="Status").reindex(index=products,columns=caps).fillna("Unassessed")

def coverage(mat):
    n=mat.size
    assessed=int((mat!="Unassessed").to_numpy().sum())
    determinate=int(mat.isin(list(KNOWN)).to_numpy().sum())
    applicable=int((mat!="Not applicable").to_numpy().sum())
    return {"pairs":n,"assessed":assessed,"determinate":determinate,"coverage":assessed/n if n else 0,
            "applicable_or_unknown":applicable}

def score_bounds(mat, weights):
    """Weighted functional overlap interval, not a commercial threat probability.
    Known partial=0.5 by explicit convention; announced, unknown, proposed and
    disputed remain [0,1]. Not applicable is omitted from denominator."""
    w=pd.Series(weights,dtype=float).reindex(mat.columns).fillna(0).clip(lower=0)
    rows=[]
    for pid,r in mat.iterrows():
        applicable=r!="Not applicable"
        total=float(w[applicable].sum())
        if total<=0:
            rows.append({"Product ID":pid,"Lower":np.nan,"Upper":np.nan,"Known weight":np.nan})
            continue
        known=r.isin(KNOWN)
        low=float((r.map(KNOWN).fillna(0)*w).sum()/total)
        known_weight=float(w[known].sum()/total)
        rows.append({"Product ID":pid,"Lower":low,"Upper":min(1.,low+1-known_weight),"Known weight":known_weight})
    return pd.DataFrame(rows,columns=["Product ID","Lower","Upper","Known weight"])

def sensitivity(mat,weights,n=250,seed=42):
    """Random multiplicative weight perturbations; rank by lower bound only.
    This is sensitivity of evidence-backed lower bounds, not probability."""
    rng=np.random.default_rng(seed)
    w=pd.Series(weights,dtype=float).reindex(mat.columns).fillna(0)
    ranks=defaultdict(list)
    for _ in range(n):
        sample=w*np.exp(rng.normal(0,.35,len(w)))
        scored=score_bounds(mat,sample).set_index("Product ID")["Lower"]
        for k,v in scored.rank(ascending=False,method="min").dropna().items():
            ranks[k].append(v)
    return pd.DataFrame([{"Product ID":k,"Best rank":min(v),"Median rank":float(np.median(v)),"Worst rank":max(v)} for k,v in ranks.items()])

def research_gaps(data,mat,priority_caps=()):
    products={value(r,"Product ID"):r for r in records(data,"Products")}
    caps={value(r,"Capability ID"):r for r in active_capabilities(data)}
    a=current_assessments(data)
    ev={(r["Product ID"],r["Capability ID"]):r["Evidence Level"] for r in a.to_dict("records")}
    priority_caps=set(priority_caps)
    rows=[]
    for pid,r in mat.iterrows():
        for cid,status in r.items():
            evidence=ev.get((pid,cid),"")
            weak=status in KNOWN and EVIDENCE_RANK.get(evidence,0)<=2
            if status not in ("Unknown","Unassessed","Announced","Disputed","Proposed") and not weak:
                continue
            role=value(products.get(pid,{}),"Competition Type")
            priority=value(products.get(pid,{}),"Strategic Priority").lower()
            score={"high":3,"medium":2,"low":1}.get(priority,1)+(2 if cid in priority_caps else 0)+(2 if role=="Direct" else 0)+(3 if status=="Disputed" else 0)
            rows.append({"Product ID":pid,"Product":value(products.get(pid,{}),"Product Name"),
                        "Capability ID":cid,"Capability":value(caps.get(cid,{}),"Capability Name"),
                        "Status":status,"Evidence":evidence,"Research priority":score,
                        "Question":f"Does this product support {value(caps.get(cid,{}),'Capability Name')} under the defined conditions?"})
    if not rows:
        return pd.DataFrame(columns=["Product ID","Product","Capability ID","Capability","Status","Evidence","Research priority","Question"])
    return pd.DataFrame(rows).sort_values(["Research priority","Product ID","Capability ID"],ascending=[False,True,True])

def similarity(mat,min_shared=5):
    rows=[]
    for a,b in combinations(mat.index,2):
        x,y=mat.loc[a].map(KNOWN),mat.loc[b].map(KNOWN)
        shared=x.notna()&y.notna()
        n=int(shared.sum())
        if n<min_shared:
            continue
        s=1-float((x[shared]-y[shared]).abs().mean())
        rows.append({"Product A":a,"Product B":b,"Shared determinate":n,"Similarity":s})
    return pd.DataFrame(rows,columns=["Product A","Product B","Shared determinate","Similarity"])

def clusters(mat,min_shared=5,threshold=.25):
    """Complete-linkage clustering only on a subset with all pair distances.
    Deterministically remove least-connected products until complete.
    Never impute unknown distances."""
    from scipy.cluster.hierarchy import linkage,fcluster
    from scipy.spatial.distance import squareform
    sim=similarity(mat,min_shared)
    ids=list(mat.index)
    pairs={(r["Product A"],r["Product B"]):r["Similarity"] for r in sim.to_dict("records")}
    pairs.update({(b,a):v for (a,b),v in list(pairs.items())})
    dropped=[]
    while len(ids)>1:
        miss={a:sum((a,b) not in pairs for b in ids if b!=a) for a in ids}
        if not max(miss.values()):
            break
        worst=sorted(ids,key=lambda a:(-miss[a],a))[0]
        ids.remove(worst); dropped.append(worst)
    if len(ids)<2:
        return pd.DataFrame(columns=["Product ID","Cluster"]),dropped+ids
    dist=np.array([[0 if a==b else 1-pairs[(a,b)] for b in ids] for a in ids])
    labels=fcluster(linkage(squareform(dist),method="complete"),t=threshold,criterion="distance")
    return pd.DataFrame({"Product ID":ids,"Cluster":labels}),dropped

def graph(data, product_ids, include_evidence=False):
    import networkx as nx
    g=nx.Graph()
    products={value(r,"Product ID"):r for r in records(data,"Products")}
    companies={value(r,"Company ID"):r for r in records(data,"Companies")}
    caps={value(r,"Capability ID"):r for r in records(data,"Capabilities")}
    for pid in product_ids:
        p=products[pid]; co=value(p,"Company ID")
        g.add_node(pid,label=value(p,"Product Name"),kind="Product")
        g.add_node(co,label=value(companies.get(co,{}),"Company Name") or co,kind="Company")
        g.add_edge(co,pid,relation="offers")
    for r in current_assessments(data).to_dict("records"):
        pid,cid=r["Product ID"],r["Capability ID"]
        if pid in product_ids and r["Status"] in ("Supported","Partially supported"):
            g.add_node(cid,label=value(caps.get(cid,{}),"Capability Name") or cid,kind="Capability")
            g.add_edge(pid,cid,relation=r["Status"])
    for r in records(data,"Deployments"):
        pid=value(r,"Product ID"); customer=value(r,"Customer Organisation")
        if pid in product_ids and customer:
            # Keep distinct deployments as nodes to avoid implying unsupported
            # equivalence or direct commercial contracts.
            did=value(r,"Deployment ID")
            g.add_node(did,label=customer+" · "+value(r,"Deployment Status"),kind="Deployment")
            g.add_edge(pid,did,relation=value(r,"Deployment Status") or "reported record")
    if include_evidence:
        for r in records(data,"Capability Assessment"):
            pid=value(r,"Product ID")
            if pid not in product_ids: continue
            aid=value(r,"Assessment ID")
            g.add_node(aid,label=aid,kind="Assessment")
            g.add_edge(pid,aid,relation="assessment")
            for o in split_ids(r.get("Related Observation IDs"))+split_ids(r.get("Related Evidence IDs")):
                g.add_node(o,label=o,kind="Evidence")
                g.add_edge(aid,o,relation="references")
    return g

def capability_gaps(data,mat,targets):
    # Explicitly report denominator and uncertainty; no claim of demand.
    rows=[]
    for cid in targets:
        if cid not in mat: continue
        s=mat[cid]
        counts=s.value_counts()
        rows.append({"Capability ID":cid,"AIT-VISTA target maturity":targets[cid],
                     "Supported":int(counts.get("Supported",0)),
                     "Partial":int(counts.get("Partially supported",0)),
                     "Explicitly unsupported":int(counts.get("Explicitly unsupported",0)),
                     "Unassessed":int(counts.get("Unassessed",0)),
                     "Other unresolved":int(s.isin(["Unknown","Announced","Disputed","Proposed"]).sum()),
                     "Not applicable":int(counts.get("Not applicable",0))})
    return pd.DataFrame(rows)
