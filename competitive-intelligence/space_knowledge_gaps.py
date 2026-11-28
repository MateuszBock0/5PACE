"""Space discovery backlog, independent of technology overlap and watchlist filters."""
import pandas as pd
from core import value,split_ids
from command_engine import registry,direct_current
from founder import CORE_IDS,summaries
from product_intelligence import CRITERIA
from analytics import EVIDENCE_RANK
from company_watchlist import _space_flags,_space_statement,_gap_row,_joined,DETAIL

SPACE_GAP_COLUMNS=["Company ID","Company","Space basis","Space evidence IDs","Space sources","Product count","Space product count","Space product IDs","Best Product ID","Best recorded overlap","Gap criteria","Unassessed pairs","Unresolved pairs","Weak evidence pairs","Recorded pairs","Technical determinate coverage","Research priority","Reason","Next Action"]

def space_knowledge_gaps(data,min_gaps=3):
    """Include space-linked firms with no mapped product or >= min_gaps distinct unresolved core criteria.
    A gap is assessed on a specific space-linked product, never inherited from its company.
    No product mapping means unknown completeness, not eight fabricated missing assessments.
    """
    if not 1<=min_gaps<=8:raise ValueError("Invalid gap threshold")
    companies=registry(data,"Companies","Company ID")
    products=registry(data,"Products","Product ID")
    criteria=registry(data,CRITERIA,"Criterion ID")
    obs=registry(data,"Observations","Observation ID")
    ledger=direct_current(data)
    deps=data.get("Deployments",{}).get("rows",[])
    rows=summaries(data)
    positions=dict(zip(rows["Product ID"],rows["Customer position"])) if not rows.empty else {}
    scores=dict(zip(rows["Product ID"],rows["Recorded overlap fraction"])) if not rows.empty else {}
    out=[];details={}
    for cid,co in companies.items():
        ps=[p for p in products.values() if value(p,"Company ID")==cid]
        target,confirmed,reported,other,refs,urls,scoped=_space_flags(data,co,ps,deps,obs,positions)
        # Explicit product target industry is a marketing signal, not a deployment.
        for p in ps:
            pid=value(p,"Product ID");url=value(p,"Product URL") or value(p,"Documentation URL")
            if url and _space_statement(value(p,"Target Industries")):
                scoped.add(pid);target.append(pid+" — target industry statement");urls.append(url)
                refs+=split_ids(p.get("Related Observation IDs"))
        if not (target or confirmed or reported or other):continue
        pairs=[];weak_n=unresolved_n=unassessed_n=recorded_n=strong_n=0
        for pid in sorted(scoped):
            for c in CORE_IDS:
                e=ledger.get((pid,c),{})
                g,_,partial=_gap_row(pid,products[pid],c,e,criteria.get(c,{}))
                state=g["Verdict"];rank=EVIDENCE_RANK.get(g["Evidence level"],-1)
                determinate=state in {"Supported","Partially supported","Explicitly unsupported","Not applicable"}
                weak=bool(e) and determinate and rank<3
                if weak and not g["Gap reason"]:g["Gap reason"]="Determinate verdict below technical documentation"
                if state=="Not applicable" and rank>=3:g["Gap reason"]=""
                if not determinate and not g["Gap reason"]:g["Gap reason"]="Unresolved verdict"
                unassessed_n+=state=="Unassessed"
                unresolved_n+=not determinate and state!="Unassessed"
                weak_n+=weak;recorded_n+=bool(e)
                strong_n+=determinate and rank>=3 and not partial
                pairs.append(g)
        gaps={x["Criterion ID"] for x in pairs if x["Gap reason"]}
        if scoped and len(gaps)<min_gaps:continue
        labels=[label for label,vals in [("Documented space activity",confirmed),("Reported space implementation",reported),("Space target",target),("Space research / other signal",other)] if vals]
        if not ps:
            reason="No registered products";action="Identify current products and solutions; establish product-specific space/AIT relevance.";priority="P0 — Product discovery"
        elif not scoped:
            reason="Company-level space link only; no product-specific space evidence";action="Verify which registered products actually target or serve space; then assess applicable AIT criteria.";priority="P0 — Product discovery"
        else:
            reason="Insufficient product-level technical evidence"
            names=[value(criteria.get(c,{}),"Product criterion") or c for c in CORE_IDS if c in gaps]
            action="Verify "+ "; ".join(names)
            priority="P1 — Technical research" if confirmed or reported else "P2 — Target / research validation"
        pids=[value(p,"Product ID") for p in ps]
        # Best product is only a navigation convenience; overlap never qualifies/excludes.
        best_ids=sorted(scoped or set(pids),key=lambda p:(-scores.get(p,0),p))
        out.append({"Company ID":cid,"Company":value(co,"Company Name") or cid,"Space basis":"; ".join(labels),
            "Space evidence IDs":_joined(refs),"Space sources":_joined(urls),"Product count":len(ps),"Space product count":len(scoped),"Space product IDs":_joined(scoped),
            "Best Product ID":best_ids[0] if best_ids else "","Best recorded overlap":max([scores.get(p,0) for p in pids] or [0]),
            "Gap criteria":len(gaps) if scoped else None,"Unassessed pairs":unassessed_n,"Unresolved pairs":unresolved_n,"Weak evidence pairs":weak_n,
            "Recorded pairs":recorded_n,"Technical determinate coverage":strong_n/len(pairs) if pairs else None,
            "Research priority":priority,"Reason":reason,"Next Action":action})
        details[cid]=pd.DataFrame(pairs,columns=DETAIL)
    frame=pd.DataFrame(out,columns=SPACE_GAP_COLUMNS)
    return frame.sort_values(["Research priority","Gap criteria","Technical determinate coverage","Company","Company ID"],ascending=[True,False,True,True,True],na_position="last").reset_index(drop=True),details
