"""Decision-oriented summaries of existing source evidence. No source mutation."""
import re
import pandas as pd
from core import value
from analytics import EVIDENCE_RANK
from command_engine import registry,direct_current,direct_matrix,profile,comparison_changes,ASSESS
from competitive_roles import classify,family_root
from product_intelligence import CRITERIA
from positioning import taxonomy,interval_arrays,advantage_portfolio,VISTA,workflow_benchmark

CORE_PATTERNS=[r"physical configuration",r"observed.*execution",r"automated.*documentation",r"offline",r"passive.*recording",r"mechanism deployment|dynamic behaviour",r"vendor.independent|modular software",r"enterprise system integration"]
POSITIVE={"Supported","Partially supported"}
CORE_ROLES={"Direct visual AIT candidate","Workflow / procurement substitute candidate"}
def strategic_criteria(data):
    criteria=registry(data,CRITERIA,"Criterion ID")
    selected=[]
    for pat in CORE_PATTERNS:
        for cid,r in criteria.items():
            if re.search(pat,value(r,"Product criterion").lower()) and cid not in selected:
                selected.append(cid)
                break
    return selected or list(criteria)[:8]

def related(data,tab,pid):
    return [r for r in data.get(tab,{}).get("rows",[]) if value(r,"Product ID")==pid]

def summaries(data):
    products=registry(data,"Products","Product ID")
    companies=registry(data,"Companies","Company ID")
    criteria=registry(data,CRITERIA,"Criterion ID")
    current=direct_current(data)
    strategic=strategic_criteria(data)
    out=[]
    for pid,p in products.items():
        cl=classify(p);role=cl["Analytical role"]
        cid=value(p,"Company ID")
        full=[c for c in strategic if current.get((pid,c),{}).get("status")=="Supported"]
        partial=[c for c in strategic if current.get((pid,c),{}).get("status")=="Partially supported"]
        unresolved=[c for c in strategic if current.get((pid,c),{}).get("status","Unassessed") not in {"Supported","Partially supported","Explicitly unsupported"}]
        strong=[c for c in full+partial if EVIDENCE_RANK.get(current[(pid,c)]["evidence"],-1)>=3]
        deps=related(data,"Deployments",pid)
        documented=[r for r in deps if value(r,"Deployment Status") in {"Documented implementation","Reported implementation"}]
        space=value(p,"Space Industry Applicability")
        market="Space deployment / adoption signal" if space in {"Space AIT deployment","Space manufacturing deployment","Space manufacturing adoption signal"} else "Space offering" if space=="Space offering" else "Current space-market fit unresolved"
        # Only recorded scope, never a negative inference from missing data.
        fraction=(len(full)+.5*len(partial))/max(1,len(strategic))
        x="Broad recorded overlap" if fraction>=2/3 else "Material recorded overlap" if fraction>=1/3 else "Some recorded overlap" if fraction>0 else "No positive record / unresolved"
        if role=="Direct visual AIT candidate": tier="Core visual competition";order=0
        elif role=="Workflow / procurement substitute candidate": tier="Workflow / budget substitution candidate";order=1
        elif role=="Cross-industry competitor candidate": tier="Adjacent market entrant";order=2
        elif role=="Unresolved role" and cl["Source role"] in {"Direct","Adjacent / substitute"}: tier="Classification requires review";order=3
        else: tier="Monitor selectively";order=4
        why=[]
        if full or partial:
            why.append("Recorded overlap: "+ "; ".join(value(criteria[c],"Product criterion") + (" (partial)" if c in partial else "") for c in (full+partial)[:3]))
        if documented: why.append("Implementation records: "+", ".join(dict.fromkeys(value(r,"Customer Organisation") for r in documented if value(r,"Customer Organisation"))) if any(value(r,"Customer Organisation") for r in documented) else "Implementation records available.")
        why.append(cl["Classification basis"])
        unresolved_text="; ".join(value(criteria[c],"Product criterion") for c in unresolved[:3])
        out.append({"Product ID":pid,"Company ID":cid,"Company":value(companies.get(cid,{}),"Company Name"),"Product":value(p,"Product Name"),"Family ID":family_root(products,pid),"Role":role,"Source classification":cl["Source role"],"Review track":tier,"Order":order,"Why care":" · ".join(why),"Unresolved":unresolved_text or "No unresolved strategic criterion in selected set","Buyer / procurement overlap":"Unconfirmed — shared procurement decision not recorded in structured fields","Space market evidence":market,"Functional overlap":x,"Recorded full":len(full),"Recorded partial":len(partial),"Technical or stronger":len(strong),"Implementation records":len(documented),"Recorded overlap fraction":fraction,"Commercial status":value(p,"Commercial Status") or "Unknown","Classification basis":cl["Classification basis"]})
    return pd.DataFrame(out).sort_values(["Order","Recorded overlap fraction","Technical or stronger","Implementation records","Product"],ascending=[True,False,False,False,True]) if out else pd.DataFrame()

