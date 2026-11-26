"""Direct evidence and local strategic scenarios. No source writes or inferred verdicts."""
from collections import defaultdict
from datetime import date
import pandas as pd
from core import value, split_ids
from analytics import KNOWN, EVIDENCE_RANK, score_bounds
from strategic import commercial_mcda
from competitive_roles import classify, family_root, family_watchlist, attention
from product_intelligence import source_rows, CRITERIA

ASSESS="Comparison Assessment"
VIEW="Competitive Comparison"
FIELDS=["Comparison ID","Product ID","Criterion ID","Verdict","Evidence level","Assessment rationale","Source URLs","Related Assessment IDs","Related Observation IDs","Related Evidence IDs","Assessment date","Supersedes Comparison ID","Limitations","Pair key","Integrity Check"]
VERDICTS=set(KNOWN)|{"Unknown","Announced","Not applicable","Disputed"}
ROLE_ORDER={"Direct":0,"Adjacent / substitute":1,"Potential entrant":2,"Indirect":3}
BASE_STATES=["Unknown","Supported","Partially supported","Explicitly unsupported"]
MATURITY=["Unknown","Planned","Implemented","Demonstrated","Verified"]
SCOPE=["Unknown","Included","Excluded"]

def registry(data,tab,key):
    return {value(r,key):r for r in source_rows(data,tab) if value(r,key)}

def validate_comparisons(data,previous=None):
    errors=[]
    if previous and ASSESS in previous and ASSESS not in data:
        errors.append("Comparison Assessment: previously synchronised worksheet disappeared")
    if ASSESS not in data:
        return errors
    if not set(FIELDS).issubset(data[ASSESS]["headers"]):
        return errors+["Comparison Assessment: missing required columns"]
    rows=source_rows(data,ASSESS)
    ids=registry(data,ASSESS,"Comparison ID")
    if len(ids)!=len(rows):
        errors.append("Comparison Assessment: blank or duplicate Comparison ID")
    p=registry(data,"Products","Product ID")
    c=registry(data,CRITERIA,"Criterion ID")
    refs={f:registry(data,t,k) for f,t,k in [
        ("Related Assessment IDs","Capability Assessment","Assessment ID"),
        ("Related Observation IDs","Observations","Observation ID"),
        ("Related Evidence IDs","Key Competitors","Evidence ID")]}
    for key,r in ids.items():
        pid,cid=value(r,"Product ID"),value(r,"Criterion ID")
        status=value(r,"Verdict")
        if pid not in p or cid not in c:
            errors.append(f"{key}: unknown comparison product or criterion")
        if status not in VERDICTS or value(r,"Evidence level") not in EVIDENCE_RANK:
            errors.append(f"{key}: invalid comparison status/evidence")
        if not value(r,"Assessment rationale") or (status in set(KNOWN)|{"Announced","Not applicable"} and not value(r,"Source URLs")):
            errors.append(f"{key}: missing comparison rationale or source")
        if value(r,"Pair key")!=pid+"|"+cid or value(r,"Integrity Check").upper() not in {"OK","PASS"}:
            errors.append(f"{key}: comparison pair/integrity failure")
        try: date.fromisoformat(value(r,"Assessment date"))
        except ValueError: errors.append(f"{key}: invalid assessment date")
        for field,target in refs.items():
            if any(x not in target for x in split_ids(r.get(field))):
                errors.append(f"{key}: invalid {field}")
        old=value(r,"Supersedes Comparison ID")
        if old and (old not in ids or any(value(ids[old],f)!=value(r,f) for f in ("Product ID","Criterion ID"))):
            errors.append(f"{key}: invalid comparison supersession")
        seen={key}
        while old in ids:
            if old in seen:
                errors.append(f"{key}: comparison supersession cycle")
                break
            seen.add(old)
            old=value(ids[old],"Supersedes Comparison ID")
    if previous and ASSESS in previous:
        prior=registry(previous,ASSESS,"Comparison ID")
        if set(prior)-set(ids): errors.append("Comparison Assessment: historical IDs disappeared")
        immutable=[f for f in FIELDS if f not in {"Pair key","Integrity Check"}]
        if any(any(value(prior[k],f)!=value(ids[k],f) for f in immutable) for k in set(prior)&set(ids)):
            errors.append("Comparison Assessment: historical evidence modified; append correction instead")
    return sorted(set(errors))

