"""Decision-oriented summaries of existing source evidence. No source mutation."""
import re
import pandas as pd
from core import value, split_ids
from decision import customer_position,decision_for
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
        position=customer_position(p,deps)
        why=[]
        if full or partial:
            why.append("Recorded overlap: "+ "; ".join(value(criteria[c],"Product criterion") + (" (partial)" if c in partial else "") for c in (full+partial)[:3]))
        if documented: why.append("Implementation records: "+", ".join(dict.fromkeys(value(r,"Customer Organisation") for r in documented if value(r,"Customer Organisation"))) if any(value(r,"Customer Organisation") for r in documented) else "Implementation records available.")
        why.append(cl["Classification basis"])
        unresolved_text="; ".join(value(criteria[c],"Product criterion") for c in unresolved[:3])
        out.append({"Product ID":pid,"Company ID":cid,"Company":value(companies.get(cid,{}),"Company Name"),"Product":value(p,"Product Name"),"Family ID":family_root(products,pid),"Role":role,"Source classification":cl["Source role"],"Review track":tier,"Order":order,"Why care":" · ".join(why),"Unresolved":unresolved_text or "No unresolved strategic criterion in selected set","Buyer / procurement overlap":"Unconfirmed — shared procurement decision not recorded in structured fields",**position,"Decision":decision_for(role),"Space market evidence":market,"Functional overlap":x,"Recorded full":len(full),"Recorded partial":len(partial),"Technical or stronger":len(strong),"Implementation records":len(documented),"Recorded overlap fraction":fraction,"Commercial status":value(p,"Commercial Status") or "Unknown","Classification basis":cl["Classification basis"]})
    return pd.DataFrame(out).sort_values(["Order","Recorded overlap fraction","Technical or stronger","Implementation records","Product"],ascending=[True,False,False,False,True]) if out else pd.DataFrame()

def priority_families(rows):
    if rows.empty:return rows
    return rows.drop_duplicates("Family ID",keep="first")

def profile_records(data,pid):
    p=registry(data,"Products","Product ID").get(pid,{})
    cid=value(p,"Company ID")
    direct=related(data,ASSESS,pid);market=related(data,"Capability Assessment",pid)
    deployments=related(data,"Deployments",pid);commercial=related(data,"Commercial Intelligence",pid)
    referenced=[p]+direct+market+deployments+commercial
    obsids={i for r in referenced for i in split_ids(r.get("Related Observation IDs"))}
    evids={i for r in referenced for i in split_ids(r.get("Related Evidence IDs"))}
    observations=[r for r in data.get("Observations",{}).get("rows",[]) if value(r,"Company ID")==cid or value(r,"Observation ID") in obsids]
    company=registry(data,"Companies","Company ID").get(cid,{})
    aliases={value(company,"Company Name").casefold()}|{a.casefold() for a in split_ids(company.get("Alternative Names"))}
    evidence=[r for r in data.get("Key Competitors",{}).get("rows",[]) if value(r,"Evidence ID") in evids or (value(r,"Company / project") and value(r,"Company / project").casefold() in aliases)]
    return {"Deployments":deployments,"Commercial Intelligence":commercial,"Observations":observations,
            "Key Competitors":evidence,"Comparison Assessment":direct,"Capability Assessment":market}

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

def profile_findings(data,cfg,pid):
    current=direct_current(data);criteria=registry(data,CRITERIA,"Criterion ID")
    result={"Recorded competitor strengths":[],"Documented relative functional differences":[],"Potential differences — weaker evidence":[],"Priority questions":[]}
    for c in strategic_criteria(data):
        e=current.get((pid,c),{})
        s=e.get("status","Unassessed");ours=profile(cfg,c,"As-Is")
        name=value(criteria[c],"Product criterion")
        basis=e.get("evidence","")
        if s in POSITIVE:result["Recorded competitor strengths"].append(name+" — "+s+" ("+basis+")")
        if s in {"Partially supported","Explicitly unsupported"} and ours=="Supported":
            key="Documented relative functional differences" if EVIDENCE_RANK.get(basis,-1)>=3 else "Potential differences — weaker evidence"
            result[key].append(name+" — "+s+" ("+basis+")")
        elif s not in {"Supported","Partially supported","Explicitly unsupported","Not applicable"}:
            result["Priority questions"].append("Verify "+name)
    return result

def recorded_market_changes(before,after):
    """Recorded register changes, not inferred real-world event chronology."""
    products=registry(after,"Products","Product ID")
    rows=[]
    for tab,key,fields in [("Products","Product ID",["Commercial Status","Competition Type","Space Industry Applicability","Target Customers","Deployment Architecture"]),("Deployments","Deployment ID",None),("Commercial Intelligence","Commercial Record ID",None)]:
        old=registry(before,tab,key);new=registry(after,tab,key)
        for ident,r in new.items():
            if ident not in old: changed=["New recorded entry"]
            else:
                keys=fields or [k for k in r if k not in {"Integrity Check","Last Reviewed"}]
                changed=[k for k in keys if value(r,k)!=value(old[ident],k)]
            if changed:
                pid=value(r,"Product ID")
                rows.append({"Product ID":pid,"Product":value(products.get(pid,{}),"Product Name"),"Register":tab,"Record":ident,"Recorded change":"; ".join(changed),"Interpretation":"New or revised source knowledge; actual product change not established"})
    return pd.DataFrame(rows,columns=["Product ID","Product","Register","Record","Recorded change","Interpretation"])

