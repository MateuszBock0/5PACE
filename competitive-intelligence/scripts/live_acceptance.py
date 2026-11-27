"""Run against the authorised local SQLite snapshot, without network or source writes.
Only a temporary SQLite backup is used. Report is private under reports/.
"""
import json,sys,sqlite3,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import core
from command_engine import registry,direct_current
from founder import summaries,profile_records,search_companies,brief_criteria
from decision import dataset_label
from founder_ui import chart_route
from streamlit.testing.v1 import AppTest

def run():
    if not core.DB.exists():raise SystemExit("No local database. Synchronise first.")
    out=ROOT/"reports"/"live-acceptance.json"
    out.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cie-acceptance-") as temp:
        path=Path(temp)/"intelligence.db"
        with sqlite3.connect(core.DB.as_uri()+"?mode=ro",uri=True) as source,sqlite3.connect(path) as target:source.backup(target)
        original=core.connect
        with original(path) as conn:
            data=core.read_snapshot(conn)
            h=core.state(conn,"current_hash");head=core.state(conn,"latest_hash")
            snap=next((s for s in core.history(conn) if s[0]==h),None)
        if not data or not snap:raise SystemExit("No validated local snapshot.")
        mode=dataset_label(data,snap[2],h,head)
        if mode.startswith("SYNTHETIC"):raise SystemExit("Synthetic data cannot pass live acceptance.")
        errors,warnings=core.validate(data)
        if errors:raise SystemExit("Validation failed: "+str(errors))
        core.connect=lambda:original(path)
        try:
            app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=75).run()
            def check(label):
                if app.exception:raise RuntimeError(label+": "+str([e.message for e in app.exception]))
            check("Landing")
            assert any(mode in c.value for c in app.caption),"Incorrect dataset indicator"
            rows=summaries(data);products=registry(data,"Products","Product ID")
            companies=registry(data,"Companies","Company ID")
            report={"Snapshot hash":h,"Capture UTC":snap[1],"Source":snap[2],"Mode":mode,
                    "Validation errors":errors,"Validation warnings":warnings,"Profiles":[],"Workspaces":[],"Browser clicks":"Not tested by AppTest; verify with live browser capture."}
            for name in ["Connektica","Rapta","Dheera","iLEAN"]:
                ids=[c for c in search_companies(data,name) if core.value(companies[c],"Company Name").casefold()==name.casefold()]
                if len(ids)!=1:raise RuntimeError("Profile missing or ambiguous: "+name)
                cid=ids[0];r=rows[rows["Company ID"]==cid].iloc[0];pid=r["Product ID"]
                # The same callback contract used by real map selections.
                class UI:pass
                ui=UI();ui.session_state={"chart":{"selection":{"points":[{"customdata":[pid]}]}}}
                chart_route(ui,"chart",data,"product")
                assert ui.session_state["founder_product_pending"]==pid
                assert ui.session_state["founder_company_pending"]==cid
                app.sidebar.radio[0].set_value("Competitor Explorer").run();check(name)
                app.text_input(key="founder-search").set_value(name).run();check(name+" search")
                assert app.selectbox(key="founder_company").value==cid
                assert app.selectbox(key="founder-product-"+cid).value==pid
                for section in ["Overview","Products","Compare","Deployments","Pricing","Evidence","Timeline"]:
                    app.radio(key="profile-section").set_value(section).run();check(name+" "+section)
                report["Profiles"].append({"Company":name,"Product":core.value(products[pid],"Product Name"),"Sections":"7/7","Customer position":r["Customer position"],"Procurement":r["Procurement"],"Direct active pairs":sum(p==pid for p,c in direct_current(data))})
            for view in ["Command Centre","Market Positioning","Competitive Advantage","Intelligence Monitor","Competitor Explorer","Advanced Analytics"]:
                app.sidebar.radio[0].set_value(view).run();check(view);report["Workspaces"].append(view)
            assert core.digest(data)==h
            with original(path) as conn:assert core.state(conn,"current_hash")==h
            report["Status"]="PASS: actual-snapshot AppTest and callback contracts; native browser and local sync separate."
            out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(json.dumps(report,ensure_ascii=False,indent=2));print("Report:",out)
        finally:core.connect=original

if __name__=="__main__":run()
