"""Capture real Streamlit browser screenshots on a fictitious, isolated dataset.
Requires playwright + Chromium (CI or an optional local environment).
Never reads or copies operational credentials, snapshots, or config.
"""
import os,sys,time,shutil,tempfile,subprocess,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))
from test_command import comparison_fixture
from core import connect,store,normalize_sheet,validate
from command_engine import FIELDS,ASSESS,VIEW

def sample():
    d=comparison_fixture()
    def append(tab,row):
        for k in row:
            if k not in d[tab]["headers"]:d[tab]["headers"].append(k)
        d[tab]["rows"].append(row)
    companies=[("DEMO-CO-1","Example Robotics","Example Visual QA","Automated Visual Inspection","Space offering"),
               ("DEMO-CO-2","Example Workflow","Example MES","Manufacturing Execution Systems","Space manufacturing deployment"),
               ("DEMO-CO-3","Example Orbital","Example Assembly AI","Assembly Guidance","Space offering"),
               ("DEMO-CO-4","Example Factory","Example Industrial Vision","Automated Visual Inspection","Not established")]
    for i,(cid,name,product,category,space) in enumerate(companies,1):
        co={"Company ID":cid,"Company Name":name,"Country":"Fictitious example","Alternative Names":"Demo "+str(i)}
        p={"Product ID":"DEMO-P"+str(i),"Company ID":cid,"Product Name":product,"Product Category":category,"Competition Type":"Direct" if i<4 else "Adjacent / substitute","Commercial Status":"Commercial","Strategic Priority":"High","Space Industry Applicability":space,"Target Customers":"Synthetic manufacturing and integration teams","Target Industries":"Illustrative manufacturing","Deployment Architecture":"Local processing" if i==1 else "Cloud with local components","Primary Use Case":"Manage spacecraft assembly procedures and test records" if i==2 else "Visual inspection of spacecraft assembly" if i!=4 else "Visual inspection of industrial assembly","Product Description":"Fictitious product for interface verification only.","Product URL":"https://example.invalid/"}
        if i<=2:
            for tab,r in [("Companies",co),("Products",p)]:
                d[tab]["rows"][i-1].update(r)
                for k in r:
                    if k not in d[tab]["headers"]:d[tab]["headers"].append(k)
        else:append("Companies",co);append("Products",p)
        if i!=1:
            append("Observations",{"Observation ID":"DEMO-O"+str(i),"Company ID":cid,"Observation":"Illustrative customer, architecture or product information. Not real market evidence.","Date added (ISO)":"2026-11-27","Implication for AIT-VISTA":"Review the relevant workflow and deployment assumptions.","Source URL":"https://example.invalid/"})
        append("Deployments",{"Deployment ID":"DEMO-D"+str(i),"Product ID":p["Product ID"],"Customer Organisation":"Example Customer "+str(i),"Deployment Status":"Documented implementation","Deployment Date":"2026-11-20","Use Case":"Synthetic example deployment","Source URL":"https://example.invalid/","Evidence Limitations":"Fictitious fixture"})
        append("Commercial Intelligence",{"Commercial Record ID":"DEMO-M"+str(i),"Product ID":p["Product ID"],"Business Model":"Illustrative subscription","Subscription Cost":"100","Currency":"EUR","Price Basis":"Fictitious per month, not a real offer","Applicable Date":"2026-11-20","Source URL":"https://example.invalid/"})
    crit=[("003","Physical configuration verification"),("004","Observed procedure verification"),("002","Automated AIT documentation"),("020","Fully local / offline operation"),("005","Passive AIT recording"),("008","Dynamic mechanism verification"),("022","Vendor-independent architecture"),("009","Digital procedure management"),("015","Non-visual measurement records")]
    ids=["AV-CR-"+i for i,_ in crit]
    d["AIT-VISTA Capabilities"]=normalize_sheet("AIT-VISTA Capabilities",[["Criterion ID","Product criterion","Type","Related market capability IDs"],*[[c,n,"Capability","DEMO-C1"] for c,(_,n) in zip(ids,crit)]])
    d["AIT-VISTA System Functions"]["rows"][0]["Comparison criterion IDs"]=ids[0]
    verdicts=[["Supported","Supported","Supported","Supported","Partially supported","Partially supported","Partially supported","Supported","Unknown"],
              ["Not assessed","Unknown","Supported","Partially supported","Partially supported","Not assessed","Not assessed","Supported","Supported"],
              ["Partially supported","Partially supported","Unknown","Unknown","Supported","Not assessed","Partially supported","Announced","Not assessed"],
              ["Supported","Not assessed","Partially supported","Unknown","Not assessed","Not assessed","Explicitly unsupported","Not assessed","Partially supported"]]
    ledger=[]
    for k,vs in enumerate(verdicts,1):
        for j,s in enumerate(vs):
            if s=="Not assessed":continue
            p="DEMO-P"+str(k);c=ids[j]
            ledger.append([f"DEMO-CMP-{k}-{j}",p,c,s,"Insufficient evidence" if s=="Unknown" else "Official technical documentation" if (k+j)%2 else "Vendor claim","Fictitious comparison for UI acceptance.","https://example.invalid/","","DEMO-O"+str(k),"","2026-11-27","","Synthetic fixture only",p+"|"+c,"OK"])
    d[ASSESS]=normalize_sheet(ASSESS,[FIELDS,*ledger])
    d[VIEW]=normalize_sheet(VIEW,[["Product ID","Company","Product",*ids],["","","",*[n for _,n in crit]],*[[f"DEMO-P{k}",companies[k-1][1],companies[k-1][2],*vs] for k,vs in enumerate(verdicts,1)]])
    errors,warnings=validate(d)
    if errors:raise RuntimeError(str(errors))
    return d

