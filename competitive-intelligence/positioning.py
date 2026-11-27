"""Market positioning on a fixed criterion set; no inferred verdicts or source writes."""
import re
import numpy as np
import pandas as pd
from core import value
from analytics import KNOWN, EVIDENCE_RANK
from command_engine import registry, direct_current, profile
from competitive_roles import classify, family_root
from product_intelligence import CRITERIA
from strategic import SPACE_STRONG, SPACE_OFFER

VISTA="__AIT_VISTA__"
ALL="Overall functional scope"
DIMENSIONS=["Visual verification","Execution automation","Documentation & traceability","QA / PA","Workflow management","Deployment architecture","Enterprise integration","Analytics & model management","Other / unmapped"]
COMMERCIAL=["Commercial availability","Space relevance","Documented adoption","Commercial readiness"]
WORKFLOWS=["Prepare procedures","Execute & capture","Verify physical state","Resolve deviations","Review & approve","Archive & analyse"]
EVIDENCE_MODES={"All recorded verdicts":0,"Technical documentation or stronger":3,"Independent documentation or stronger":4}

# Generic label-based taxonomy, visible and overridable locally. No real source rows in Git.
DIM_RULES=[
 ("Enterprise integration",r"enterprise system integration|enterprise integration|external system integration"),
 ("Deployment architecture",r"offline|standalone|vendor.independent|modular software|data security|access management|data residency|generative ai|local operation"),
 ("Analytics & model management",r"model management|model updating|cross.unit comparison|performance statistics|process analytics|event analysis|historical.*reconstruction"),
 ("QA / PA",r"nonconformance|non.conformance|formal approval|quality assurance|reliability assessment|human.in.the.loop|override"),
 ("Documentation & traceability",r"records|audit trail|documentation|traceability|association.*evidence|evidence.*procedure"),
 ("Visual verification",r"physical configuration|dynamic behaviour|mechanism deployment|visual measurement|visual verification|detect object|visual inspection|geometrical"),
 ("Execution automation",r"observed.*execution|passive.*recording|deviation detection|planned versus actual|automatic.*execution"),
 ("Workflow management",r"procedure|workflow|collaboration|notification|hardware units"),
 ("Visual verification",r"inspect|presence|image|camera|vision"),
]
STAGE_RULES=[
 ("Prepare procedures",r"procedure management|procedure version|procedure reuse|adaptability|procedure author|work instructions"),
 ("Execute & capture",r"passive.*record|observed.*execution|procedure management|hardware units|measurement.*documentation|association.*evidence"),
 ("Verify physical state",r"physical configuration|dynamic behaviour|mechanism deployment|visual measurement|verification reliability|observed.*execution|visual verification|inspect|presence"),
 ("Resolve deviations",r"deviation detection|nonconformance|non.conformance|human.in.the.loop|override|planned versus actual"),
 ("Review & approve",r"formal approval|quality assurance|human.in.the.loop|verification reliability|audit trail|nonconformance"),
 ("Archive & analyse",r"records|documentation|traceability|historical|cross.unit comparison|process analytics|performance statistics|event analysis|association.*evidence"),
]

def taxonomy(data,cfg):
    rows=[]
    overrides=cfg.get("positioning_dimensions",{})
    stages=cfg.get("positioning_workflows",{})
    for cid,r in registry(data,CRITERIA,"Criterion ID").items():
        name=value(r,"Product criterion")
        text=name.lower()
        dim=next((d for d,pattern in DIM_RULES if re.search(pattern,text)),"Other / unmapped")
        override=overrides.get(cid)
        if override in DIMENSIONS: dim=override
        matched=[s for s,pattern in STAGE_RULES if re.search(pattern,text)]
        if isinstance(stages.get(cid),list): matched=[s for s in WORKFLOWS if s in stages[cid]]
        rows.append({"Criterion ID":cid,"Criterion":name,"Dimension":dim,"Workflow stages":"; ".join(matched),
                     "Mapping basis":"Local override" if override in DIMENSIONS or cid in stages else "Provisional label rule"})
    return pd.DataFrame(rows,columns=["Criterion ID","Criterion","Dimension","Workflow stages","Mapping basis"])