def direct_current(data):
    rows=source_rows(data,ASSESS)
    retired={value(r,"Supersedes Comparison ID") for r in rows if value(r,"Supersedes Comparison ID")}
    groups=defaultdict(list)
    for r in rows:
        if value(r,"Comparison ID") not in retired:
            groups[(value(r,"Product ID"),value(r,"Criterion ID"))].append(r)
    result={}
    for pair,g in groups.items():
        states={value(r,"Verdict") for r in g}
        status=next(iter(states)) if len(states)==1 else "Disputed"
        evidence=max((value(r,"Evidence level") for r in g),key=lambda x:EVIDENCE_RANK.get(x,-1))
        result[pair]={"status":status,"evidence":evidence,"rows":g}
    return result

def direct_matrix(data,products=None,criteria=None):
    products=list(registry(data,"Products","Product ID")) if products is None else list(products)
    criteria=list(registry(data,CRITERIA,"Criterion ID")) if criteria is None else list(criteria)
    m=pd.DataFrame("Unassessed",index=products,columns=criteria)
    for (p,c),r in direct_current(data).items():
        if p in m.index and c in m.columns: m.loc[p,c]=r["status"]
    return m

def matrix_audit(data):
    if VIEW not in data: return ["Derived comparison worksheet absent"]
    m=direct_matrix(data); out=[]
    rows=registry(data,VIEW,"Product ID")
    if len(rows)!=sum(bool(value(r,"Product ID")) for r in source_rows(data,VIEW)): out.append("Derived matrix contains duplicate product IDs")
    if set(rows)!=set(m.index): out.append("Derived matrix product IDs differ from canonical products")
    if not set(m.columns).issubset(data[VIEW]["headers"]): out.append("Derived matrix missing criterion columns")
    for p in m.index:
        if p not in rows: continue
        for c in m.columns:
            raw=value(rows[p],c)
            shown="Unassessed" if raw in {"","Not assessed"} else raw
            if shown!=m.loc[p,c]:
                out.append(f"{p} / {c}: ledger {m.loc[p,c]}, derived {shown}")
    return out

def profile(cfg,cid,mode):
    r=cfg.get("command_profiles",{}).get(cid,{})
    if mode=="As-Is":
        # Product owner declares the listed AIT-VISTA criteria implemented.
        # Explicit local status overrides remain possible. No evidence gate.
        status=r.get("status","Supported")
        return status if status in BASE_STATES else "Unknown"
    scope=r.get("mvp","Unknown") if mode=="MVP" else r.get("target","Included")
    return {"Included":"Target","Excluded":"Not applicable"}.get(scope,"Unknown")

def scope_ids(data,cfg,mode):
    return [c for c in registry(data,CRITERIA,"Criterion ID") if profile(cfg,c,mode) in ({"Target"} if mode!="As-Is" else {"Supported","Partially supported"})]

