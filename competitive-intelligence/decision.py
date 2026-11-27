"""Founder decision views: recorded evidence, never inferred procurement or demand."""
import re
import pandas as pd
from core import value,split_ids
from command_engine import registry,direct_current,ASSESS
from product_intelligence import CRITERIA
from analytics import EVIDENCE_RANK

CUSTOMER_LANES=["Unresolved target overlap","Adjacent sector signal","Space AIT target segment","Space AIT implementation case"]
FUNCTION_LANES=["No positive record / unresolved","Some recorded overlap","Material recorded overlap","Broad recorded overlap"]
SPACE=r"\b(spacecraft|satellite[s]?|space[- ]equipment|space hardware|space manufacturing)\b"
TEAM=r"\b(manufactur\w*|integrat\w*|assembly|ait|quality|qa|production|component[s]?)\b"
NEG=r"\b(no|not|unverified|unconfirmed|unknown|unestablished|unproven|without)\b"

def customer_position(product,deps):
    """Independent segment evidence, not a calibrated buyer/budget score.
    A deployment must be an implementation and contain positive space-AIT context.
    Marketing is not adoption. No source claims a shared buying decision by default.
    """
    matched=[]
    for d in deps:
        if value(d,"Deployment Status") not in {"Documented implementation","Reported implementation"}:continue
        industry=value(d,"Industry").lower();use=value(d,"Use Case").lower()
        if re.search(SPACE,industry) and re.search(r"\b(ait|assembly|procedur\w*|test\w*|inspect\w*|report\w*|manufactur\w*)\b",use) and not re.search(NEG,industry+" "+use):
            matched.append(d)
    target=value(product,"Target Customers")
    # Assess clauses independently: positive marketed scope followed by an
    # explicit limitation on named customers is not a negative target claim.
    clauses=[c.strip().lower() for c in re.split(r"[;.\n]",target) if c.strip()]
    matching=[c for c in clauses if re.search(SPACE,c) and re.search(TEAM,c) and not re.search(NEG,c)]
    adjacent=any(re.search(r"\b(aerospace|defen[cs]e|precision manufacturing|industrial manufacturing)\b",c) and not re.search(NEG,c) for c in clauses)
    if matched:
        lane=CUSTOMER_LANES[3]
        basis="Recorded implementation in the target sector/workflow: "+", ".join(dict.fromkeys(value(d,"Customer Organisation") or "Unnamed customer" for d in matched))
        refs=[value(d,"Deployment ID") for d in matched]
    elif matching:
        lane=CUSTOMER_LANES[2];basis="Recorded target-customer statement: "+target;refs=split_ids(product.get("Related Observation IDs"))
    elif adjacent:
        lane=CUSTOMER_LANES[1];basis="Recorded adjacent-sector target statement: "+target;refs=split_ids(product.get("Related Observation IDs"))
    else:
        lane=CUSTOMER_LANES[0];basis="No sufficiently specific positive target-customer or implementation record.";refs=[]
    return {"Customer position":lane,"Customer basis":basis,"Customer evidence IDs":"; ".join(refs),"Procurement":"Unresolved — no verified shared buyer, tender or budget."}

def decision_for(role):
    return {
      "Direct visual AIT candidate":"Benchmark visual verification, execution and local deployment; test buyer overlap.",
      "Workflow / procurement substitute candidate":"Test whether buyers would purchase a MES instead of, or alongside, AIT-VISTA.",
      "Cross-industry competitor candidate":"Monitor adaptation to spacecraft AIT and the cost of entry.",
      "Enabling technology":"Assess integration or build-vs-buy rather than assuming substitution.",
      "Complementary system":"Explore interoperability; verify whether any workflow is replaced."
    }.get(role,"Resolve the commercial offer and actual AIT use case before ranking.")

def differentiation_questions(data,criteria_ids,pids):
    current=direct_current(data);criteria=registry(data,CRITERIA,"Criterion ID")
    out=[]
    for c in criteria_ids:
        if c not in criteria:continue
        full=[];partial=[];negative=[];unresolved=[]
        for p in pids:
            e=current.get((p,c),{});s=e.get("status","Unassessed");strong=EVIDENCE_RANK.get(e.get("evidence",""),-1)>=3
            if s=="Supported":full.append(p)
            elif s=="Partially supported":partial.append(p)
            elif s=="Explicitly unsupported" and strong:negative.append(p)
            else:unresolved.append(p)
        if full: label="Recorded competitor support — benchmark depth"
        elif partial:label="Potential scope differentiation — confirm limitations"
        elif unresolved:label="Unresolved — investigate, not a proven advantage"
        elif negative:label="Recorded non-support in selected cohort — verify customer value"
        else:label="No comparable cohort"
        out.append({"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"Finding":label,
            "Full support":len(full),"Partial support":len(partial),"Unresolved":len(unresolved),
            "Evidence needed":"Verify full criterion, operating conditions and source; validate customer importance and comparable operational performance.",
            "Product IDs":"; ".join(unresolved+partial+full+negative)})
    return pd.DataFrame(out)

