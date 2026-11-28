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
    crit=[("003","Physical configuration verification"),("004","Observed procedure verification"),("002","Automated AIT documentation"),("020","Fully local / offline operation"),("005","Passive AIT recording"),("008","Dynamic mechanism verification"),("022","Vendor-independent architecture"),("009","Digital procedure management"),("015","Non-visual measurement records"),("023","Enterprise system integration")]
    ids=["AV-CR-"+i for i,_ in crit]
    d["AIT-VISTA Capabilities"]=normalize_sheet("AIT-VISTA Capabilities",[["Criterion ID","Product criterion","Type","Related market capability IDs"],*[[c,n,"Capability","DEMO-C1"] for c,(_,n) in zip(ids,crit)]])
    d["AIT-VISTA System Functions"]["rows"][0]["Comparison criterion IDs"]=ids[0]
    verdicts=[["Supported","Supported","Supported","Supported","Partially supported","Partially supported","Partially supported","Supported","Unknown","Supported"],
              ["Not assessed","Unknown","Supported","Partially supported","Partially supported","Not assessed","Not assessed","Supported","Supported","Partially supported"],
              ["Partially supported","Partially supported","Unknown","Unknown","Supported","Not assessed","Partially supported","Announced","Not assessed","Not assessed"],
              ["Supported","Not assessed","Partially supported","Unknown","Not assessed","Not assessed","Explicitly unsupported","Not assessed","Partially supported","Not assessed"]]
    ledger=[]
    for k,vs in enumerate(verdicts,1):
        for j,s in enumerate(vs):
            if s=="Not assessed":continue
            p="DEMO-P"+str(k);c=ids[j]
            ledger.append([f"DEMO-CMP-{k}-{j}",p,c,s,"Insufficient evidence" if s=="Unknown" else "Official technical documentation" if (k+j)%2 else "Vendor claim","Fictitious comparison for UI acceptance.","https://example.invalid/","","DEMO-O"+str(k),"","2026-11-27","","Synthetic fixture only",p+"|"+c,"OK"])
    d[ASSESS]=normalize_sheet(ASSESS,[FIELDS,*ledger])
    d[VIEW]=normalize_sheet(VIEW,[["Product ID","Company","Product",*ids],["","","",*[n for _,n in crit]],*[[f"DEMO-P{k}",companies[k-1][1],companies[k-1][2],*vs] for k,vs in enumerate(verdicts,1)]])
    # 43-company fixture exercises long labels and zero-score points without private data.
    for k in range(5,44):
        cid="DEMO-CO-"+str(k);pid="DEMO-P"+str(k)
        label="Example Long-Named Manufacturing Organisation "+str(k)
        append("Companies",{"Company ID":cid,"Company Name":label,"Country":"Fictitious example"})
        append("Products",{"Product ID":pid,"Company ID":cid,"Product Name":"Example unassessed product "+str(k),"Commercial Status":"Commercial","Product URL":"https://example.invalid/"})
        append(VIEW,{"Product ID":pid,"Company":label,"Product":"Example unassessed product "+str(k),**{c:"Not assessed" for c in ids}})
    errors,warnings=validate(d)
    if errors:raise RuntimeError(str(errors))
    return d