def axis_groups(tax):
    groups={ALL:tax["Criterion ID"].tolist()}
    for d in DIMENSIONS:
        ids=tax.loc[tax.Dimension==d,"Criterion ID"].tolist()
        if ids: groups[d]=ids
    return groups

def workflow_groups(tax):
    return {s:tax.loc[tax["Workflow stages"].map(lambda x:s in x.split("; ")),"Criterion ID"].tolist() for s in WORKFLOWS}

def interval_arrays(data,mat,cfg,mode="As-Is",evidence_mode="All recorded verdicts",partial=.5):
    """Fixed denominators; N/A is incomparable, never unsupported or silently excluded."""
    if evidence_mode not in EVIDENCE_MODES: raise ValueError("Invalid evidence scenario")
    if not 0<=partial<=1: raise ValueError("Invalid partial-support convention")
    current=direct_current(data)
    idx=[VISTA]+list(mat.index)
    lo=pd.DataFrame(0.,index=idx,columns=mat.columns)
    hi=pd.DataFrame(1.,index=idx,columns=mat.columns)
    state=mat.copy().reindex(idx)
    basis=state.copy()
    known={"Supported":1.,"Partially supported":float(partial),"Explicitly unsupported":0.}
    for c in mat.columns:
        ours=profile(cfg,c,mode)
        state.loc[VISTA,c]=ours
        basis.loc[VISTA,c]="Owner declaration" if mode=="As-Is" else "Planning scope"
        if ours in known: lo.loc[VISTA,c]=hi.loc[VISTA,c]=known[ours]
        elif ours=="Target": lo.loc[VISTA,c]=hi.loc[VISTA,c]=1.
        elif ours=="Not applicable" and mode!="As-Is": lo.loc[VISTA,c]=hi.loc[VISTA,c]=0.
        for p in mat.index:
            s=mat.loc[p,c]; e=current.get((p,c),{}).get("evidence","")
            basis.loc[p,c]=e or "No direct evidence"
            if s in known and EVIDENCE_RANK.get(e,-1)>=EVIDENCE_MODES[evidence_mode]:
                lo.loc[p,c]=hi.loc[p,c]=known[s]
    return lo,hi,state,basis

def bounds(lo,hi,ids,weights=None):
    ids=list(ids)
    if not ids: return pd.DataFrame({"Lower":np.nan,"Upper":np.nan,"Determinate weight":np.nan},index=lo.index)
    w=np.array([max(0.,float((weights or {}).get(c,1))) for c in ids])
    if w.sum()==0: return pd.DataFrame({"Lower":np.nan,"Upper":np.nan,"Determinate weight":np.nan},index=lo.index)
    w=w/w.sum()
    l=lo[ids].to_numpy();h=hi[ids].to_numpy()
    return pd.DataFrame({"Lower":l@w,"Upper":h@w,"Determinate weight":np.isclose(l,h)@w},index=lo.index)

def commercial_axes(data,pids,cfg):
    """Same ordinal conventions for own product and peers; no adoption imputation."""
    products=registry(data,"Products","Product ID")
    deployments=registry(data,"Deployments","Deployment ID")
    own=cfg.get("positioning_vista_commercial",{})
    result={}
    for pid in [VISTA]+list(pids):
        p=products.get(pid,{})
        status=own.get("commercial_status","Unknown") if pid==VISTA else value(p,"Commercial Status")
        space=own.get("space_applicability","Unknown") if pid==VISTA else value(p,"Space Industry Applicability")
        deps=[r for r in deployments.values() if value(r,"Product ID")==pid]
        adoption=own.get("adoption","Unknown") if pid==VISTA else ("Documented implementation" if any(value(r,"Deployment Status")=="Documented implementation" for r in deps) else "Reported implementation" if any(value(r,"Deployment Status")=="Reported implementation" for r in deps) else "Unknown")
        a=(1.,1.) if status=="Commercial" else (0.,.5) if status in {"Announced","Research","Historical","Internal / custom"} else (0.,1.)
        b=(1.,1.) if space in SPACE_STRONG else (.5,1.) if space in SPACE_OFFER else (0.,1.)
        c=(1.,1.) if adoption=="Documented implementation" else (.5,1.) if adoption=="Reported implementation" else (0.,1.)
        result[pid]=dict(zip(COMMERCIAL,[a,b,c,tuple(np.mean([a,b,c],axis=0))]))
    return result