# These are criterion references from the UX specification, not competitor data.
BRIEF_CRITERIA=["AV-CR-003","AV-CR-004","AV-CR-002","AV-CR-005","AV-CR-006","AV-CR-008","AV-CR-020","AV-CR-021","AV-CR-022","AV-CR-026","AV-CR-029","AV-CR-034"]
WORKFLOW_EXAMPLES=[("Procedure planning","AV-CR-009"),("Physical assembly","AV-CR-003"),("Execution control","AV-CR-004"),("Testing / measurements","AV-CR-015"),("Evidence / reporting","AV-CR-002")]
def brief_criteria(data):
    c=registry(data,CRITERIA,"Criterion ID")
    ids=[i for i in BRIEF_CRITERIA if i in c]
    return ids or strategic_criteria(data)

def search_companies(data,q):
    companies=registry(data,"Companies","Company ID")
    products=registry(data,"Products","Product ID")
    q=q.strip().casefold()
    return [c for c in sorted(companies,key=lambda c:value(companies[c],"Company Name").casefold())
        if not q or q in " ".join(value(companies[c],f) for f in ("Company Name","Alternative Names","Canonical Domain")).casefold()
        or any(q in " ".join(value(p,f) for f in ("Product Name","Alternative Names","Product Category","Primary Use Case","Product Description")).casefold()
               for p in products.values() if value(p,"Company ID")==c)]

def short_reason(r):
    # Keep the full source-linked rationale in the profile.
    return str(r["Why care"]).split(" · ")[0] if r["Why care"] else "Competitive relationship not established."

def relationship_lane(r):
    return {"Direct visual AIT candidate":"Visual AIT candidates",
            "Workflow / procurement substitute candidate":"Workflow / budget candidates",
            "Cross-industry competitor candidate":"Cross-industry technology",
            "Enabling technology":"Complementary / enabling",
            "Complementary system":"Complementary / enabling"}.get(r["Role"],"Unresolved / other")

def commercial_summary(records):
    rows=records.get("Commercial Intelligence",[])
    out=[]
    for r in rows:
        prices=[]
        for f in ("Subscription Cost","One-time Licence Cost","Deployment Cost","Integration Cost"):
            if value(r,f): prices.append(f+": "+value(r,f)+" "+value(r,"Currency"))
        text=" · ".join(x for x in [value(r,"Business Model"),value(r,"Pricing Model"),*prices,value(r,"Price Basis"),value(r,"Applicable Date")] if x)
        if text:out.append(text)
    return out or ["Commercial model / pricing not recorded."]

DEFAULT_MAP_SCOPE="Strategically relevant (axis union)"
MAP_SCOPES=[DEFAULT_MAP_SCOPE,"Strategic + research","Commercial shortlist","Research & emerging","All products"]

def axis_eligible(rows):
    return rows["Customer position"].isin(["Space AIT target segment","Space AIT implementation case"]) | rows["Functional overlap"].isin(["Material recorded overlap","Broad recorded overlap"])

def strategic_map_cohort(rows,scope=DEFAULT_MAP_SCOPE,limit=10):
    """Default union evaluated for every actual product, without role/family/rank filters."""
    if rows.empty:return rows.copy()
    if scope=="All products":return rows.copy()
    if scope==DEFAULT_MAP_SCOPE:return rows[axis_eligible(rows)].copy()
    f=priority_families(rows)
    research=f[f.Role=="Research / emerging entrant"]
    if scope=="Research & emerging":return research.copy()
    commercial=f[f.Order<3].head(limit)
    if scope=="Commercial shortlist":return commercial.copy()
    return pd.concat([commercial,research],ignore_index=True).drop_duplicates("Family ID")

def map_exclusions(rows,shown,scope=None):
    if rows.empty:return pd.DataFrame()
    selected=set(shown["Product ID"]) if not shown.empty else set()
    d=rows[~rows["Product ID"].isin(selected)].copy()
    if d.empty:return d
    families=set(shown["Family ID"]) if not shown.empty else set()
    if scope==DEFAULT_MAP_SCOPE:
        d["Reason not shown"]="Neither target/case customer evidence nor material/broad recorded overlap"
    else:
        d["Reason not shown"]=d.apply(lambda r:"Another family member is shown (selected shortlist only)" if r["Family ID"] in families else "Outside selected map scope or shortlist limit",axis=1)
    return d
