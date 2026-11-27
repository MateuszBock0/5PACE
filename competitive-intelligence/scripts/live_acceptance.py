"""Run against the authorised local SQLite snapshot, without network or source writes.
Only a temporary SQLite backup is used. Report is private under reports/.
"""
import json,sys,sqlite3,tempfile,os
from contextlib import closing
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
        with closing(sqlite3.connect(core.DB.as_uri()+"?mode=ro",uri=True)) as source,closing(sqlite3.connect(path)) as target:source.backup(target)
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
            from founder import strategic_map_cohort,DEFAULT_MAP_SCOPE
            expected={r["Product ID"] for _,r in rows.iterrows() if r["Recorded overlap fraction"]>=.6 or (r["Recorded overlap fraction"]>=.4 and r["Customer position"] in {"Space AIT target segment","Space AIT implementation case"})}
            assert set(strategic_map_cohort(rows)["Product ID"])==expected
            assert set(strategic_map_cohort(rows,"All products")["Product ID"])==set(products)
            assert set(app.session_state["landing-products"])==set(products)
            assert set(app.session_state["threat-products"])==expected
            from company_portfolio import portfolio_data
            pf,pdets=portfolio_data(data,rows)
            assert set(app.session_state["portfolio-company-ids"])==set(rows["Company ID"])
            assert (pf["Portfolio coverage"]>=pf["Best single product coverage"]).all()
            assert (pf["Portfolio coverage"]<=1).all()
            app.selectbox(key="landing-map-scope").set_value(DEFAULT_MAP_SCOPE).run();check("Map scope independence")
            assert set(app.session_state["landing-products"])==expected and set(app.session_state["threat-products"])==expected
            app.button(key="landing-map-scope-reset").click().run();check("Map reset independence")
            assert set(app.session_state["landing-products"])==set(products) and set(app.session_state["threat-products"])==expected
            from space_research import priority_queue
            q=priority_queue(data,core.config(),h,snap[1])
            assert not q.duplicated(["Product ID","Criterion ID"]).any()
            companies=registry(data,"Companies","Company ID")
            report={"Snapshot hash":h,"Capture UTC":snap[1],"Source":snap[2],"Mode":mode,
                    "Validation errors":errors,"Validation warnings":warnings,"Default map IDs":sorted(products),"Strategic core IDs":sorted(expected),"Portfolio companies":len(pf),"Portfolio-only exposure":pf[pf["Portfolio flag"]=="Portfolio-only exposure"]["Company ID"].tolist(),"All product IDs":sorted(products),"Profiles":[],"Workspaces":[],"Browser clicks":"Not tested by AppTest; verify with live browser capture."}
            for name in ["Connektica","Rapta","Dheera","iLEAN","AI4AIT"]:
                ids=[c for c in search_companies(data,name) if core.value(companies[c],"Company Name").casefold()==name.casefold() or (name=="AI4AIT" and core.value(companies[c],"Company Name").casefold().startswith("ai4ait"))]
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
            for view in ["Command Centre","Market Positioning","Competitive Advantage","Company Watchlist","Intelligence Monitor","Competitor Explorer","Advanced Analytics"]:
                app.sidebar.radio[0].set_value(view).run();check(view);report["Workspaces"].append(view)
                if view=="Company Watchlist":
                    from company_watchlist import watchlist
                    w,_=watchlist(data)
                    assert set(app.session_state["watchlist-company-ids"])==set(w["Company ID"])
                    report["Watchlist companies"]=len(w)
                if view=="Market Positioning":
                    assert set(app.session_state["founder-map-products"])==expected
                    assert set(app.session_state["workflow-products"])==expected
                if view=="Competitive Advantage":
                    assert set(app.session_state["founder-adv-products"])==expected
            from pdf_reports import REPORTS,render_report
            from threat_watch import report_provenance
            report["PDF reports"]=[]
            for kind in REPORTS:
                payload=render_report(data,core.config(),kind,mode=mode,captured=snap[1],snapshot_hash=h,source=snap[2])
                assert payload.startswith(b"%PDF-") and b"%%EOF" in payload[-100:]
                file=out.parent/("acceptance_"+kind.replace(" ","_").replace("&","and")+".pdf")
                file.write_bytes(payload)
                report["PDF reports"].append({"Report":kind,"Bytes":len(payload),"File":file.name})
            report["PDF visual QA"]="Not covered by PDF signature tests; inspect rendered pages."
            assert core.digest(data)==h
            with original(path) as conn:assert core.state(conn,"current_hash")==h
            report["Status"]="PASS: actual-snapshot AppTest and callback contracts; native browser and local sync separate."
            out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(json.dumps(report,ensure_ascii=False,indent=2));print("Report:",out)
        finally:core.connect=original

if __name__=="__main__":run()