def capture(out):
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cie-ux-") as temp:
        work=Path(temp)/"app"
        shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns("data","credentials","config.local.json","reports",".venv","__pycache__",".pytest_cache","screenshots"))
        with connect(work/"data"/"intelligence.db") as conn:store(conn,sample(),source="Synthetic UX fixture",mark_synced=False)
        env={**os.environ,"CIE_VISUAL_PREVIEW":"1"}
        log=out/"streamlit.log"
        with log.open("w",encoding="utf-8") as f:
            p=subprocess.Popen([sys.executable,"-m","streamlit","run","app.py","--server.headless=true","--server.port=8765"],cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT)
            try:
                for _ in range(80):
                    try:
                        urllib.request.urlopen("http://127.0.0.1:8765/_stcore/health",timeout=1);break
                    except OSError:time.sleep(.5)
                else:raise RuntimeError("Streamlit failed to start")
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(args=["--no-sandbox"])
                    page=browser.new_page(viewport={"width":1600,"height":1080},device_scale_factor=1)
                    page.goto("http://127.0.0.1:8765",wait_until="domcontentloaded")
                    def ready(heading):
                        page.get_by_role("heading",name=heading,exact=True).wait_for(timeout=45000)
                        page.wait_for_timeout(900)
                        errors=page.get_by_test_id("stException")
                        if errors.count():raise RuntimeError(errors.first.inner_text())
                    def shot(name):
                        page.screenshot(path=str(out/(name+".png")),animations="disabled")
                    def top():
                        page.evaluate("""() => {
                          document.scrollingElement.scrollTop=0;
                          for (const el of document.querySelectorAll('main,section,div')) {
                            if (el.scrollHeight>el.clientHeight+5 && el.scrollTop>0) el.scrollTop=0;
                          }
                        }""")
                        page.wait_for_timeout(350)
                    def section(name):
                        page.get_by_role("heading",name=name,exact=True).evaluate("(el) => el.scrollIntoView({block:'start',inline:'nearest'})")
                        page.wait_for_timeout(400)
                    def nav(name):
                        page.get_by_test_id("stSidebar").get_by_text(name,exact=True).click()
                        ready(name)
                        top()
                    ready("Competitive Command Centre")
                    shot("01_Command_Centre")
                    page.get_by_role("button",name="Open profile",exact=True).first.click()
                    ready("Competitor Explorer")
                    top()
                    shot("02_Competitor_Explorer")
                    page.get_by_text("Compare",exact=True).click()
                    page.get_by_text("Inspect criterion evidence",exact=True).wait_for(timeout=30000)
                    page.wait_for_timeout(700)
                    page.get_by_text("Inspect criterion evidence",exact=True).evaluate("(el)=>el.scrollIntoView({block:'center'})")
                    shot("03_Profile_Comparison")
                    nav("Market Positioning")
                    shot("04_Market_Positioning")
                    section("AIT workflow coverage")
                    shot("05_AIT_Workflow")
                    nav("Competitive Advantage")
                    shot("06_Competitive_Advantage")
                    section("Differentiation portfolio")
                    shot("07_Advantage_Portfolio")
                    nav("Intelligence Monitor")
                    shot("08_Intelligence_Monitor")
                    assert (out/"04_Market_Positioning.png").read_bytes() != (out/"05_AIT_Workflow.png").read_bytes(), "Map and workflow screenshots are identical"
                    assert (out/"06_Competitive_Advantage.png").read_bytes() != (out/"07_Advantage_Portfolio.png").read_bytes(), "Advantage screenshots are identical"
                    browser.close()
            finally:
                p.terminate()
                try:p.wait(timeout=10)
                except subprocess.TimeoutExpired:p.kill()
    (out/"README.txt").write_text("Actual browser screenshots of the v1.4.1 Streamlit app.\nAll displayed companies, prices, deployments and competitor evidence are fictitious UI fixtures. Not a live 5PACE dataset or research result.\n",encoding="utf-8")

if __name__=="__main__":capture(Path(sys.argv[1] if len(sys.argv)>1 else "screenshots").resolve())
