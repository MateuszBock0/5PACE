"""Local-only advanced workflows and strategic exports."""
from __future__ import annotations
import html
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from chart_theme import plot, tokens, role_colors, action_colors, reference_marker, rival_marker, heatmap_colors, colors as chart_colors
from core import ROOT,DATA,config,connect,store,read_snapshot,validate,records,value,digest
from analytics import matrix
from product_intelligence import mappings,criterion_matrix,function_profile,target_ids,source_rows,CRITERIA,FUNCTIONS,MATURITY
from strategic import commercial_mcda,convergence,transitions,stale_evidence,opportunity_register,integration_candidates,CRITERIA as MCDA_CRITERIA
from filelock import FileLock,Timeout

def save_settings(changes):
    cfg=config()
    cfg.update(changes)
    path=ROOT/"config.local.json"
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg,indent=2),encoding="utf-8")
    tmp.replace(path)

def import_panel(st,demo_mode):
    st.subheader("Offline snapshot import")
    st.caption("Import a locally exported CIE snapshot JSON. It must match the schema and existing history. This never contacts Google Sheets or changes the source.")
    file=st.file_uploader("Snapshot JSON",type=["json"],disabled=demo_mode)
    if file and st.button("Validate and import snapshot",disabled=demo_mode):
        try:
            data=json.loads(file.getvalue())
            if not isinstance(data,dict) or any(not isinstance(v,dict) or not isinstance(v.get("headers"),list) or not isinstance(v.get("rows"),list) or any(not isinstance(r,dict) for r in v["rows"]) for v in data.values()):
                raise ValueError("Invalid CIE snapshot structure")
            if any(value(r,"Company ID").startswith("DEMO-") for r in records(data,"Companies")):
                raise ValueError("Synthetic demo snapshots cannot be imported as operational intelligence")
            DATA.mkdir(parents=True,exist_ok=True)
            with FileLock(str(DATA/"sync.lock"),timeout=0):
                with connect() as conn:
                    h=store(conn,data,source="Local JSON import",mark_synced=False)
            st.success("Imported "+h[:12]+"; refresh interface to open it.")
        except (ValueError,KeyError,TypeError,Timeout) as exc:
            st.error("Import rejected; previous data retained. "+str(exc)[:600])

def commercial_page(st,data,mat,cnames,cfg,show):
    st.divider()
    st.subheader("Multi-criteria commercial relevance scenario")
    st.caption("Illustrative decision model, not a calibrated probability or market-share ranking. Space deployment = 1; space offering/adoption signal/R&D = [0.5,1]; unknown space relevance = [0,1]. Commercial = 1; announced/research/internal/historical = [0,0.5]; unknown = [0,1]. Documented implementation = 1; reported = [0.5,1]; no implementation record = [0,1]. Price is not scored because price bases differ.")
    targets=[c for c in target_ids(data) if c in mat.columns]
    chosen=st.multiselect("Market capability proxies in commercial scenario",list(mat.columns),default=targets,format_func=cnames.get,key="mcda-targets")
    if not chosen:
        st.info("Select at least one capability proxy.")
        return
    weights={k:st.slider(k,0,10,int(cfg.get("commercial_weights",{}).get(k,5)),key="mcda-"+k) for k in MCDA_CRITERIA}
    if not sum(weights.values()):
        st.info("At least one criterion needs positive weight.")
        return
    out=commercial_mcda(data,mat[chosen],{c:1 for c in chosen},weights).sort_values("Lower",ascending=False)
    if out.empty: return
    fig=go.Figure(go.Scatter(x=out["Lower"],y=out["Product"],mode="markers",error_x={"type":"data","symmetric":False,"array":out["Uncertainty width"],"arrayminus":[0]*len(out)}))
    fig.update_layout(xaxis={"range":[0,1],"title":"Scenario lower–upper bound"},height=max(400,25*len(out)))
    plot(st,fig,use_container_width=True)
    show(out,"commercial_mcda")
    st.caption("A wide interval indicates insufficient evidence. Lower-bound order is not a definitive threat ranking.")
    if st.button("Compare criterion-weight scenarios"):
        rows=[]
        for key in MCDA_CRITERIA:
            scenario={k:(2*v if k==key else v) for k,v in weights.items()}
            df=commercial_mcda(data,mat[chosen],{c:1 for c in chosen},scenario)
            df["Scenario"]="Double "+key
            df["Lower-bound rank"]=df["Lower"].rank(ascending=False,method="min")
            rows.append(df[["Scenario","Product ID","Lower","Upper","Lower-bound rank"]])
        show(pd.concat(rows,ignore_index=True),"commercial_sensitivity")

def evolution_panel(st,before,after,selected_caps,cnames,show):
    st.subheader("Evidence-state transitions")
    show(transitions(before,after),"assessment_transitions")
    st.subheader("Convergence on a fixed comparison cohort")
    chosen=st.multiselect("Target capabilities for historical comparison",selected_caps,default=[c for c in target_ids(after) if c in selected_caps],format_func=cnames.get,key="evolution-targets")
    if chosen:
        out=convergence(before,after,chosen)
        show(out,"convergence")
        if not out.empty:
            fig=px.scatter(out,x="Baseline lower",y="Current lower",hover_name="Product ID",color="Jointly determinate",range_x=[0,1],range_y=[0,1],title="Change in recorded functional overlap")
            fig.add_shape(type="line",x0=0,y0=0,x1=1,y1=1,line={"dash":"dot"})
            plot(st,fig,use_container_width=True)
        st.caption("Common products and capabilities only. A positive change can reflect newly discovered evidence rather than a product release. Jointly determinate changes are reported separately.")