def threat_table(data,mat,weights,criterion_weights=None):
    cols=list(mat.columns)
    if not cols or mat.empty: return pd.DataFrame()
    cw={c:float(weights.get(c,1)) for c in cols}
    w=criterion_weights or {"Functional overlap":5,"Space relevance":3,"Commercial availability":2,"Documented adoption":2}
    b=score_bounds(mat,cw).set_index("Product ID")
    # Keep functional and commercial axes independent.
    market_weights={k:v for k,v in w.items() if k!="Functional overlap"}
    market_weights["Functional overlap"]=0
    commercial=commercial_mcda(data,mat,cw,market_weights).set_index("Product ID")
    total=commercial_mcda(data,mat,cw,w).set_index("Product ID")
    products=registry(data,"Products","Product ID")
    companies=registry(data,"Companies","Company ID")
    current=direct_current(data)
    rows=[]
    for pid,r in mat.iterrows():
        p=products[pid]; role=value(p,"Competition Type") or "Unclassified"
        known=float(b.loc[pid,"Known weight"])
        evidence=[current[(pid,c)]["evidence"] for c in cols if (pid,c) in current and r[c] in KNOWN]
        strong=sum(EVIDENCE_RANK.get(e,0)>=3 for e in evidence)
        low=float(total.loc[pid,"Lower"]); high=float(total.loc[pid,"Upper"])
        classification=classify(p)
        analytical=classification["Analytical role"]
        exposure=attention(low,high)
        if analytical=="Direct visual AIT candidate": action="Review visual AIT substitution and operational performance"
        elif analytical=="Workflow / procurement substitute candidate": action="Verify shared buyer, procurement and workflow replacement"
        elif analytical=="Cross-industry competitor candidate": action="Check spacecraft AIT adaptation and customer overlap"
        elif analytical in {"Enabling technology","Complementary system"}: action="Check integration vs substitution; do not assume direct competition"
        elif analytical in {"Research / emerging entrant","Internal / custom solution","Historical solution"}: action="Monitor external availability and transition to commercial offer"
        else: action="Resolve product role and procurement overlap"
        criteria=registry(data,CRITERIA,"Criterion ID")
        supported=[value(criteria[c],"Product criterion") for c in cols if r[c]=="Supported"]
        partial=[value(criteria[c],"Product criterion") for c in cols if r[c]=="Partially supported"]
        unknown=[c for c in cols if r[c] not in KNOWN and r[c]!="Not applicable"]
        reason=("Full recorded criterion support: "+", ".join(supported[:3])) if supported else ("Partial recorded scope: "+", ".join(partial[:3])) if partial else "No positive direct criterion verdict in selected scope"
        rows.append({"Product ID":pid,"Product":value(p,"Product Name"),"Company":value(companies.get(value(p,"Company ID"),{}),"Company Name"),
            "Role":role,**classification,"Family ID":family_root(products,pid),"Attention":exposure,"Source priority":value(p,"Strategic Priority"),"Review action":action,"Why watch":reason,"Unresolved criteria":len(unknown),
            "Overlap lower":float(b.loc[pid,"Lower"]),"Overlap upper":float(b.loc[pid,"Upper"]),
            "Market lower":float(commercial.loc[pid,"Lower"]),"Market upper":float(commercial.loc[pid,"Upper"]),
            "Threat lower":low,"Threat upper":high,"Known weight":known,"Technical/independent records":strong,
            "Rank group":ROLE_ORDER.get(role,4),"Commercial status":value(p,"Commercial Status"),
            "Space relevance":value(p,"Space Industry Applicability"),"Customer segment":value(p,"Target Customers")})
    return pd.DataFrame(rows).sort_values(["Threat upper","Threat lower","Product ID"],ascending=[False,False,True],na_position="last")