def company_brief(data,cid):
    products=[r for r in data.get("Products",{}).get("rows",[]) if value(r,"Company ID")==cid]
    ids={value(p,"Product ID") for p in products}
    deps=[r for r in data.get("Deployments",{}).get("rows",[]) if value(r,"Product ID") in ids]
    commercial=[r for r in data.get("Commercial Intelligence",{}).get("rows",[]) if value(r,"Product ID") in ids]
    return {"Products":products,"Deployments":deps,"Commercial Intelligence":commercial}

def observation_product(data,r):
    cid=value(r,"Company ID");oid=value(r,"Observation ID")
    p=[x for x in data.get("Products",{}).get("rows",[]) if value(x,"Company ID")==cid]
    name=value(r,"Product / solution").casefold()
    exact=[value(x,"Product ID") for x in p if name and name in {value(x,"Product Name").casefold(),*[a.casefold() for a in split_ids(x.get("Alternative Names"))]}]
    linked=[value(x,"Product ID") for x in p if oid and oid in split_ids(x.get("Related Observation IDs"))]
    hits=exact or linked
    return hits[0] if len(hits)==1 else ""

def signals(data):
    """Prioritise source-grounded market records and explicit strategic observations.
    Date types are not silently interchanged; observations are discovery, not events.
    """
    products=registry(data,"Products","Product ID");out=[]
    for tab,key,date,kind,description in [
        ("Deployments","Deployment ID","Deployment Date","Reported deployment / demonstration","Use Case"),
        ("Commercial Intelligence","Commercial Record ID","Applicable Date","Commercial information applicable","Business Model")]:
        for r in data.get(tab,{}).get("rows",[]):
            pid=value(r,"Product ID");p=products.get(pid,{})
            text=" · ".join(x for x in [value(r,"Customer Organisation"),value(r,description),value(r,"Deployment Status"),value(r,"Pricing Model")] if x)
            out.append({"Date":value(r,date),"Date basis":kind,"Discovery / review date":value(r,"Last Reviewed"),
            "Company ID":value(p,"Company ID"),"Product ID":pid,"Development":text,
            "Strategic implication":"Review adoption and implementation fit." if tab=="Deployments" else "Review pricing, procurement and implementation trade-offs.",
            "Limitations":value(r,"Evidence Limitations"),"Source":value(r,"Source URL"),"Reference":value(r,key),"Register":tab})
    for r in data.get("Observations",{}).get("rows",[]):
        if not value(r,"Implication for AIT-VISTA"):continue
        out.append({"Date":value(r,"Date added (ISO)"),"Date basis":"Research observation recorded",
        "Discovery / review date":value(r,"Source checked (ISO)"),"Company ID":value(r,"Company ID"),"Product ID":observation_product(data,r),
        "Development":value(r,"Observation"),"Strategic implication":value(r,"Implication for AIT-VISTA"),
        "Limitations":value(r,"Evidence status"),"Source":value(r,"Source URL"),"Reference":value(r,"Observation ID"),"Register":"Observations"})
    cols=["Date","Date basis","Discovery / review date","Company ID","Product ID","Development","Strategic implication","Limitations","Source","Reference","Register"]
    return pd.DataFrame(out,columns=cols).sort_values("Date",ascending=False)

def dataset_label(data,source,current,head,demo=False):
    if demo:return "SYNTHETIC DEMO"
    if data is None:return "NO LOCAL DATA"
    if str(source).lower().startswith("synthetic"):return "SYNTHETIC UX PREVIEW"
    if current!=head:return "HISTORICAL LOCAL SNAPSHOT"
    if source=="Google Sheets":return "LOCAL GOOGLE SHEETS SNAPSHOT"
    return "LOCAL IMPORTED SNAPSHOT"

def importance_lane(cfg,criterion):
    # Existing team estimates are not authority. Explicit, provenance-bearing
    # importance evidence is required before placing a point on this axis.
    r=cfg.get("command_profiles",{}).get(criterion,{})
    v=r.get("customer_importance","Unknown")
    return v if v in {"Low","Medium","High"} and str(r.get("customer_importance_reference","")).strip() else "Unresolved"