def positioning_table(data,lo,hi,groups,weights,cfg,mode):
    products=registry(data,"Products","Product ID"); companies=registry(data,"Companies","Company ID")
    market=commercial_axes(data,[p for p in lo.index if p!=VISTA],cfg)
    scores={axis:bounds(lo,hi,ids,weights) for axis,ids in groups.items()}
    rows=[]
    for pid in lo.index:
        p=products.get(pid,{})
        cid=value(p,"Company ID")
        r={"Product ID":pid,"Product":"AIT-VISTA ("+mode+")" if pid==VISTA else value(p,"Product Name"),"Company ID":"__5PACE__" if pid==VISTA else cid,
           "Company":"5PACE" if pid==VISTA else value(companies.get(cid,{}),"Company Name"),"Role":"AIT-VISTA reference" if pid==VISTA else classify(p)["Analytical role"],
           "Family ID":VISTA if pid==VISTA else family_root(products,pid)}
        for axis,score in scores.items():
            r[axis+" lower"]=score.loc[pid,"Lower"];r[axis+" upper"]=score.loc[pid,"Upper"];r[axis+" determinate"]=score.loc[pid,"Determinate weight"]
        for axis,(l,h) in market[pid].items(): r[axis+" lower"]=l;r[axis+" upper"]=h
        rows.append(r)
    return pd.DataFrame(rows)

def proximity(lo,hi,groups,weights=None):
    """Interval similarity to reference: 1 minus weighted absolute distance.
    Opposite interval endpoints give the greatest possible distance. No midpoint imputation."""
    rows=[]
    for axis,ids in groups.items():
        if not ids: continue
        w=np.array([max(0.,float((weights or {}).get(c,1))) for c in ids])
        if not w.sum(): continue
        w/=w.sum()
        a=lo.loc[VISTA,ids].to_numpy();b=hi.loc[VISTA,ids].to_numpy()
        for p in lo.index:
            if p==VISTA: continue
            l=lo.loc[p,ids].to_numpy();h=hi.loc[p,ids].to_numpy()
            mind=np.maximum(0,np.maximum(a-h,l-b))
            maxd=np.maximum(np.abs(a-h),np.abs(b-l))
            rows.append({"Product ID":p,"Dimension":axis,"Similarity lower":float(1-maxd@w),"Similarity upper":float(1-mind@w),
                         "Jointly determinate weight":float((np.isclose(a,b)&np.isclose(l,h))@w)})
    return pd.DataFrame(rows,columns=["Product ID","Dimension","Similarity lower","Similarity upper","Jointly determinate weight"])

def company_positions(pos,axis=ALL):
    """Portfolio envelope over individually scored products, never synthetic union."""
    rows=[]
    for company,g in pos[pos["Product ID"]!=VISTA].groupby("Company ID",sort=False):
        l=axis+" lower";h=axis+" upper"
        a=g.sort_values([l,h,"Product ID"],ascending=[False,False,True]).iloc[0]
        b=g.sort_values([h,l,"Product ID"],ascending=[False,False,True]).iloc[0]
        rows.append({"Company ID":company,"Company":a.Company,"Products":len(g),"Explicit families":g["Family ID"].nunique(),
                     "Best recorded product":a.Product,"Recorded product ID":a["Product ID"],"Highest potential product":b.Product,"Potential product ID":b["Product ID"],
                     "Portfolio lower":a[l],"Portfolio upper":b[h],"Roles":"; ".join(sorted(set(g.Role)))})
    return pd.DataFrame(rows,columns=["Company ID","Company","Products","Explicit families","Best recorded product","Recorded product ID","Highest potential product","Potential product ID","Portfolio lower","Portfolio upper","Roles"]).sort_values(["Portfolio lower","Portfolio upper","Company ID"],ascending=[False,False,True])

