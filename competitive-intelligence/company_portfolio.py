"""Read-only company-level union of eight fixed active comparison criteria."""
from itertools import combinations
import re
import pandas as pd
from core import value,split_ids
from command_engine import registry,direct_current
from founder import CORE_IDS,eligible,summaries,SPACE_CUSTOMER
from product_intelligence import CRITERIA

NOTE="Portfolio coverage aggregates the best evidence across products. It does not prove that the company offers one integrated end-to-end system."
CREDIT={"Supported":1.0,"Partially supported":.5}
DETERMINATE={"Supported","Partially supported","Explicitly unsupported"}
ALL_COMPANIES="All companies"
CORE_COMPANIES="Companies with products in strategic core"
PORTFOLIO_EXPOSURE="Companies with product or portfolio exposure"
CUSTOM="Custom selection"
SCOPES=[ALL_COMPANIES,CORE_COMPANIES,PORTFOLIO_EXPOSURE,CUSTOM]
NEG=r"\b(no|not|never|without|unknown|uncertain|unconfirmed|unverified|unproven|unestablished|lack|lacks|cannot|could not)\b"
REL=r"\b(integrat(?:es? with|ed with|ion with|ion between|ion of)|interoperab\w*|compatible with|works with|work together|connects? to|connected to)\b"
POTENTIAL=r"\b(planned|proposed|future|intended|can|could|may|potential|compatible|interoperab\w*)\b"

def _names(p):
    return {n.strip().casefold() for n in [value(p,"Product Name"),value(p,"Product ID")]+split_ids(p.get("Alternative Names")) if len(n.strip())>=5}

def integration_evidence(data,cid,pids,products,ledger):
    """Source-backed named-pair signals only. Never infer integration from union."""
    if len(pids)<2:return "Single product — cross-module integration not assessed",[]
    aliases={p:_names(products[p]) for p in pids}
    ambiguous={n for n in set().union(*aliases.values()) if sum(n in a for a in aliases.values())>1}
    aliases={p:ns-ambiguous for p,ns in aliases.items()}
    def matches(clause,p):
        return [m.span() for n in aliases[p] for m in re.finditer(r"(?<!\w)"+re.escape(n)+r"(?!\w)",clause)]
    records=[]
    def scan(register,rid,source,statement,quality,limitations=""):
        if not source or not rid:return
        for raw in re.split(r"[;\n]|(?<=[.!?])\s+",statement):
            clause=raw.casefold()
            if not re.search(REL,clause) or re.search(NEG,clause):continue
            for a,b in combinations(pids,2):
                # Require the relation itself between names, not mere co-mention.
                def linked(x,y):
                    if x[1]>y[0]:return False
                    between=clause[x[1]:y[0]].strip()
                    return bool(re.fullmatch(r"(?:(?:is|are|was|were|can|may|could|be|has been|will be|designed to)\s+)*"+REL,between))
                if not any(linked(x,y) or linked(y,x) for x in matches(clause,a) for y in matches(clause,b)):continue
                documented=quality=="Documented" and not re.search(POTENTIAL,clause) and not re.search(NEG,limitations.casefold())
                records.append({"Register":register,"Reference":rid,"Product IDs":[a,b],"Status":"Documented integration" if documented else "Potential integration","Statement":raw.strip(),"Source":source,"Limitations":limitations})
    for pid in pids:
        p=products[pid]
        scan("Products",pid,value(p,"Documentation URL") or value(p,"Product URL"),value(p,"Product Description")+"\n"+value(p,"Notes"),"Claim")
    for r in data.get("Observations",{}).get("rows",[]):
        if value(r,"Company ID")!=cid:continue
        quality="Documented" if value(r,"Evidence status") in {"Official documentation","Independent corroboration"} else "Claim"
        scan("Observations",value(r,"Observation ID"),value(r,"Source URL"),value(r,"Observation")+"\n"+value(r,"Supporting evidence"),quality)
    for r in data.get("Deployments",{}).get("rows",[]):
        if value(r,"Product ID") not in pids:continue
        quality="Documented" if value(r,"Deployment Status")=="Documented implementation" and value(r,"Evidence Type") in {"Official documentation","Independent corroboration"} else "Claim"
        scan("Deployments",value(r,"Deployment ID"),value(r,"Source URL"),value(r,"Use Case")+"\n"+value(r,"Reported Results"),quality,value(r,"Evidence Limitations"))
    company_name=value(registry(data,"Companies","Company ID").get(cid,{}),"Company Name").casefold()
    for r in data.get("Key Competitors",{}).get("rows",[]):
        if not company_name or value(r,"Company / project").casefold()!=company_name:continue
        quality="Documented" if value(r,"Source type") in {"Official documentation","Official documentation — full review","Official deployment documentation","Official integration catalogue","Independent corroboration"} else "Claim"
        scan("Key Competitors",value(r,"Evidence ID"),value(r,"Source URL"),value(r,"Evidence / finding"),quality,value(r,"Evidence limitations"))
    for (pid,c),e in ledger.items():
        if pid not in pids or e["status"] not in CREDIT:continue
        for r in e["rows"]:
            quality="Documented" if value(r,"Evidence level") in {"Independently verified","Independently documented","Official technical documentation"} else "Claim"
            scan("Comparison Assessment",value(r,"Comparison ID"),value(r,"Source URLs"),value(r,"Assessment rationale"),quality,value(r,"Limitations"))
    unique={(r["Register"],r["Reference"],tuple(r["Product IDs"]),r["Statement"]):r for r in records}
    records=list(unique.values())
    status="Documented integration (specific pairs only)" if any(r["Status"]=="Documented integration" for r in records) else "Potential integration (source claim)" if records else "Compatibility unconfirmed"
    return status,records

