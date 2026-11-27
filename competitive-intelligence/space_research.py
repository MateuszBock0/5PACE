"""Derived full-snapshot research queue; product evidence never inherited from company."""
import re
from datetime import date
import pandas as pd
from core import value,split_ids,digest
from command_engine import registry,direct_current
from product_intelligence import CRITERIA
from analytics import EVIDENCE_RANK
from founder import CORE_IDS,eligible,summaries
from decision import SPACE,NEG,customer_position

SPACE_TYPES={"Space offering","Space manufacturing deployment","Space AIT deployment","Space manufacturing adoption signal","Space AIT R&D","Space AIT R&D heritage","Planned space application","Space industry only"}
SECONDARY=["AV-CR-"+x for x in ("006","021","026","028","029","034")]
GAPS={"Disputed":0,"Unknown":1,"Announced":2,"Unassessed":3,"Partially supported":4,"Supported":5,"Explicitly unsupported":6}
def relevance(product,company,deps,observations):
    kind=value(product,"Space Industry Applicability")
    refs=set(split_ids(product.get("Space Deployment Evidence")))
    # Explicit product-scoped evidence IDs; never promote solely from company links.
    linked=set(split_ids(product.get("Related Observation IDs")))
    urls=set()
    if kind in SPACE_TYPES:
        refs.update(linked)
        for k in ("Product URL","Documentation URL"):
            if value(product,k):urls.add(value(product,k))
    for oid in refs:
        url=value(observations.get(oid,{}),"Source URL")
        if url:urls.add(url)
    for d in deps:
        if re.search(SPACE,value(d,"Industry"),re.I) and not re.search(NEG,value(d,"Industry"),re.I) and value(d,"Source URL"):
            refs.add(value(d,"Deployment ID"));urls.add(value(d,"Source URL"))
            if kind not in SPACE_TYPES:kind="Product-specific space deployment / demonstration record"
    if kind in SPACE_TYPES and (refs or urls):return kind,sorted(refs),sorted(urls),True
    if kind=="Product-specific space deployment / demonstration record":return kind,sorted(refs),sorted(urls),True
    if customer_position(product,deps)["Customer position"] in {"Space AIT target segment","Space AIT implementation case"} and value(product,"Product URL"):
        return "Product-specific space target statement",sorted(linked),[value(product,"Product URL")],True
    if value(company,"Space Industry Presence") in {"Documented presence","Documented presence outside AIT"}:
        return "Company-only space signal — product relevance unconfirmed",split_ids(company.get("Space Industry Evidence")),[value(company,"Source URL")] if value(company,"Source URL") else [],False
    return "Product space relevance not established",[],[],False

def priority_queue(data,cfg,snapshot_id="",snapshot_date=""):
    rows=summaries(data);products=registry(data,"Products","Product ID");companies=registry(data,"Companies","Company ID");criteria=registry(data,CRITERIA,"Criterion ID")
    obs=registry(data,"Observations","Observation ID");current=direct_current(data)
    deps=data.get("Deployments",{}).get("rows",[])
    try:asof=date.fromisoformat(snapshot_date[:10])
    except (ValueError,TypeError):asof=date.today()
    out=[]
    for _,r in rows.iterrows():
        pid=r["Product ID"];p=products[pid];cid=r["Company ID"]
        kind,refs,urls,space=relevance(p,companies.get(cid,{}),[d for d in deps if value(d,"Product ID")==pid],obs)
        strategic=eligible(r["Recorded overlap fraction"],r["Customer position"]) or r.Role in {"Direct visual AIT candidate","Cross-industry competitor candidate"}
        tier="P0 — Space Priority" if space else "P1 — Strategic / technology gaps" if strategic else "P2 — Remaining research"
        existing=[c for q,c in current if q==pid and c in criteria]
        # For P2 do not assume every capability relevant to unrelated products.
        candidates=list(dict.fromkeys([c for c in CORE_IDS+SECONDARY if c in criteria]+existing)) if space or strategic else existing
        base={"Priority tier":tier,"Company ID":cid,"Company":r.Company,"Product ID":pid,"Product":r.Product,"Space relevance type":kind,"Recorded overlap":r["Recorded overlap fraction"],"Evidence coverage":r["Core evidence coverage"],"Snapshot ID":snapshot_id or digest(data),"Snapshot date":snapshot_date}
        for c in candidates:
            e=current.get((pid,c),{});s=e.get("status","Unassessed");grade=e.get("evidence","");records=e.get("rows",[])
            if s=="Not applicable":continue
            weak=EVIDENCE_RANK.get(grade,-1)<3
            dates=[]
            for a in records:
                try:dates.append(date.fromisoformat(value(a,"Assessment date")[:10]))
                except ValueError:pass
            stale=bool(dates and (asof-max(dates)).days>=int(cfg.get("research_stale_days",90)))
            partial_gap=s=="Partially supported" and any(re.search(r"\b(unclear|unknown|unconfirmed|unverified|not established|not documented|not confirmed|not demonstrated|requires verification|not specified)\b",value(a,"Limitations")+" "+value(a,"Assessment rationale"),re.I) for a in records)
            unresolved=s in {"Unknown","Disputed","Announced","Unassessed"}
            if not (unresolved or weak or stale or partial_gap):continue
            reason="; ".join(x for x in [s if unresolved else "", "Weak / missing evidence" if weak else "", "Specific partial scope unresolved" if partial_gap else "", "Review due" if stale else ""] if x)
            evidence=set(refs)
            sources=set(urls)
            for a in records:
                for k in ("Comparison ID","Related Assessment IDs","Related Observation IDs","Related Evidence IDs"):evidence.update(split_ids(a.get(k)))
                sources.update(x.strip() for x in re.split(r"[;\n]",value(a,"Source URLs")) if x.strip())
            out.append({**base,"Criterion ID":c,"Current verdict":s,"Evidence level":grade,"Evidence IDs":"; ".join(sorted(evidence)),"Source URLs":"; ".join(sorted(sources)),"Research question":"Verify "+value(criteria[c],"Product criterion")+" for "+r.Product+"; identify conditions, limits and primary evidence.","Reason":reason,"Comparison ID":value(records[0],"Comparison ID") if len(records)==1 else "","_core":0 if c in CORE_IDS else 1 if c in SECONDARY else 2,"_gap":GAPS.get(s,7)})
        if not space and not strategic and (kind.startswith("Company-only") or not existing or r.Role=="Unresolved role"):
            out.append({**base,"Criterion ID":"","Current verdict":"Product relevance unresolved","Evidence level":"","Evidence IDs":"; ".join(refs),"Source URLs":"; ".join(urls),"Research question":"Establish product-specific space relevance, AIT use case and applicable criteria; do not inherit company heritage.","Reason":kind,"Comparison ID":"","_core":3,"_gap":7})
    cols=["Priority tier","Company ID","Company","Product ID","Product","Criterion ID","Current verdict","Evidence level","Space relevance type","Evidence IDs","Source URLs","Research question","Reason","Recorded overlap","Evidence coverage","Snapshot ID","Snapshot date","Comparison ID"]
    if not out:return pd.DataFrame(columns=cols)
    d=pd.DataFrame(out).sort_values(["Priority tier","_core","_gap","Recorded overlap","Product ID","Criterion ID"],ascending=[True,True,True,False,True,True])
    return d[cols]