def priority_families(rows):
    if rows.empty:return rows
    return rows.drop_duplicates("Family ID",keep="first")

def profile_records(data,pid):
    p=registry(data,"Products","Product ID").get(pid,{})
    cid=value(p,"Company ID")
    return {"Deployments":related(data,"Deployments",pid),"Commercial Intelligence":related(data,"Commercial Intelligence",pid),
            "Observations":[r for r in data.get("Observations",{}).get("rows",[]) if value(r,"Company ID")==cid],
            "Key Competitors":[r for r in data.get("Key Competitors",{}).get("rows",[]) if value(r,"Company / project")==value(registry(data,"Companies","Company ID").get(cid,{}),"Company Name")],
            "Comparison Assessment":related(data,ASSESS,pid),"Capability Assessment":related(data,"Capability Assessment",pid)}

def timeline(data):
    rows=[]
    for r in data.get("Observations",{}).get("rows",[]):
        rows.append({"Date":value(r,"Date added (ISO)"),"Date basis":"Observation recorded","Company ID":value(r,"Company ID"),"Product ID":"","Development":value(r,"Observation"),"Strategic implication":value(r,"Implication for AIT-VISTA"),"Source":value(r,"Source URL"),"Reference":value(r,"Observation ID")})
    pro=registry(data,"Products","Product ID")
    for tab,key,field,datefield,basis in [("Deployments","Deployment ID","Use Case","Deployment Date","Reported deployment date"),("Commercial Intelligence","Commercial Record ID","Business Model","Applicable Date","Commercial information applicable date"),(ASSESS,"Comparison ID","Assessment rationale","Assessment date","Assessment recorded")]:
        for r in data.get(tab,{}).get("rows",[]):
            p=value(r,"Product ID");prod=pro.get(p,{})
            rows.append({"Date":value(r,datefield),"Date basis":basis,"Company ID":value(prod,"Company ID"),"Product ID":p,"Development":value(r,field),"Strategic implication":value(r,"Limitations") or value(r,"Evidence Limitations"),"Source":value(r,"Source URL") or value(r,"Source URLs"),"Reference":value(r,key)})
    return pd.DataFrame(rows,columns=["Date","Date basis","Company ID","Product ID","Development","Strategic implication","Source","Reference"]).sort_values("Date",ascending=False)

def advantage_summary(data,cfg,pids):
    mat=direct_matrix(data,pids)
    # Strict comparative claims; all-recorded evidence remains visible in heatmap.
    lo,hi,state,_=interval_arrays(data,mat,cfg,"As-Is","Technical documentation or stronger")
    return advantage_portfolio(data,lo,hi,state,cfg,"As-Is")

def evidence_detail(data,pid,cid):
    active=direct_current(data).get((pid,cid),{})
    return active.get("status","Unassessed"),active.get("rows",[]),[r for r in related(data,ASSESS,pid) if value(r,"Criterion ID")==cid]