def portfolio_data(data,rows=None):
    rows=summaries(data) if rows is None else rows
    products=registry(data,"Products","Product ID");companies=registry(data,"Companies","Company ID");criteria=registry(data,CRITERIA,"Criterion ID")
    ledger=direct_current(data);out=[];details={}
    if rows.empty:return pd.DataFrame(columns=["Company ID","Company","Portfolio coverage","Best single product coverage","Additional portfolio coverage","Portfolio flag","Integration status","Product count"]),details
    for cid,g in rows.groupby("Company ID",sort=False):
        g=g.sort_values(["Recorded overlap fraction","Product","Product ID"],ascending=[False,True,True])
        pids=g["Product ID"].tolist();name=value(companies.get(cid,{}),"Company Name") or cid
        product_rows=[];criterion_rows=[];records=[];credit=[];commercial_credit=[];recorded=determinate=pair_recorded=pair_determinate=0
        for _,r in g.iterrows():
            product_rows.append({"Product ID":r["Product ID"],"Product":r.Product,"Commercial status":r["Commercial status"],"Recorded overlap":r["Recorded overlap fraction"],"Evidence coverage":r["Core evidence coverage"],"Determinate coverage":r["Core determinate coverage"],"Strategic core":eligible(r["Recorded overlap fraction"],r["Customer position"]),"Customer position":r["Customer position"]})
        for c in CORE_IDS:
            states=[];scores=[]
            for pid in pids:
                e=ledger.get((pid,c),{});s=e.get("status","Unassessed")
                states.append(s);scores.append(CREDIT.get(s,0))
                pair_recorded+=bool(e);pair_determinate+=s in DETERMINATE
                for r in e.get("rows",[]) or [{}]:
                    records.append({"Criterion ID":c,"Product ID":pid,"Product":value(products[pid],"Product Name"),"Commercial status":value(products[pid],"Commercial Status") or "Unknown","Pair verdict":s,"Record verdict":value(r,"Verdict") or s,"Comparison ID":value(r,"Comparison ID"),"Evidence level":value(r,"Evidence level"),"Assessment date":value(r,"Assessment date"),"Source URLs":value(r,"Source URLs"),"Rationale":value(r,"Assessment rationale"),"Limitations":value(r,"Limitations")})
            best=max(scores);credit.append(best)
            commercial_credit.append(max([sc for pid,sc in zip(pids,scores) if value(products[pid],"Commercial Status")=="Commercial"] or [0]))
            recorded+=any((pid,c) in ledger for pid in pids);determinate+=any(s in DETERMINATE for s in states)
            winners=[pid for pid,sc in zip(pids,scores) if sc==best and best>0]
            verdict="Supported" if best==1 else "Partially supported" if best==.5 else states[0] if len(set(states))==1 else "Mixed zero-credit states"
            criterion_rows.append({"Criterion ID":c,"Criterion":value(criteria.get(c,{}),"Product criterion") or c,"Portfolio verdict":verdict,"Credit":best,"Contributing product IDs":"; ".join(winners),"Contributing products":"; ".join(value(products[p],"Product Name")+" ["+(value(products[p],"Commercial Status") or "Unknown")+"]" for p in winners) or "None","Product states":"; ".join(value(products[p],"Product Name")+": "+s for p,s in zip(pids,states))})
        best=float(g.iloc[0]["Recorded overlap fraction"]);union=sum(credit)/8;additional=union-best
        if additional< -1e-9:raise ValueError("Portfolio union below single-product score")
        additional=max(0.,additional);ties=g[g["Recorded overlap fraction"]==best]
        core=any(r["Strategic core"] for r in product_rows)
        space_products=[r for r in product_rows if r["Customer position"] in SPACE_CUSTOMER]
        portfolio_eligible=eligible(union,"Space AIT target segment" if space_products else "Unresolved target overlap")
        flag="Product-level core" if core else "Portfolio-only exposure" if portfolio_eligible and additional>0 else "Below threshold"
        integration,links=integration_evidence(data,cid,pids,products,ledger)
        out.append({"Company ID":cid,"Company":name,"Portfolio coverage":union,"Best single product coverage":best,"Additional portfolio coverage":additional,"Best product":ties.iloc[0].Product,"Best product IDs":"; ".join(ties["Product ID"]),"Best product ties":"; ".join(ties.Product),"Product count":len(pids),"Recorded coverage":recorded/8,"Determinate coverage":determinate/8,"Pair recorded coverage":pair_recorded/(8*len(pids)),"Pair determinate coverage":pair_determinate/(8*len(pids)),"Commercial-only coverage":sum(commercial_credit)/8,"Portfolio flag":flag,"Product-level core":core,"Space threshold basis":"; ".join(r["Product ID"] for r in space_products) or "None","Portfolio review threshold":.4 if space_products else .6,"Integration status":integration})
        details[cid]={"products":pd.DataFrame(product_rows),"criteria":pd.DataFrame(criterion_rows),"records":pd.DataFrame(records),"integration":links}
    return pd.DataFrame(out).sort_values(["Portfolio coverage","Company","Company ID"],ascending=[False,True,True]).reset_index(drop=True),details

def filter_companies(frame,scope=ALL_COMPANIES,ids=None):
    if frame.empty:return frame.copy()
    if scope==CORE_COMPANIES:return frame[frame["Product-level core"]].copy()
    if scope==PORTFOLIO_EXPOSURE:return frame[frame["Portfolio flag"]!="Below threshold"].copy()
    if scope==CUSTOM:return frame[frame["Company ID"].isin(ids or [])].copy()
    return frame.copy()

def selected_company(event,allowed):
    pts=event.get("selection",{}).get("points",[])
    d=pts[0].get("customdata",[]) if pts else []
    return d[0] if d and d[0] in allowed else None