def advantages(data,mat,cfg,mode):
    current=direct_current(data)
    criteria=registry(data,CRITERIA,"Criterion ID")
    result=[]
    products=registry(data,"Products","Product ID")
    for c in mat.columns:
        our=profile(cfg,c,mode); r=cfg.get("command_profiles",{}).get(c,{})
        column=mat[c]; eligible=column[column!="Not applicable"]
        known=eligible[eligible.isin(KNOWN)]
        positives=known[known.isin(["Supported","Partially supported"])]
        # Group explicit platform/module relationships for cohort metrics.
        families=defaultdict(list)
        for p,s in eligible.items(): families[family_root(products,p)].append((p,s))
        family_status={}
        for f,members in families.items():
            scores=[KNOWN[s] for p,s in members if s in KNOWN]
            if 1. in scores: family_status[f]="Supported"
            elif any(s not in KNOWN for p,s in members): family_status[f]="Unknown"
            elif scores: family_status[f]="Partially supported" if max(scores)==.5 else "Explicitly unsupported"
            else: family_status[f]="Unknown"
        n=len(families); unresolved=sum(s=="Unknown" for s in family_status.values())
        strong=all(EVIDENCE_RANK.get(current.get((p,c),{}).get("evidence",""),0)>=3 for p in eligible.index)
        # No market-wide absence claim. Every applicable member must be resolved and strong.
        complete=n>0 and len(known)==len(eligible) and strong
        demand=r.get("demand")=="Validated" and bool(str(r.get("demand_reference","")).strip())
        actual=our in KNOWN
        best=max((KNOWN[v] for v in known),default=None)
        if our=="Not applicable": label="Outside selected scope"
        elif not n: label="No applicable competitor in cohort"
        elif actual and best is not None and KNOWN[our]<best: label="Observed disadvantage"
        elif our=="Target" and best==1: label="Planned parity / existing offer"
        elif actual and complete and KNOWN[our]==best: label="Observed parity"
        elif actual and best==1 and KNOWN[our]==1: label="Recorded functional parity with at least one competitor"
        elif actual and complete and KNOWN[our]>best: label="Functional advantage (selected cohort)"
        elif actual and best is not None and KNOWN[our]>best: label="Potential advantage — incomplete competitor evidence"
        elif actual and not len(positives): label="Insufficient evidence — investigate potential white space"
        elif our=="Target" and complete and best<1: label="Planned differentiation hypothesis"
        elif our=="Target" and not len(positives): label="Research white-space hypothesis"
        elif our=="Target": label="Planned overlap — differentiation unproven"
        else: label="Insufficient evidence"
        # Best observed competitor is only a lower bound on the best possible.
        best_upper=1. if len(known)<len(eligible) or not strong else best
        delta_low=KNOWN[our]-best_upper if actual and best_upper is not None else None
        delta_high=KNOWN[our]-best if actual and best is not None else None
        if actual and best is None and n: delta_low=KNOWN[our]-1;delta_high=KNOWN[our]
        result.append({"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"AIT-VISTA":our,
            "Assessment":label,"Known competitors":n-unresolved,"Eligible competitors":n,"Unresolved":unresolved,
            "Existing full support":sum(s=="Supported" for s in family_status.values()),"Existing partial support":sum(s=="Partially supported" for s in family_status.values()),
            "Applicable products":len(eligible),"Determinate products":len(known),"Customer importance (team estimate)":r.get("strategic_value","Unknown"),
            "Operational performance comparison":"Not established — comparable measures required",
            "AIT-VISTA maturity":r.get("stage","Implemented (team-declared)"),
            "Best observed":best,"Delta lower":delta_low,"Delta upper":delta_high,"Demand": "Validated (local declaration)" if demand else "Unvalidated",
            "AIT-VISTA basis":"Team-declared functionality" if mode=="As-Is" else "Selected scope",
            "Reference":r.get("reference",""),"Demand reference":r.get("demand_reference","")})
    return pd.DataFrame(result)

def research_queue(data,mat,cfg,snapshot_date=""):
    current=direct_current(data); products=registry(data,"Products","Product ID"); criteria=registry(data,CRITERIA,"Criterion ID")
    out=[]
    for p,row in mat.iterrows():
        pr=products[p]; role=value(pr,"Competition Type")
        for c,s in row.items():
            e=current.get((p,c),{}); level=e.get("evidence","")
            if s=="Not applicable": continue
            age=None
            try: age=(date.today()-max(date.fromisoformat(value(r,"Assessment date")) for r in e.get("rows",[]))).days
            except (ValueError,TypeError): pass
            weak=EVIDENCE_RANK.get(level,0)<3
            stale=age is not None and age>=int(cfg.get("research_stale_days",90))
            if s in KNOWN and not weak and not stale: continue
            imp=float(cfg.get("command_profiles",{}).get(c,{}).get("importance",3))
            role_weight=5 if classify(pr)["Analytical role"] in {"Direct visual AIT candidate","Workflow / procurement substitute candidate"} else 3 if role in {"Direct","Adjacent / substitute"} else 1
            priority=role_weight+imp+(3 if s=="Disputed" else 2 if s in {"Unknown","Unassessed","Announced"} else 1)+(1 if stale else 0)
            ids={x for r in e.get("rows",[]) for field in ("Comparison ID","Related Assessment IDs","Related Observation IDs","Related Evidence IDs") for x in split_ids(r.get(field))}
            reasons=[s] if s not in KNOWN else []
            if weak: reasons.append("Weak or missing evidence")
            if stale: reasons.append("Assessment review due")
            out.append({"Product ID":p,"Criterion ID":c,"Research question":f"Verify whether {value(pr,'Product Name')} meets the full criterion: {value(criteria[c],'Product criterion')}. Identify conditions, limits and primary evidence.",
              "Strategic decision affected":"Functional differentiation / product positioning" if profile(cfg,c,"As-Is")=="Supported" else "Product scope / development priority",
              "Priority":priority,"Existing evidence IDs":"; ".join(sorted(ids)),"Reason for uncertainty":"; ".join(reasons),"Snapshot date":snapshot_date})
        cl=classify(pr)
        if cl["Missing context"] or cl["Analytical role"]=="Unresolved role" or cl["Analytical role"].endswith("candidate"):
            refs={x for field in ("Related Observation IDs",) for x in split_ids(pr.get(field))}
            out.append({"Product ID":p,"Criterion ID":"","Research question":f"Establish {value(pr,'Product Name')}'s target buyer, procurement overlap, AIT use case, independent availability and deployment architecture. Distinguish platform and modules.",
                "Strategic decision affected":"Competitive classification / substitution / monitoring priority",
                "Priority":10 if role=="Direct" else 7,"Existing evidence IDs":"; ".join(sorted(refs)),
                "Reason for uncertainty":cl["Classification basis"]+" Missing fields: "+(cl["Missing context"] or "none; buying decision remains unestablished"),"Snapshot date":snapshot_date})
    return pd.DataFrame(out,columns=["Product ID","Criterion ID","Research question","Strategic decision affected","Priority","Existing evidence IDs","Reason for uncertainty","Snapshot date"]).sort_values(["Priority","Product ID","Criterion ID"],ascending=[False,True,True])