def advantage_portfolio(data,lo,hi,state,cfg,mode):
    """Conservative family-level prevalence and difference vs best product.
    A functional advantage needs a strictly positive lower difference; demand is separate."""
    products=registry(data,"Products","Product ID")
    criteria=registry(data,CRITERIA,"Criterion ID")
    current=direct_current(data)
    ids=[p for p in lo.index if p!=VISTA]; families={}
    for p in ids: families.setdefault(family_root(products,p),[]).append(p)
    rows=[]
    for c in lo.columns:
        r=cfg.get("command_profiles",{}).get(c,{})
        a,b=lo.loc[VISTA,c],hi.loc[VISTA,c]
        if not ids: continue
        applicable=[p for p in ids if state.loc[p,c]!="Not applicable"]
        if not applicable: continue
        best_l=float(lo.loc[applicable,c].max());best_h=float(hi.loc[applicable,c].max())
        dl=float(a-best_h);dh=float(b-best_l)
        fam=[members for members in families.values() if any(p in applicable for p in members)]
        # Presence of any positive support, not a jointly integrated offer.
        positive_lower=sum(any(p in applicable and lo.loc[p,c]>0 for p in group) for group in fam)/len(fam)
        positive_upper=sum(any(p in applicable and hi.loc[p,c]>0 for p in group) for group in fam)/len(fam)
        # A permissive evidence scenario can explore recorded claims, but must
        # not promote a vendor-only negative verdict into a substantiated edge.
        strong=all(EVIDENCE_RANK.get(current.get((p,c),{}).get("evidence",""),-1)>=3 for p in applicable)
        strong_positive=any(EVIDENCE_RANK.get(current.get((p,c),{}).get("evidence",""),-1)>=3 and lo.loc[p,c]>b for p in applicable)
        if mode!="As-Is": finding="Planning scenario"
        elif dl>1e-9: finding="Substantiated functional advantage" if strong else "Scenario advantage — weaker competitor evidence"
        elif dh< -1e-9: finding="Substantiated functional disadvantage" if strong_positive else "Scenario disadvantage — weaker competitor evidence"
        elif abs(dl)<1e-9 and abs(dh)<1e-9: finding="Functional parity with best recorded product" if strong else "Scenario parity — weaker competitor evidence"
        elif dh>1e-9 and dl>=-1e-9: finding="Potential differentiation — unresolved"
        else: finding="Insufficient comparative evidence"
        importance=r.get("customer_importance","Unknown")
        if importance not in {"Low","Medium","High"}: importance="Unknown"
        demand=r.get("demand")=="Validated" and bool(str(r.get("demand_reference","")).strip())
        rows.append({"Criterion ID":c,"Criterion":value(criteria[c],"Product criterion"),"Finding":finding,"Delta lower":dl,"Delta upper":dh,
                     "Rarity lower":1-positive_upper,"Rarity upper":1-positive_lower,"Customer importance":importance,
                     "Customer demand":"Validated (local declaration)" if demand else "Unvalidated","Demand reference":r.get("demand_reference",""),
                     "Decision":"Protect / validate value" if finding=="Substantiated functional advantage" else "Review gap" if finding=="Substantiated functional disadvantage" else "Investigate / maintain parity"})
    return pd.DataFrame(rows)

