"""Traceable internal-function ↔ product criterion ↔ market-capability mappings."""
from collections import defaultdict
import pandas as pd
from core import value, split_ids

CRITERIA="AIT-VISTA Capabilities"
FUNCTIONS="AIT-VISTA System Functions"
MATURITY={"Planned","Implemented","Demonstrated","Verified","Unknown"}

def source_rows(data,tab):
    return data.get(tab,{}).get("rows",[])

def validate_mapping(data):
    errors=[]
    if CRITERIA not in data or FUNCTIONS not in data:
        return ["AIT-VISTA mapping: both related worksheets are required when either is present"]
    cfields={"Criterion ID","Product criterion","Type","Related market capability IDs"}
    ffields={"Function ID","Functionality","Consolidated Capability ID","Comparison criterion IDs","Capability ID","Consolidated Functionality"}
    if not cfields.issubset(data[CRITERIA]["headers"]) or not ffields.issubset(data[FUNCTIONS]["headers"]):
        return ["AIT-VISTA mapping: missing required columns"]
    cr=source_rows(data,CRITERIA); fr=source_rows(data,FUNCTIONS)
    def unique(rows,field,required=False):
        keys=[value(r,field) for r in rows if value(r,field)]
        if len(keys)!=len(set(keys)) or (required and len(keys)!=len(rows)):
            errors.append("AIT-VISTA mapping: blank or duplicate "+field)
        return set(keys)
    cids=unique(cr,"Criterion ID",True)
    fids=unique(fr,"Function ID")
    cons=unique(fr,"Capability ID")
    market={value(r,"Capability ID") for r in source_rows(data,"Capabilities")}
    for r in cr:
        if not value(r,"Product criterion"): errors.append("AIT-VISTA mapping: missing criterion description")
        if any(c not in market for c in split_ids(r.get("Related market capability IDs"))):
            errors.append("AIT-VISTA mapping: unknown market capability for "+value(r,"Criterion ID"))
    for r in fr:
        fid=value(r,"Function ID")
        if fid:
            if not value(r,"Functionality"): errors.append("AIT-VISTA mapping: missing function description")
            if value(r,"Consolidated Capability ID") and value(r,"Consolidated Capability ID") not in cons:
                errors.append("AIT-VISTA mapping: unknown consolidated capability for "+fid)
            if any(c not in cids for c in split_ids(r.get("Comparison criterion IDs"))):
                errors.append("AIT-VISTA mapping: unknown comparison criterion for "+fid)
    return sorted(set(errors))

def mappings(data):
    criteria={value(r,"Criterion ID"):r for r in source_rows(data,CRITERIA)}
    consolidated={value(r,"Capability ID"):value(r,"Consolidated Functionality") for r in source_rows(data,FUNCTIONS) if value(r,"Capability ID")}
    rows=[]
    for r in source_rows(data,FUNCTIONS):
        fid=value(r,"Function ID")
        if not fid: continue
        cons=value(r,"Consolidated Capability ID")
        links=split_ids(r.get("Comparison criterion IDs"))
        market=sorted({c for link in links for c in split_ids(criteria.get(link,{}).get("Related market capability IDs"))})
        rows.append({"Function ID":fid,"Functionality":value(r,"Functionality"),
                     "Consolidated Capability ID":cons,"Consolidated functionality":consolidated.get(cons,""),
                     "Criterion IDs":"; ".join(links),"Market capability IDs":"; ".join(market),
                     "Mapping status":"Mapped" if market else "Unmapped"})
    return pd.DataFrame(rows,columns=["Function ID","Functionality","Consolidated Capability ID","Consolidated functionality","Criterion IDs","Market capability IDs","Mapping status"])

def criterion_matrix(data, mat):
    """A linked market capability is a comparison proxy, not proof of criterion fulfilment."""
    rows=[]
    for r in source_rows(data,CRITERIA):
        cid=value(r,"Criterion ID"); market=split_ids(r.get("Related market capability IDs"))
        for p in mat.index:
            statuses=[mat.loc[p,c] if c in mat.columns else "Unassessed" for c in market]
            support=sum(s=="Supported" for s in statuses)
            partial=sum(s=="Partially supported" for s in statuses)
            unsupported=sum(s=="Explicitly unsupported" for s in statuses)
            applicable=sum(s!="Not applicable" for s in statuses)
            rows.append({"Product ID":p,"Criterion ID":cid,"Criterion":value(r,"Product criterion"),
                         "Criterion type":value(r,"Type"),"Linked capabilities":len(market),
                         "Supported":support,"Partial":partial,"Explicitly unsupported":unsupported,
                         "Unresolved":applicable-support-partial-unsupported,
                         "Not applicable":len(market)-applicable,
                         "Proxy coverage":(support+partial+unsupported)/applicable if applicable else None})
    return pd.DataFrame(rows,columns=["Product ID","Criterion ID","Criterion","Criterion type","Linked capabilities","Supported","Partial","Explicitly unsupported","Unresolved","Not applicable","Proxy coverage"])

def function_profile(data,mat,product_id,local_maturity=None):
    local_maturity=local_maturity or {}
    rows=[]
    for r in mappings(data).to_dict("records"):
        linked=split_ids(r["Market capability IDs"])
        s=[mat.loc[product_id,c] if c in mat.columns else "Unassessed" for c in linked]
        rows.append({**r,"AIT-VISTA maturity":local_maturity.get(r["Function ID"],"Unknown"),
                     "Supported proxies":s.count("Supported"),"Partial proxies":s.count("Partially supported"),
                     "Unresolved proxies":sum(x not in ("Supported","Partially supported","Explicitly unsupported","Not applicable") for x in s),
                     "Unsupported proxies":s.count("Explicitly unsupported")})
    return pd.DataFrame(rows)

def target_ids(data):
    return sorted({c for r in source_rows(data,CRITERIA) for c in split_ids(r.get("Related market capability IDs"))})