def comparison_changes(before,after):
    a=direct_current(before); b=direct_current(after)
    out=[]
    for pair in sorted(set(a)|set(b)):
        x=a.get(pair,{}); y=b.get(pair,{})
        s0=x.get("status","Unassessed");s1=y.get("status","Unassessed")
        e0=x.get("evidence","");e1=y.get("evidence","")
        ids0="; ".join(value(r,"Comparison ID") for r in x.get("rows",[])); ids1="; ".join(value(r,"Comparison ID") for r in y.get("rows",[]))
        if (s0,e0,ids0)==(s1,e1,ids1): continue
        out.append({"Product ID":pair[0],"Criterion ID":pair[1],"Before":s0,"After":s1,"Evidence before":e0,"Evidence after":e1,"Record IDs":ids1,"Interpretation":"New recorded knowledge" if s0=="Unassessed" else "Recorded evidence/assessment changed; product release not established"})
    return pd.DataFrame(out)

def overlap_history(snapshots,product_ids,criteria,weights):
    """Fixed criterion set. Missing historical criteria are not scored."""
    rows=[]
    for stamp,data in snapshots:
        if ASSESS not in data or not set(criteria).issubset(registry(data,CRITERIA,"Criterion ID")):
            continue
        ids=[p for p in product_ids if p in registry(data,"Products","Product ID")]
        if not ids or not criteria: continue
        m=direct_matrix(data,ids,criteria)
        # Treat changing applicability as unresolved for a fixed denominator.
        m=m.replace("Not applicable","Unknown")
        for r in score_bounds(m,weights).to_dict("records"):
            rows.append({"Snapshot":stamp,**r})
    return pd.DataFrame(rows,columns=["Snapshot","Product ID","Lower","Upper","Known weight"])

def head_to_head(data,mat,cfg,pid,mode):
    current=direct_current(data)
    criteria=registry(data,CRITERIA,"Criterion ID")
    rows=[]
    for c in mat.columns:
        ours=profile(cfg,c,mode)
        theirs=mat.loc[pid,c]
        e=current.get((pid,c),{})
        level=e.get("evidence","")
        strong=EVIDENCE_RANK.get(level,0)>=3
        if ours=="Not applicable": result="Outside scope"
        elif ours=="Unknown" or theirs not in KNOWN: result="Insufficient evidence" if theirs!="Not applicable" else "Not applicable"
        elif ours=="Target": result="Planned functionality / existing competitor offer" if theirs=="Supported" else "Planned differentiation hypothesis"
        elif not strong: result="Provisional comparison — weak competitor evidence"
        elif KNOWN[ours]>KNOWN[theirs]: result="AIT-VISTA functional superiority"
        elif KNOWN[ours]<KNOWN[theirs]: result="Competitor functional superiority"
        else: result="Functional parity"
        rows.append({"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"AIT-VISTA":ours,"Competitor":theirs,"Comparison":result,"Evidence level":level,
            "Comparison IDs":"; ".join(value(r,"Comparison ID") for r in e.get("rows",[])),
            "Limitations":"; ".join(value(r,"Limitations") for r in e.get("rows",[])),
            "Operational performance":"Not established by categorical verdict"})
    return pd.DataFrame(rows)
