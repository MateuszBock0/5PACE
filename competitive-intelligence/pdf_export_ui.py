"""Explicit report export panel. No writes unless the user downloads a PDF."""
from core import value,digest
from founder import summaries,strategic_map_cohort,DEFAULT_MAP_SCOPE
from threat_watch import selected_criteria,threat_cohort
from command_engine import registry
from product_intelligence import CRITERIA
from decision import dataset_label
from pdf_reports import REPORTS,MIME,render_report
from threat_watch import report_provenance

def export_panel(st,data,cfg,snapshots,current,head,demo,primary,location="sidebar"):
    if data is None:return
    source=next((s[2] for s in snapshots if s[0]==current),"")
    stamp=next((s[1] for s in snapshots if s[0]==current),"")
    mode=dataset_label(data,source,current,head,demo)
    stamp,h,source=report_provenance(data,mode,stamp,digest(data),source)
    if demo:stamp="Not applicable (synthetic)"
    k="pdf-"+location
    container=st.sidebar.expander("Export reports (PDF)") if location=="sidebar" else st.container(border=True)
    with container:
        st.markdown("**Export panel**")
        defaults={"Command Centre":"Strategic overview","Competitor Explorer":"Competitor profile","Market Positioning":"Market positioning & workflow","Competitive Advantage":"Competitive advantage","Intelligence Monitor":"Intelligence monitor"}
        kind=st.selectbox("Report",REPORTS,index=REPORTS.index(defaults.get(primary,"Strategic overview")),key=k+"-type")
        r=summaries(data)
        names={x["Product ID"]:x["Company"]+" / "+x["Product"] for x in r.to_dict("records")} if not r.empty else {}
        scope=st.selectbox("Product scope",[DEFAULT_MAP_SCOPE,"Current view selection","Select products","All products","Threat Watch selection","Strategic + research"],index=1 if primary in {"Competitor Explorer","Market Positioning","Competitive Advantage"} else 0,key=k+"-scope")
        if scope=="Threat Watch selection":
            ids=st.session_state.get("threat-products",threat_cohort(data,r)["Product ID"].tolist() if names else [])
        elif scope=="Select products":
            ids=st.multiselect("Products to include",list(names),format_func=names.get,key=k+"-products")
        elif scope=="All products":ids=list(names)
        elif scope=="Current view selection":
            ss=st.session_state
            if primary=="Competitor Explorer":ids=[ss.get("founder-product-"+str(ss.get("founder_company","")))]
            elif primary=="Market Positioning":ids=ss.get("founder-map-products",[])
            elif primary=="Competitive Advantage":ids=ss.get("founder-adv-products",[])
            elif primary=="Command Centre":ids=strategic_map_cohort(r,ss.get("landing-map-scope",DEFAULT_MAP_SCOPE))["Product ID"].tolist() if names else []
            else:ids=list(names)
            ids=[i for i in ids if i in names]
        else:ids=strategic_map_cohort(r,scope)["Product ID"].tolist() if names else []
        ids=[i for i in ids if i in names]
        crit_scope=st.selectbox("Threat / comparison criteria",["Current Threat Watch","Strategic criteria","All criteria"],key=k+"-criteria")
        cids=list(registry(data,CRITERIA,"Criterion ID")) if crit_scope=="All criteria" or (crit_scope=="Current Threat Watch" and st.session_state.get("threat-all",False)) else selected_criteria(data)
        actual_scope=st.session_state.get("landing-map-scope",DEFAULT_MAP_SCOPE) if scope=="Current view selection" and primary=="Command Centre" else scope
        st.caption(f"{len(cids)} criteria in Threat Watch and strategic comparison; profile and QA retain full scope.")
        st.caption(f"{len(ids)} products · {mode}. PDF uses this snapshot and explicit scope, not live data. QA checks the entire snapshot.")
        signature=(h,mode,stamp,source,kind,tuple(ids),tuple(cids),actual_scope,repr(cfg.get("command_profiles",{})))
        if st.button("Generate PDF",key=k+"-generate",disabled=(not ids and kind!="QA & data integrity")):
            try:
                payload=render_report(data,cfg,kind,ids,mode,stamp,h,source,criterion_ids=cids,map_scope=actual_scope)
                st.session_state[k+"-prepared"]=(signature,payload)
            except Exception as exc:st.error("PDF export failed: "+type(exc).__name__+": "+str(exc)[:180])
        prepared=st.session_state.get(k+"-prepared")
        if prepared and prepared[0]==signature:
            filename="5PACE_"+kind.replace(" & ","_").replace(" ","_")+"_"+h[:12]+".pdf"
            st.download_button("Download PDF",prepared[1],file_name=filename,mime=MIME,key=k+"-download")
        st.caption("Local download only. Existing Excel, CSV and HTML exports remain available.")