def capture(out,live=False):
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cie-ux-") as temp:
        work=Path(temp)/"app"
        shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns("data","credentials","config.local.json","reports",".venv","__pycache__",".pytest_cache","screenshots"))
        if live:
            import sqlite3,json
            from contextlib import closing
            from core import DB,config,read_snapshot,state,history,validate
            if not DB.is_file():raise RuntimeError("No local SQLite snapshot; synchronise first.")
            (work/"data").mkdir(exist_ok=True)
            with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as a,closing(sqlite3.connect(work/"data"/"intelligence.db")) as b:a.backup(b)
            with connect(work/"data"/"intelligence.db") as conn:
                data=read_snapshot(conn);h=state(conn,"current_hash");snap=next((s for s in history(conn) if s[0]==h),None)
                if not data or not snap or str(snap[2]).lower().startswith("synthetic"):raise RuntimeError("Actual local snapshot required")
                errors,_=validate(data)
                if errors:raise RuntimeError("Local validation failed")
            cfg=config()
            (work/"config.local.json").write_text(json.dumps({k:cfg[k] for k in ("command_profiles","positioning_dimensions","positioning_workflows","positioning_vista_commercial") if k in cfg}),encoding="utf-8")
        else:
            with connect(work/"data"/"intelligence.db") as conn:store(conn,sample(),source="Synthetic UX fixture",mark_synced=False)
        env=dict(os.environ)
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
                    page=browser.new_page(viewport={"width":1600,"height":1080},device_scale_factor=1,color_scheme="dark")
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
                        ready("Competitive Command Centre" if name=="Command Centre" else name)
                        top()
                    ready("Competitive Command Centre")
                    if not live:
                        chart=page.locator(".js-plotly-plot").first
                        chart.wait_for(timeout=20000)
                        style=chart.evaluate("""gd=>({
                          background:gd._fullLayout.plot_bgcolor,
                          firstSize:gd.data[0].marker.size,
                          ids:gd.data.slice(1).flatMap(t=>(t.customdata||[]).map(d=>d[0])),
                          labels:gd.data.slice(1).flatMap(t=>Array.from(t.text||[])),
                          points:gd.calcdata.slice(1).flatMap((ps,i)=>ps.map((p,j)=>({id:gd.data[i+1].customdata[j][0],x:p.x,y:p.y,label:gd.data[i+1].text[j]}))),
                          rivals:gd.data.slice(1).map(t=>({size:t.marker.size,opacity:t.marker.opacity,width:t.marker.line.width}))
                        })""")
                        assert style["background"].lower()=="#141f30",style
                        assert style["firstSize"]==36 and style["rivals"],style
                        assert set(style["ids"])=={"DEMO-P"+str(k) for k in range(1,44)},style
                        assert "Example Robotics" in style["labels"],style
                        assert any(not s for s in style["labels"]),style
                        assert all("%" not in s for s in style["labels"]),style
                        assert all(bool(p["label"])==(p["x"]>=(40 if p["y"]>=1.5 else 60)) for p in style["points"]),style
                        assert all(r["size"]==12 and r["opacity"]==1 and r["width"]>=1.5 for r in style["rivals"]),style
                    shot("01_Command_Centre")
                    for width,height in [(1280,800),(1920,1080)]:
                        page.set_viewport_size({"width":width,"height":height});page.wait_for_timeout(500)
                        top();shot("Landing_"+str(width)+"x"+str(height))
                    page.set_viewport_size({"width":1600,"height":1080});page.wait_for_timeout(500)
                    # Assert actual DOM reading order, independent of the number of optional charts.
                    order=page.get_by_role("heading").all_text_contents()
                    assert order.index("Technology × customer positioning") < order.index("Strategic benchmark") < order.index("Threat Watch") < order.index("Company Portfolio Coverage"),order
                    section("Threat Watch");shot("09_Threat_Watch")
                    section("Company Portfolio Coverage");shot("10_Company_Portfolio")
                    if not live:
                        plots=page.locator(".js-plotly-plot")
                        index=plots.evaluate_all("(plots)=>plots.findIndex(gd=>gd.data?.filter(t=>t.type==='bar').length===2 && gd.data[0].customdata?.length===43)")
                        assert index>=1,"Portfolio chart missing"
                        portfolio=plots.nth(index)
                        portfolio.wait_for(timeout=20000)
                        info=portfolio.evaluate("""gd=>({bg:gd._fullLayout.plot_bgcolor,bars:gd.data.filter(t=>t.type==="bar").length,ids:gd.data[0].customdata.map(d=>d[0]),second:gd.data[0].customdata[1]})""")
                        assert info["bg"].lower()=="#141f30" and info["bars"]==2 and len(set(info["ids"]))==43,info
                        portfolio.screenshot(path=str(out/"11_Company_Portfolio_Full.png"))
                        portfolio.locator(".barlayer .trace .point path").nth(1).click(force=True)
                        page.get_by_text(info["second"][1]+" — "+info["second"][9],exact=True).wait_for(timeout=15000)
                        assert page.get_by_text("Eight criterion attribution",exact=True).count()==1
                    top()
                    def map_point(pid,criterion=None,plot_index=0):
                        plot=page.locator(".js-plotly-plot").nth(plot_index)
                        plot.scroll_into_view_if_needed()
                        xy=plot.evaluate("""(gd,args)=>{for(let ti=0;ti<gd.data.length;ti++){const tr=gd.data[ti];for(let i=0;i<(tr.customdata||[]).length;i++){
                          const d=tr.customdata[i];if(d[0]===args[0] && (args[1]===null||d[1]===args[1])){
                            const pt=(gd.calcdata[ti]||[]).find(p=>p.i===i)||(gd.calcdata[ti]||[])[i];
                            if(!pt)return null;
                            const r=gd.getBoundingClientRect(),x=gd._fullLayout.xaxis,y=gd._fullLayout.yaxis;
                            const xy=[r.x+x._offset+x.l2p(pt.x),r.y+y._offset+y.l2p(pt.y)];
                            return xy.every(Number.isFinite)?xy:null;
                          }}}return null;}""",[pid,criterion])
                        if xy is None:raise RuntimeError("Requested chart point not present: "+pid)
                        page.mouse.click(*xy)
                    if live:
                        from command_engine import registry
                        from founder import summaries
                        rows=summaries(data)
                        for name in ["Connektica","Rapta","Dheera","iLEAN","AI4AIT"]:
                            r=rows[rows.Company.str.casefold().str.startswith("ai4ait")] if name=="AI4AIT" else rows[rows.Company.str.casefold()==name.casefold()]
                            if r.empty:raise RuntimeError("Acceptance company not found: "+name)
                            nav("Market Positioning")
                            # Use the displayed default map when possible; otherwise use
                            # the searchable profile directory (recorded as a limitation).
                            pid=r.iloc[0]["Product ID"]
                            plot=page.locator(".js-plotly-plot").first
                            present=plot.evaluate("(gd,p)=>gd.data.some(t=>(t.customdata||[]).some(d=>d[0]===p))",pid)
                            if present:
                                map_point(pid)
                                ready("Competitor Explorer")
                            else:
                                nav("Competitor Explorer")
                                search=page.get_by_placeholder("Search companies, products or technologies")
                                if not search.count():search=page.get_by_role("textbox").first
                                search.fill(name);search.press("Enter");page.wait_for_timeout(600)
                            page.get_by_role("heading",name=r.iloc[0].Company,exact=True).wait_for(timeout=15000)
                            top();shot("Profile_"+name)
                        nav("Competitor Explorer")
                    else:
                        map_point("DEMO-P1")
                        ready("Competitor Explorer")
                        page.get_by_role("heading",name="Example Robotics",exact=True).wait_for(timeout=10000)
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
                    if not live:
                        map_point("DEMO-P1","AV-CR-003")
                        ready("Competitor Explorer")
                        page.get_by_text("Physical configuration verification — Supported",exact=True).wait_for(timeout=15000)
                        nav("Competitive Advantage")
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
    (out/"README.txt").write_text("Actual browser screenshots of the v1.5.2 Streamlit app (dark mode).\n"+("Private actual local snapshot; do not publish.\n" if live else "All displayed companies, prices, deployments and competitor evidence are fictitious UI fixtures. Not a live 5PACE dataset or research result.\n"),encoding="utf-8")
    if live:
        from zipfile import ZipFile,ZIP_DEFLATED
        with ZipFile(out.parent/"5PACE_live_screenshots.zip","w",ZIP_DEFLATED) as z:
            for path in sorted(out.glob("*.png")):z.write(path,path.name)
            z.write(out/"README.txt","README.txt")

if __name__=="__main__":capture(Path(sys.argv[1] if len(sys.argv)>1 else "screenshots").resolve(),live="--live" in sys.argv[2:])
