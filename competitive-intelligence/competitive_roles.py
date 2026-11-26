"""Transparent, provisional product roles using existing source fields only."""
from core import value, split_ids

VISUAL={"Automated Visual Inspection","Assembly Guidance","Process Verification","Augmented Reality Assembly Assistance"}
WORKFLOW={"Digital Work Instructions","Manufacturing Execution Systems","Manufacturing Traceability","Manufacturing Analytics","Test Management"}
ENABLING={"Computer Vision","Digital Twins","Industrial Automation"}
COMPLEMENT={"Spacecraft Checkout Systems","Geometrical Verification","Measurement Assistance"}
ROLES=["Direct visual AIT candidate","Workflow / procurement substitute candidate","Cross-industry competitor candidate","Enabling technology","Complementary system","Internal / custom solution","Research / emerging entrant","Historical solution","Unresolved role"]

def family_root(products,pid):
    seen=set()
    current=pid
    while current in products and current not in seen:
        seen.add(current)
        parent=value(products[current],"Product Family")
        if not parent or parent not in products: return current
        current=parent
    return pid

def classify(p):
    cat=value(p,"Product Category")
    use=value(p,"Primary Use Case")
    customers=value(p,"Target Customers")
    industries=value(p,"Target Industries")
    commercial=value(p,"Commercial Status")
    role=value(p,"Competition Type")
    text=(use+" "+customers+" "+industries).lower()
    space=any(x in text for x in ("spacecraft","satellite","space hardware","space manufacturing","space equipment","space-equipment","space-sector","space / aerospace"))
    visual=any(x in use.lower() for x in ("visual","camera","image","3d sensor","optical","photograph","computer vision","inspect"))
    assembly=any(x in use.lower() for x in ("assembly","ait","integration","component","workmanship","procedure","inspection"))
    checkout=cat=="Spacecraft Checkout Systems" or ("checkout" in use.lower() and not visual)
    if commercial=="Internal / custom": label="Internal / custom solution"; why="Source commercial status: internal/custom; external availability unestablished."
    elif commercial=="Historical": label="Historical solution"; why="Source commercial status: historical."
    elif commercial=="Research" or role=="Potential entrant": label="Research / emerging entrant"; why="Source research/entrant classification; commercial substitution not established."
    elif checkout: label="Complementary system"; why="Checkout/testing category or use case; visual AIT substitution not established."
    elif use and space and visual and assembly and cat in VISUAL: label="Direct visual AIT candidate"; why="Recorded visual/assembly use case and space-sector relevance; same procurement and operational fit still require review."
    elif use and space and cat in WORKFLOW: label="Workflow / procurement substitute candidate"; why="Recorded workflow/traceability/test use case and space relevance; same buying decision not established."
    elif cat in ENABLING: label="Enabling technology"; why="Product category indicates technology/tooling; integrated AIT substitution not established."
    elif cat in COMPLEMENT: label="Complementary system"; why="Measurement/checkout category; full AIT substitution not established."
    elif use and cat in VISUAL|WORKFLOW: label="Cross-industry competitor candidate"; why="Recorded related workflow/visual use case; spacecraft customer and procurement overlap not established."
    else: label="Unresolved role"; why="Insufficient explicit product-use-case/customer evidence for finer classification."
    missing=[f for f in ("Primary Use Case","Target Customers","Target Industries","Deployment Architecture") if not value(p,f)]
    return {"Analytical role":label,"Classification basis":why,"Missing context":"; ".join(missing),"Source role":role or "Unclassified"}

def family_watchlist(threat):
    """One row per explicit family. No merging of individual functional scores."""
    if threat.empty: return threat.copy()
    rows=[]
    for family,g in threat.groupby("Family ID",sort=False):
        # Representative is a real product, chosen by upper then lower scenario bound.
        # Family interval is the max of member intervals, not a sum or combined feature claim.
        g=g.sort_values(["Threat upper","Threat lower","Product ID"],ascending=[False,False,True],na_position="last")
        r=g.iloc[0].to_dict()
        r["Family lower"]=g["Threat lower"].max()
        r["Family upper"]=g["Threat upper"].max()
        r["Family members"]=len(g)
        r["Member IDs"]="; ".join(g["Product ID"])
        rows.append(r)
    import pandas as pd
    out=pd.DataFrame(rows)
    return out.sort_values(["Family upper","Family lower","Family ID"],ascending=[False,False,True],na_position="last")

def attention(lower,upper):
    # Configured triage convention, not calibrated probabilities or risk prediction.
    if upper<.65: return "Lower scenario exposure"
    if lower>=.65: return "High recorded exposure"
    return "Potential high exposure — unresolved"