def research_panel(st,data,cfg,show):
    st.subheader("Source review queue")
    days=st.number_input("Review age threshold (days)",min_value=1,max_value=3650,value=int(cfg.get("research_stale_days",90)))
    stale=stale_evidence(data,int(days))
    show(stale,"stale_evidence")
    st.caption("Review due is a research workflow flag, not a conclusion that evidence is obsolete.")

def product_page(st,data,mat,pnames,cnames,cfg,show,demo_mode):
    st.header("AIT-VISTA product intelligence")
    if CRITERIA not in data or FUNCTIONS not in data:
        st.info("This snapshot predates the two AIT-VISTA mapping worksheets. Synchronise or import a newer snapshot.")
        return
    f=mappings(data)
    st.caption("Traceability: system function → consolidated capability → product comparison criterion → market capability proxies. Source sheets are read-only. Proxy evidence is not direct proof of criterion fulfilment or AIT-VISTA implementation maturity.")
    c1,c2,c3=st.columns(3)
    c1.metric("System functions",len(f))
    c2.metric("Product criteria",len(source_rows(data,CRITERIA)))
    c3.metric("Unmapped functions",int((f["Mapping status"]=="Unmapped").sum()))
    show(f,"function_traceability")
    if mat.empty: return
    pid=st.selectbox("Compare competitor",list(mat.index),format_func=pnames.get)
    # Always use all market capabilities for the source mapping; global category filters do not truncate traceability.
    full=matrix(data,[pid])
    criteria=criterion_matrix(data,full)
    show(criteria,"criterion_proxies")
    profile=function_profile(data,full,pid,cfg.get("function_maturity",{}))
    show(profile,"function_comparison")
    if not f.empty:
        st.subheader("Local function maturity register")
        with st.form("function-maturity"):
            fid=st.selectbox("System function",list(f["Function ID"]))
            maturity=st.selectbox("Maturity",sorted(MATURITY),index=sorted(MATURITY).index("Implemented"))
            submit=st.form_submit_button("Save local maturity",disabled=demo_mode)
            if submit:
                values=config().get("function_maturity",{}); values[fid]=maturity
                save_settings({"function_maturity":values})
                st.success("Saved locally. Refresh interface to update profile.")
        st.caption("Listed functions are Implemented by default under the product owner declaration; optional local overrides remain available. This is not independent verification.")

def strategic_page(st,data,mat,cnames,cfg,show,demo_mode):
    st.header("Strategic intelligence")
    st.caption("Evidence-backed hypotheses and diligence tasks, not autonomous business decisions or evidence of customer demand.")
    choices=list(mat.columns)
    default=[c for c in target_ids(data) if c in choices] or [c for c in cfg.get("priority_capabilities",[]) if c in choices]
    targets=st.multiselect("Strategic capability targets",choices,default=default,format_func=cnames.get)
    if not targets:
        st.info("Select target capabilities to evaluate.")
        return
    opportunities=opportunity_register(data,mat,targets,cfg.get("demand_validation",{}))
    show(opportunities,"strategic_opportunities")
    st.subheader("Possible suppliers and integration candidates")
    show(integration_candidates(data,mat,targets),"integration_candidates")
    st.caption("Matches are functional proxies; no integration compatibility, partnership or willingness to sell is assumed. Assess licensing, security, API, cost and effort before a build-versus-buy decision.")
    st.subheader("Local customer-demand evidence")
    with st.form("demand-validation"):
        cid=st.selectbox("Capability",targets,format_func=cnames.get)
        status=st.selectbox("Demand evidence status",["Unvalidated","Validated"])
        ref=st.text_input("Reference to customer validation evidence (interview / survey / record ID)")
        submitted=st.form_submit_button("Save local demand assessment",disabled=demo_mode)
        if submitted:
            if status=="Validated" and not ref.strip():
                st.error("A validation reference is required.")
            else:
                d=config().get("demand_validation",{}); d[cid]={"status":status,"reference":ref.strip()}
                save_settings({"demand_validation":d})
                st.success("Saved locally. Refresh to update the register.")
    st.caption("Demand status is user-declared, not independently validated by the application.")

def strategic_report(data,mat,cfg,demo_mode=False):
    targets=[c for c in target_ids(data) if c in mat.columns] or [c for c in cfg.get("priority_capabilities",[]) if c in mat.columns]
    title="5PACE Strategic Intelligence"+(" — SYNTHETIC DEMO" if demo_mode else "")
    sections=[("System function traceability",mappings(data)),("Opportunity hypotheses",opportunity_register(data,mat,targets,cfg.get("demand_validation",{}))),("Integration candidates",integration_candidates(data,mat,targets)),("Stale evidence",stale_evidence(data,cfg.get("research_stale_days",90)))]
    doc="<!doctype html><html><head><meta charset='utf-8'><title>"+html.escape(title)+"</title><style>body{font:14px system-ui;margin:32px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:5px;vertical-align:top}</style></head><body><h1>"+html.escape(title)+"</h1><p>Snapshot "+html.escape(digest(data))+"</p>"
    for name,df in sections:
        doc+="<h2>"+html.escape(name)+"</h2>"+df.to_html(index=False,escape=True)
    doc+="<p>Proxy overlap is not implementation maturity. No competitive gap is proof of demand. Customer validation and integration feasibility require separate evidence.</p></body></html>"
    return doc.encode("utf-8")
