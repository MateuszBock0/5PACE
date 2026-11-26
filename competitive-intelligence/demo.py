"""Synthetic fixtures only. Never mixed with the operational database."""
from core import TABLES
def fixture():
    data={t:{"headers":list(h),"rows":[]} for t,h in TABLES.items()}
    def add(t,**row):
        for k in row:
            if k not in data[t]["headers"]: data[t]["headers"].append(k)
        data[t]["rows"].append(row)
    add("Companies",**{"Company ID":"DEMO-CO-1","Company Name":"Example Robotics"})
    add("Companies",**{"Company ID":"DEMO-CO-2","Company Name":"Example Workflow"})
    add("Products",**{"Product ID":"DEMO-P1","Company ID":"DEMO-CO-1","Product Name":"Example Vision","Competition Type":"Adjacent / substitute","Strategic Priority":"High"})
    add("Products",**{"Product ID":"DEMO-P2","Company ID":"DEMO-CO-2","Product Name":"Example Procedure","Competition Type":"Direct","Strategic Priority":"High"})
    for cid,name,cat in [("DEMO-C1","Presence check","VIS"),("DEMO-C2","Procedure execution","PRC"),("DEMO-C3","Offline operation","DEP")]:
        add("Capabilities",**{"Capability ID":cid,"Capability Name":name,"Category ID":cat,"Taxonomy Status":"Active"})
    add("Observations",**{"Observation ID":"DEMO-O1","Company ID":"DEMO-CO-1","Observation":"Synthetic example only"})
    add("Main",**{"Observation ID":"DEMO-O1","Company ID":"DEMO-CO-1"})
    for i,p,c,s,e in [(1,"DEMO-P1","DEMO-C1","Supported","Vendor claim"),(2,"DEMO-P1","DEMO-C3","Unknown","Insufficient evidence"),(3,"DEMO-P2","DEMO-C2","Supported","Official technical documentation"),(4,"DEMO-P2","DEMO-C1","Explicitly unsupported","Official technical documentation")]:
        add("Capability Assessment",**{"Assessment ID":f"DEMO-A{i}","Product ID":p,"Capability ID":c,"Availability Status":s,"Evidence Level":e,"Review Status":"Reviewed","Supersedes Assessment ID":"","Evidence Description":"Synthetic demonstration, not market data","Source URL":"https://example.invalid/","Related Observation IDs":"DEMO-O1"})
    return data
