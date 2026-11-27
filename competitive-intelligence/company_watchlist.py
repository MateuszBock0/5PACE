"""Company watchlist derived from immutable snapshots; no source writes."""
import re
import pandas as pd
from core import value, split_ids
from command_engine import registry, direct_current
from founder import CORE_IDS, summaries
from product_intelligence import CRITERIA
from analytics import EVIDENCE_RANK
from company_portfolio import portfolio_data, CREDIT
from decision import SPACE, NEG
from space_research import relevance

UNRESOLVED={"Unknown","Unassessed","Announced","Disputed"}
PARTIAL_GAP=re.compile(r"\b(unclear|unknown|unconfirmed|unverified|not established|not documented|not confirmed|not demonstrated|requires verification|not specified)\b",re.I)
SPACE_TERM=re.compile(r"\b(space|spacecraft|satellites?)\b",re.I)
COLUMNS=["Company ID","Company","Priority","Watch Reason","Space Target","Space Confirmed","Reported space implementation","Space research / other signal","Space evidence IDs","Space sources","Best Product ID","Best Product","Best Product Overlap","Portfolio Overlap","Commercial-only overlap","Product count","Research basis","Research product IDs","Gap criteria","Unverified Claims","Unknown","Unassessed","Announced","Disputed","Partial scope gaps","Evidence Completeness","Determinate completeness","Last Reviewed","Next Action"]
DETAIL=["Company ID","Product ID","Product","Criterion ID","Criterion","Verdict","Evidence level","Gap reason","Comparison IDs","Source URLs","Rationale","Limitations","Assessment date"]

def _space_statement(s):
    return any(SPACE_TERM.search(x) and not re.search(NEG,x,re.I) for x in re.split(r"[;.\n]",s))

def _joined(items):
    return "; ".join(sorted({str(x) for x in items if x}))

def _space_flags(data,co,products,deps,obs,positions):
    target=[]; confirmed=[]; reported=[]; other=[]; refs=[]; urls=[]; scoped=set()
    cid=value(co,"Company ID"); presence=value(co,"Space Industry Presence")
    if presence in {"Documented presence","Documented presence outside AIT"} and (value(co,"Source URL") or value(co,"Space Industry Evidence")):
        confirmed.append("Company-level documented presence: "+presence)
        refs+=split_ids(co.get("Space Industry Evidence"))
        urls.append(value(co,"Source URL"))
    if _space_statement(value(co,"Target Industries")) and value(co,"Source URL"):
        target.append("Company-level target statement")
        urls.append(value(co,"Source URL"))
    for p in products:
        pid=value(p,"Product ID")
        pdps=[d for d in deps if value(d,"Product ID")==pid]
        kind,ids,links,space=relevance(p,co,pdps,obs)
        if space:
            scoped.add(pid);refs+=ids;urls+=links
            if kind in {"Space offering","Planned space application","Product-specific space target statement"}:
                target.append(pid+" — "+kind)
            elif kind in {"Space AIT R&D","Space AIT R&D heritage","Space industry only","Space manufacturing adoption signal","Space manufacturing deployment","Space AIT deployment","Product-specific space deployment / demonstration record"}:
                other.append(pid+" — "+kind)
        if positions.get(pid)=="Space AIT target segment" and (value(p,"Product URL") or value(p,"Documentation URL")):
            scoped.add(pid);target.append(pid+" — target segment")
            refs+=split_ids(p.get("Related Observation IDs"));urls.append(value(p,"Product URL") or value(p,"Documentation URL"))
        # Do not infer confirmed space implementation from marketing, demonstrations or company heritage.
        for d in pdps:
            industry=value(d,"Industry")
            if not (re.search(SPACE,industry,re.I) or _space_statement(industry)) or re.search(NEG,industry,re.I) or not value(d,"Source URL"):continue
            status=value(d,"Deployment Status")
            if status not in {"Documented implementation","Reported implementation"}:continue
            scoped.add(pid);refs.append(value(d,"Deployment ID"));urls.append(value(d,"Source URL"))
            label=pid+" — "+(value(d,"Customer Organisation") or "Unnamed customer")
            (confirmed if status=="Documented implementation" else reported).append(label)
    for ref in refs:
        urls.append(value(obs.get(ref,{}),"Source URL"))
    return target,confirmed,reported,other,refs,urls,scoped