def workflow_benchmark(lo,hi,tax,weights=None):
    groups=workflow_groups(tax)
    rows=[]
    for stage,ids in groups.items():
        if not ids: continue
        b=bounds(lo,hi,ids,weights)
        for p in lo.index:
            rows.append({"Product ID":p,"Stage":stage,"Lower":b.loc[p,"Lower"],"Upper":b.loc[p,"Upper"],
                         "Delta vs AIT-VISTA lower":float(b.loc[p,"Lower"]-b.loc[VISTA,"Upper"]) if p!=VISTA else 0.,
                         "Delta vs AIT-VISTA upper":float(b.loc[p,"Upper"]-b.loc[VISTA,"Lower"]) if p!=VISTA else 0.,
                         "All mapped criteria lower":float(lo.loc[p,ids].min()),"All mapped criteria upper":float(hi.loc[p,ids].min()),
                         "Determinate weight":b.loc[p,"Determinate weight"],"Criterion IDs":"; ".join(ids)})
    d=pd.DataFrame(rows,columns=["Product ID","Stage","Lower","Upper","Delta vs AIT-VISTA lower","Delta vs AIT-VISTA upper","All mapped criteria lower","All mapped criteria upper","Determinate weight","Criterion IDs"])
    bottlenecks=[]
    for p,g in d.groupby("Product ID",sort=False):
        bottlenecks.append({"Product ID":p,"Weakest stage lower":g.Lower.min(),"Weakest stage upper":g.Upper.min(),
                            "Stages mapped":len(g),"All mapped criteria lower":g["All mapped criteria lower"].min(),"All mapped criteria upper":g["All mapped criteria upper"].min(),"All-stage integration":"Not established by criterion assessments"})
    return d,pd.DataFrame(bottlenecks,columns=["Product ID","Weakest stage lower","Weakest stage upper","Stages mapped","All mapped criteria lower","All mapped criteria upper","All-stage integration"])

def sensitivity_analysis(data,mat,cfg,mode,weights,draws=40,seed=42):
    """Weight and evidence scenarios; rank bounds use interval dominance, not random truth.
    Equal score ties can share a rank. Scenarios are not probabilities."""
    ids=list(mat.columns); pids=list(mat.index)
    if not ids or not pids: return pd.DataFrame(),pd.DataFrame()
    rng=np.random.default_rng(seed)
    base=np.array([max(0.,float(weights.get(c,1))) for c in ids])
    if not base.sum(): return pd.DataFrame(),pd.DataFrame()
    w=np.vstack([base,base*rng.uniform(.5,1.5,size=(max(1,int(draws)),len(ids)))])
    w=w/w.sum(axis=1,keepdims=True)
    detail=[]
    for em in EVIDENCE_MODES:
        for partial in (.25,.5,.75):
            lo,hi,_,_=interval_arrays(data,mat,cfg,mode,em,partial)
            a=lo.loc[VISTA].to_numpy();b=hi.loc[VISTA].to_numpy()
            l=lo.loc[pids].to_numpy();h=hi.loc[pids].to_numpy()
            low=1-np.maximum(np.abs(a-h),np.abs(b-l))@w.T
            high=1-np.maximum(0,np.maximum(a-h,l-b))@w.T
            for k,p in enumerate(pids):
                # best rank: only competitors guaranteed strictly above.
                # worst rank: all others possibly strictly above.
                best=1+(low>high[k]+1e-9).sum(axis=0)
                worst=1+(high>low[k]+1e-9).sum(axis=0)-(high[k]>low[k]+1e-9)
                detail.append({"Product ID":p,"Evidence scenario":em,"Partial support":partial,
                               "Similarity lower min":float(low[k].min()),"Similarity upper max":float(high[k].max()),
                               "Best possible rank":int(best.min()),"Worst possible rank":int(worst.max())})
    d=pd.DataFrame(detail)
    s=d.groupby("Product ID",as_index=False).agg({"Similarity lower min":"min","Similarity upper max":"max","Best possible rank":"min","Worst possible rank":"max"})
    return s.sort_values(["Best possible rank","Worst possible rank","Product ID"]),d