def _gap_row(pid,p,c,e,criterion):
    s=e.get("status","Unassessed"); grade=e.get("evidence",""); records=e.get("rows",[])
    weak=s in CREDIT and EVIDENCE_RANK.get(grade,-1)<3
    partial=s=="Partially supported" and any(PARTIAL_GAP.search(value(r,"Limitations")+" "+value(r,"Assessment rationale")) for r in records)
    reason=_joined([s if s in UNRESOLVED else "", "Positive claim below technical documentation" if weak else "", "Partial scope unresolved" if partial else ""])
    return {"Company ID":value(p,"Company ID"),"Product ID":pid,"Product":value(p,"Product Name"),"Criterion ID":c,"Criterion":value(criterion,"Product criterion") or c,"Verdict":s,"Evidence level":grade,"Gap reason":reason,"Comparison IDs":_joined(value(r,"Comparison ID") for r in records),"Source URLs":_joined(value(r,"Source URLs") for r in records),"Rationale":"\n".join(value(r,"Assessment rationale") for r in records),"Limitations":"\n".join(value(r,"Limitations") for r in records),"Assessment date":max([value(r,"Assessment date") for r in records] or [""])},weak,partial

def watchlist(data,threshold=.20,min_gaps=3):
    """Company-level A OR B OR (C AND gaps). Distinct criterion gap count, not pair count."""
    if not 0<=threshold<=1 or not 1<=min_gaps<=8:raise ValueError("Invalid watchlist thresholds")
    companies=registry(data,"Companies","Company ID");pro=registry(data,"Products","Product ID")
    criteria=registry(data,CRITERIA,"Criterion ID");obs=registry(data,"Observations","Observation ID")
    ledger=direct_current(data);deps=data.get("Deployments",{}).get("rows",[])
    rows=summaries(data);pf,_=portfolio_data(data,rows)
    positions=dict(zip(rows["Product ID"],rows["Customer position"])) if not rows.empty else {}
    overlaps=dict(zip(rows["Product ID"],rows["Recorded overlap fraction"])) if not rows.empty else {}
    by_company={r["Company ID"]:r for _,r in pf.iterrows()}
    out=[];details={}
    for cid,co in companies.items():
        products=[p for p in pro.values() if value(p,"Company ID")==cid]
        pids=[value(p,"Product ID") for p in products]
        target,confirmed,reported,other,refs,urls,space_ids=_space_flags(data,co,products,deps,obs,positions)
        r=by_company.get(cid,{})
        union=float(r.get("Portfolio coverage",0));best=float(r.get("Best single product coverage",0))
        positive={pid for pid in pids if overlaps.get(pid,0)>0}
        basis=space_ids|positive
        basis_label="Space-relevant and positive-overlap products"
        if not basis and (target or confirmed or reported or other):
            basis=set(pids);basis_label="Company-only exploratory review; product relevance unconfirmed"
        if not basis:basis_label="No eligible product research basis"
        pairs=[];weak_count=partial_count=0
        for pid in sorted(basis):
            for c in CORE_IDS:
                detail,weak,partial=_gap_row(pid,pro[pid],c,ledger.get((pid,c),{}),criteria.get(c,{}))
                pairs.append(detail);weak_count+=weak;partial_count+=partial
        gaps={p["Criterion ID"] for p in pairs if p["Gap reason"]}
        # The technology trigger uses only positively overlapping products, not unrelated space products.
        tech_gaps={p["Criterion ID"] for p in pairs if p["Gap reason"] and p["Product ID"] in positive}
        tech=union>threshold and len(tech_gaps)>=min_gaps
        if not (target or confirmed or reported or other or tech):continue
        reasons=[x for x,y in [("Space Target",target),("Space Confirmed",confirmed),("Reported space implementation",reported),("Space research / other signal",other),("Technology exposure",tech)] if y]
        significant=len(gaps)>=min_gaps
        priority="P0" if confirmed and significant else "P1" if (target or reported or other) and significant else "P2" if tech else "P3"
        d=pd.DataFrame(pairs,columns=DETAIL);details[cid]=d
        state_counts=d["Verdict"].value_counts().to_dict()
        gap_names=[value(criteria.get(c,{}),"Product criterion") or c for c in CORE_IDS if c in gaps]
        best_ids=str(r.get("Best product IDs","")).split("; ")
        best_pid=best_ids[0] if best_ids[0] else (pids[0] if pids else "")
        out.append({"Company ID":cid,"Company":value(co,"Company Name") or cid,"Priority":priority,"Watch Reason":"; ".join(reasons),
            "Space Target":_joined(target),"Space Confirmed":_joined(confirmed),"Reported space implementation":_joined(reported),"Space research / other signal":_joined(other),
            "Space evidence IDs":_joined(refs),"Space sources":_joined(urls),"Best Product ID":best_pid,"Best Product":str(r.get("Best product ties","")),
            "Best Product Overlap":best,"Portfolio Overlap":union,"Commercial-only overlap":float(r.get("Commercial-only coverage",0)),"Product count":len(pids),
            "Research basis":basis_label,"Research product IDs":_joined(basis),"Gap criteria":len(gaps),"Unverified Claims":weak_count,
            "Unknown":state_counts.get("Unknown",0),"Unassessed":state_counts.get("Unassessed",0),"Announced":state_counts.get("Announced",0),"Disputed":state_counts.get("Disputed",0),
            "Partial scope gaps":partial_count,"Evidence Completeness":float(r.get("Recorded coverage",0)),"Determinate completeness":float(r.get("Determinate coverage",0)),
            "Last Reviewed":max([value(co,"Last Reviewed")]+[value(p,"Last Reviewed") for p in products]+[x["Assessment date"] for x in pairs]),
            "Next Action":("Verify "+ "; ".join(gap_names)) if gap_names else ("Establish product-specific relevance" if not pairs else "Monitor new evidence and deployments")})
    frame=pd.DataFrame(out,columns=COLUMNS)
    return frame.sort_values(["Priority","Gap criteria","Portfolio Overlap","Company","Company ID"],ascending=[True,False,False,True,True]).reset_index(drop=True),details

def watchlist_changes(before,after):
    """Compare two watchlists computed with the same thresholds, by stable company ID."""
    cols=["Company ID","Company","Change","Before priority","After priority","Before overlap","After overlap","Before gap criteria","After gap criteria"]
    a=before.set_index("Company ID").to_dict("index");b=after.set_index("Company ID").to_dict("index")
    out=[]
    tracked=["Priority","Watch Reason","Space Target","Space Confirmed","Reported space implementation","Space research / other signal","Portfolio Overlap","Best Product Overlap","Gap criteria","Unverified Claims","Unknown","Unassessed","Announced","Disputed","Partial scope gaps","Evidence Completeness","Determinate completeness"]
    for cid in sorted(set(a)|set(b)):
        x=a.get(cid,{});y=b.get(cid,{})
        change="Newly qualifies" if not x else "No longer qualifies" if not y else "; ".join(k for k in tracked if x.get(k)!=y.get(k))
        if change:out.append([cid,y.get("Company",x.get("Company","")),change,x.get("Priority",""),y.get("Priority",""),x.get("Portfolio Overlap"),y.get("Portfolio Overlap"),x.get("Gap criteria"),y.get("Gap criteria")])
    return pd.DataFrame(out,columns=cols)
