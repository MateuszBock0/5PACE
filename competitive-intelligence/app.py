"""5PACE Competitive Intelligence Engine — local browser interface."""
from __future__ import annotations
import html
import os
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from chart_theme import plot, tokens, role_colors, action_colors, reference_marker, rival_marker, heatmap_colors, colors as chart_colors
import streamlit as st
import networkx as nx
from core import ROOT, config, connect, read_snapshot, history, state, restore, diff, records, value, due, digest, validate, canonical
from analytics import (frame, current_assessments, active_capabilities, matrix, coverage, score_bounds,
                       sensitivity, research_gaps, similarity, clusters, graph, capability_gaps, DISPLAY)
from demo import fixture
from command_ui import command_page
from excel_archive import download_analysis, workbook_bytes, MIME
from archive_ui import archive_page
from founder_ui import PRIMARY, founder_page
from decision import dataset_label
from pdf_export_ui import export_panel
from advanced_ui import (commercial_page, product_page, strategic_page, evolution_panel, research_panel, import_panel)

st.set_page_config(page_title="5PACE | Competitive Intelligence", layout="wide")
st.markdown("**5PACE / INTELLIGENCE**")
st.caption("v1.4.6-rc1 · Offline-first competitive intelligence · Evidence-aware analytics · Read-only Google Sheets")
cfg=config()
with connect() as conn:
    data=read_snapshot(conn)
    last=state(conn,"last_successful_sync")
    head=state(conn,"latest_hash")
    current=state(conn,"current_hash")
    stale=due(conn,float(cfg["refresh_interval_hours"]))
    snapshots=history(conn)
    logs=conn.execute("SELECT at,status,detail FROM sync_log ORDER BY rowid DESC LIMIT 30").fetchall()
demo_mode=st.sidebar.checkbox("Synthetic demo mode",value=False,help="Never saved into the live database.")
if demo_mode:
    data=fixture()
    st.warning("SYNTHETIC DEMO — all displayed products and observations are fictitious.")
elif str(next((s[2] for s in snapshots if s[0]==current),"")).lower().startswith("synthetic"):
    st.warning("SYNTHETIC UX PREVIEW — fictitious companies and evidence; not live research.")
elif data is None:
    st.info("No local dataset yet. Configure read-only Google OAuth and run a first synchronisation. Once downloaded, the application works offline.")
elif current!=head:
    st.warning("You are viewing a restored historical snapshot. Sync will select the latest source dataset again.")
source=next((s[2] for s in snapshots if s[0]==current),"")
st.caption("DATA MODE: "+dataset_label(data,source,current,head,demo_mode)+" · "+(next((s[1] for s in snapshots if s[0]==current),"No capture") if not demo_mode else "Fictitious fixture"))
st.sidebar.caption("Last successful source sync (UTC)")
st.sidebar.write("Not applicable (synthetic)" if demo_mode else last or "Never")
st.sidebar.caption("Source check age: "+("not applicable" if demo_mode else "due" if stale else "fresh"))
st.sidebar.caption("Snapshot capture and source check are distinct; unchanged source content retains its capture time.")
if st.sidebar.button("Refresh interface"):
    st.rerun()
if st.sidebar.button("Sync data now",disabled=demo_mode):
    subprocess.Popen([sys.executable,str(ROOT/"sync.py"),"--force"],cwd=str(ROOT))
    st.sidebar.info("Sync started in a separate process. Refresh interface to inspect its result.")
PAGES=["Command Centre","Overview","Companies & products","Capability matrix","Evidence & deployments","Landscape & threats","Knowledge graph","Research gaps","Similarity & clustering","Technology gaps","History & evolution","Product intelligence","Strategic intelligence","Reports","Excel Archive","Synchronisation"]
primary=st.sidebar.radio("Workspace",PRIMARY,index=0 if data is not None else len(PRIMARY)-1,key="founder_workspace")
if primary=="Advanced Analytics":
    page=st.sidebar.radio("Advanced workspace",PAGES,index=0 if data is not None else len(PAGES)-1)
    if data is not None:export_panel(st,data,cfg,snapshots,current,head,demo_mode,page)
else:
    if data is not None:
        founder_page(st,primary,data,cfg,snapshots,current,demo_mode)
        export_panel(st,data,cfg,snapshots,current,head,demo_mode,primary)
    else: st.info("Open Advanced Analytics → Synchronisation to configure the source, or Excel Archive to inspect existing snapshots.")
    st.stop()

def show(df, key=None):
    st.dataframe(df,use_container_width=True,hide_index=True)
    if key and isinstance(df,pd.DataFrame):
        st.download_button("Export CSV",df.to_csv(index=False).encode("utf-8"),file_name=key+".csv",key="csv-"+key,mime="text/csv")
        download_analysis(st,df,"app-"+key,key)

def label_dict(data,tab,idcol,namecol):
    return {value(r,idcol):f"{value(r,namecol)} · {value(r,idcol)}" for r in records(data,tab)}

if page=="Excel Archive":
    archive_page(st,snapshots,head,demo_mode)
    st.stop()

if page=="Synchronisation":
    st.header("Synchronisation centre")
    st.write("Source access is strictly read-only. Code updates and source-data refreshes are separate.")
    st.write({"refresh_interval_hours":cfg["refresh_interval_hours"],"source_configured":bool(cfg["spreadsheet_id"]),
              "last_successful_sync_utc":last,"current_hash":current,"latest_hash":head,"distinct_snapshots":len(snapshots)})
    st.subheader("Local configuration")
    st.caption("Stored in ignored config.local.json; never committed to Git. Do not paste OAuth secrets into this field.")
    with st.form("configuration"):
        sid=st.text_input("Google Sheets spreadsheet ID",value=cfg["spreadsheet_id"],type="password")
        interval=st.number_input("Refresh interval (hours)",min_value=1,max_value=168,value=int(cfg["refresh_interval_hours"]))
        if st.form_submit_button("Save local settings"):
            cfg.update({"spreadsheet_id":sid.strip(),"refresh_interval_hours":int(interval)})
            p=ROOT/"config.local.json"; tmp=p.with_suffix(".tmp")
            tmp.write_text(json.dumps(cfg,indent=2),encoding="utf-8"); tmp.replace(p)
            st.success("Local settings saved.")
    st.caption("For first authorisation, follow README.md and run AUTHORISE_WINDOWS.bat. Then run SYNC_NOW.bat.")
    import_panel(st,demo_mode)
    st.subheader("Synchronisation log")
    show(pd.DataFrame(logs,columns=["UTC","Status","Detail"]))
    if data is not None:
        st.subheader("Local dataset validation")
        errors,warnings=validate(data)
        st.write({"errors":errors,"warnings":warnings})
    st.stop()
if data is None:
    st.stop()

if page=="Command Centre":
    command_page(st,data,cfg,demo_mode,snapshots,current)
    st.stop()

co=frame(data,"Companies"); pro=frame(data,"Products"); cap=frame(data,"Capabilities")
a=frame(data,"Capability Assessment"); latest=current_assessments(data)
pnames=label_dict(data,"Products","Product ID","Product Name")
cnames=label_dict(data,"Capabilities","Capability ID","Capability Name")
conames=label_dict(data,"Companies","Company ID","Company Name")
active=active_capabilities(data); cap_ids=[value(r,"Capability ID") for r in active]
categories=sorted({value(r,"Category ID") for r in active})
selected_roles=st.sidebar.multiselect("Competition type",sorted({value(r,"Competition Type") for r in records(data,"Products") if value(r,"Competition Type")}),default=[])
selected_products=[value(r,"Product ID") for r in records(data,"Products") if not selected_roles or value(r,"Competition Type") in selected_roles]
selected_categories=st.sidebar.multiselect("Capability categories",categories,default=[])
selected_caps=[value(r,"Capability ID") for r in active if not selected_categories or value(r,"Category ID") in selected_categories]
mat=matrix(data,selected_products,selected_caps)
stats=coverage(mat)
st.sidebar.caption(f"Filtered: {len(selected_products)} products · {len(selected_caps)} capabilities")
if not selected_products or not selected_caps:
    st.warning("No records match the active filters.")
    st.stop()

if page=="Overview":
    st.header("Intelligence overview")
    cols=st.columns(6)
    for col,(name,tab) in zip(cols,[("Companies","Companies"),("Products","Products"),("Capabilities","Capabilities"),("Assessments","Capability Assessment"),("Deployments","Deployments"),("Commercial","Commercial Intelligence")]):
        col.metric(name,len(records(data,tab)))
    st.caption("Counts above refer to the full snapshot. Charts and coverage below use the selected filters.")
    x,y,z=st.columns(3)
    x.metric("Assessment coverage",f"{stats['coverage']:.1%}")
    y.metric("Determinate pairs",stats["determinate"])
    z.metric("Unassessed pairs",stats["pairs"]-stats["assessed"])
    st.progress(stats["coverage"])
    if not latest.empty:
        filtered=latest[latest["Product ID"].isin(selected_products)&latest["Capability ID"].isin(selected_caps)]
        left,right=st.columns(2)
        for c,field,title in [(left,"Status","Availability"),(right,"Evidence Level","Strongest recorded evidence per pair")]:
            counts=filtered[field].value_counts().rename_axis(field).reset_index(name="Count")
            plot(c,px.bar(counts,x="Count",y=field,orientation="h",title=title),use_container_width=True)
    st.subheader("Latest recorded observations")
    obs=frame(data,"Observations")
    if "Date added (ISO)" in obs: obs=obs.sort_values("Date added (ISO)",ascending=False)
    show(obs.head(30),"observations")
elif page=="Companies & products":
    st.header("Company and product explorer")
    co_id=st.selectbox("Company",list(conames),format_func=conames.get)
    show(co[co["Company ID"]==co_id].T.reset_index().rename(columns={"index":"Field"}))
    ids=pro.loc[(pro["Company ID"]==co_id)&pro["Product ID"].isin(selected_products),"Product ID"].tolist()
    show(pro[pro["Product ID"].isin(ids)],"company_products")
    if ids:
        pid=st.selectbox("Product",ids,format_func=pnames.get)
        st.subheader("Product profile")
        show(pro[pro["Product ID"]==pid].T.reset_index().rename(columns={"index":"Field"}))
        show(latest[latest["Product ID"]==pid],"product_capabilities")
        st.subheader("Assessment history and evidence")
        show(a[a["Product ID"]==pid],"product_evidence")
    st.subheader("Company observations")
    show(frame(data,"Observations").query("`Company ID` == @co_id"),"company_observations")
elif page=="Capability matrix":
    st.header("Product–capability matrix")
    st.caption("Grey = unassessed. Unknown = investigated but inconclusive. Conflicting active reviews are shown as disputed.")
    chosen=st.multiselect("Products to compare",selected_products,default=selected_products[:min(12,len(selected_products))],format_func=pnames.get)
    if chosen:
        m=mat.loc[chosen]
        code={v:i for i,v in enumerate(DISPLAY)}
        colors=["#404b5f","#9ba2af","#b95155","#7898cc","#c8a35c","#389776","#666666","#d578c7","#8d83b9"]
        scale=[]
        for i,c in enumerate(colors): scale.extend([[i/len(colors),c],[(i+1)/len(colors),c]])
        fig=go.Figure(go.Heatmap(z=m.apply(lambda s:s.map(code)).to_numpy(),x=[cnames[c] for c in m.columns],y=[pnames[p] for p in m.index],zmin=-.5,zmax=len(colors)-.5,colorscale=scale,text=m.to_numpy(),hovertemplate="%{y}<br>%{x}<br>%{text}<extra></extra>",colorbar={"tickmode":"array","tickvals":list(range(len(colors))),"ticktext":DISPLAY}))
        fig.update_layout(height=max(420,30*len(chosen)+180))
        plot(st,fig,use_container_width=True)
        show(m.rename(index=pnames,columns=cnames).rename_axis("Product").reset_index(),"capability_matrix")
        pid=st.selectbox("Inspect product",chosen,format_func=pnames.get)
        cid=st.selectbox("Inspect capability",selected_caps,format_func=cnames.get)
        st.write("Current status:",m.loc[pid,cid])
        show(a[(a["Product ID"]==pid)&(a["Capability ID"]==cid)],"pair_evidence")
elif page=="Evidence & deployments":
    st.header("Evidence and commercial intelligence")
    tab=st.selectbox("Register",["Capability Assessment","Deployments","Commercial Intelligence","Observations","Key Competitors","To be Confirmed","Archive","Notes","Main"])
    df=frame(data,tab)
    if "Product ID" in df: df=df[df["Product ID"].isin(selected_products)]
    query=st.text_input("Filter all columns (literal text)")
    if query and not df.empty:
        df=df[df.astype(str).apply(lambda c:c.str.contains(query,case=False,regex=False)).any(axis=1)]
    show(df,tab.lower().replace(" ","_"))
    st.caption("Deployment and price records are shown with their source limitations; currencies and price bases are not combined.")
elif page=="Landscape & threats":
    st.header("Competitive landscape and uncertainty")
    st.caption("Weighted functional overlap bounds, not a probability of commercial threat. Unknown, proposed, announced and disputed pairs contribute an interval [0, 1]. Partial support = 0.5 by modelling convention. Not applicable is excluded.")
    target=st.multiselect("Capabilities defining the comparison scenario",selected_caps,default=[c for c in cfg.get("priority_capabilities",[]) if c in selected_caps],format_func=cnames.get)
    if not target:
        st.info("Select capabilities relevant to the strategic scenario. No AIT-VISTA functionality is assumed.")
    else:
        weight_by_cat={cat:st.slider(f"{cat} weight",0,10,5,key="weight-"+cat) for cat in categories if any(value(r,"Category ID")==cat and value(r,"Capability ID") in target for r in active)}
        weights={value(r,"Capability ID"):weight_by_cat.get(value(r,"Category ID"),0) for r in active if value(r,"Capability ID") in target}
        s=score_bounds(mat[target],weights)
        s["Product"]=s["Product ID"].map(pnames)
        if "Space Industry Applicability" in pro:
            s=s.merge(pro[["Product ID","Space Industry Applicability"]],on="Product ID",how="left")
            color="Space Industry Applicability"
        else: color=None
        s["Uncertainty width"]=s["Upper"]-s["Lower"]
        plot(st,px.scatter(s,x="Lower",y="Known weight",color=color,hover_name="Product",hover_data=["Upper"],range_x=[0,1],range_y=[0,1],title="Evidence-backed overlap vs assessed weight"),use_container_width=True)
        plot=s.dropna(subset=["Lower"]).sort_values("Lower")
        fig=go.Figure(go.Scatter(x=plot["Lower"],y=plot["Product"],mode="markers",error_x={"type":"data","symmetric":False,"array":plot["Uncertainty width"],"arrayminus":[0]*len(plot)}))
        fig.update_layout(xaxis={"range":[0,1],"title":"Lower–upper overlap bounds"},height=max(380,len(plot)*23))
        plot(st,fig,use_container_width=True)
        show(s.sort_values("Lower",ascending=False),"threat_bounds")
        if st.button("Run weight sensitivity (250 scenarios)"):
            ss=sensitivity(mat[target],weights).merge(s[["Product ID","Product"]],on="Product ID",how="left")
            show(ss,"sensitivity")
        st.caption("Commercial threat judgement additionally requires comparable customer adoption, market fit and price evidence. The application does not invent those scores.")
    commercial_page(st,data,mat,cnames,cfg,show)
elif page=="Knowledge graph":
    st.header("Knowledge graph")
    ids=st.multiselect("Products",selected_products,default=selected_products[:min(5,len(selected_products))],format_func=pnames.get)
    evidence=st.checkbox("Include assessment and evidence nodes")
    g=graph(data,ids,evidence)
    if len(g):
        if len(g)>350:
            st.warning("Select fewer products to keep the graph readable.")
        else:
            pos=nx.spring_layout(g,seed=42)
            ex=[];ey=[]
            for u,v in g.edges:
                ex.extend([pos[u][0],pos[v][0],None]);ey.extend([pos[u][1],pos[v][1],None])
            fig=go.Figure(go.Scatter(x=ex,y=ey,mode="lines",line={"color":"#52627a","width":1},hoverinfo="skip",showlegend=False))
            for kind in sorted({d["kind"] for _,d in g.nodes(data=True)}):
                nodes=[n for n,d in g.nodes(data=True) if d["kind"]==kind]
                fig.add_trace(go.Scatter(x=[pos[n][0] for n in nodes],y=[pos[n][1] for n in nodes],mode="markers+text" if len(g)<40 else "markers",text=[g.nodes[n]["label"] for n in nodes],hovertext=nodes,hoverinfo="text",name=kind,textposition="top center",marker={"size":13}))
            fig.update_layout(height=650,xaxis={"visible":False},yaxis={"visible":False})
            plot(st,fig,use_container_width=True)
        show(pd.DataFrame([{"Source":u,"Target":v,**d} for u,v,d in g.edges(data=True)]),"graph_edges")
    st.caption("Edges reflect documented capabilities or evidence references, not inferred commercial partnerships.")
elif page=="Research gaps":
    st.header("Research gap analyser")
    priority=st.multiselect("Priority capabilities",selected_caps,default=[c for c in cfg.get("priority_capabilities",[]) if c in selected_caps],format_func=cnames.get)
    gaps=research_gaps(data,mat,priority)
    st.metric("Candidate research questions",len(gaps))
    statuses=st.multiselect("Research status",sorted(gaps["Status"].unique()),default=[])
    if statuses: gaps=gaps[gaps["Status"].isin(statuses)]
    show(gaps,"research_gaps")
    st.caption("Heuristic priorities: product priority + direct competition + selected capability + disputed evidence. Review relevance before assigning research; not all combinations are applicable.")
    research_panel(st,data,cfg,show)
    st.subheader("Existing open questions")
    show(frame(data,"To be Confirmed"),"existing_questions")
elif page=="Similarity & clustering":
    st.header("Product similarity and clustering")
    threshold=st.number_input("Minimum jointly determinate capabilities",min_value=1,max_value=max(1,len(selected_caps)),value=min(int(cfg.get("min_shared_capabilities",5)),len(selected_caps)))
    sim=similarity(mat,int(threshold))
    if sim.empty: st.info("Insufficient shared determinate assessments. No similarity is estimated.")
    else:
        sim=sim.sort_values(["Similarity","Shared determinate"],ascending=False)
        show(sim,"similarity")
        cluster,excluded=clusters(mat,int(threshold))
        show(cluster,"clusters")
        st.write("Excluded from complete-distance clustering:",len(excluded),"products")
        st.caption("Complete-linkage clustering uses a deterministic fully comparable subset; excluded products are not assigned clusters.")
elif page=="Technology gaps":
    st.header("AIT-VISTA capability and function mapping")
    st.caption("Use local design targets, not market assertions. Market scarcity does not validate customer demand.")
    configured=cfg.get("vista_capabilities",{})
    targets=st.multiselect("AIT-VISTA capabilities",selected_caps,default=[c for c in configured if c in selected_caps],format_func=cnames.get)
    if targets:
        maturity={cid:st.selectbox(cnames[cid],["Planned","Implemented","Demonstrated","Verified"],index=["Planned","Implemented","Demonstrated","Verified"].index(configured.get(cid,"Planned")) if configured.get(cid,"Planned") in ["Planned","Implemented","Demonstrated","Verified"] else 0,key="maturity-"+cid) for cid in targets}
        gap=capability_gaps(data,mat,maturity)
        gap["Capability"]=gap["Capability ID"].map(cnames)
        gap["System functions"]=gap["Capability ID"].map(lambda c:"; ".join(cfg.get("function_mapping",{}).get(c,[])))
        show(gap,"technology_gaps")
        st.caption("Set persistent targets and system-function links in the local configuration. No changes are made to Google Sheets.")
    else: st.info("No target mapping selected. Choose capabilities or configure reviewed AIT-VISTA targets locally.")
elif page=="History & evolution":
    st.header("Historical intelligence")
    if demo_mode: st.info("History is unavailable in synthetic demo mode.")
    else:
        show(pd.DataFrame(snapshots,columns=["Hash","Captured UTC","Source","Schema version"]),"snapshots")
        if len(snapshots)>1:
            hashes=[r[0] for r in snapshots]
            label={r[0]:r[1]+" · "+r[0][:10] for r in snapshots}
            old=st.selectbox("Baseline",hashes,index=1,format_func=label.get)
            new=st.selectbox("Comparison",hashes,index=0,format_func=label.get)
            with connect() as conn:
                before,after=read_snapshot(conn,old),read_snapshot(conn,new)
            show(pd.DataFrame(diff(before,after),columns=["Table","ID","Change","Fields"]),"snapshot_changes")
            st.caption("A new assessment is new recorded knowledge, not necessarily a newly introduced product capability.")
            evolution_panel(st,before,after,selected_caps,cnames,show)
        if snapshots:
            rows=[]
            with connect() as conn:
                for h,t,_,_ in reversed(snapshots):
                    snap=read_snapshot(conn,h)
                    for name in ["Companies","Products","Capabilities","Capability Assessment","Deployments","Commercial Intelligence"]:
                        rows.append({"UTC":t,"Register":name,"Records":len(records(snap,name))})
            plot(st,px.line(pd.DataFrame(rows),x="UTC",y="Records",color="Register",markers=True),use_container_width=True)
            chosen=st.selectbox("Restore local snapshot", [r[0] for r in snapshots],format_func=lambda h:h[:12])
            if st.checkbox("I understand this changes the local view only") and st.button("Restore selected snapshot"):
                with connect() as conn: restore(conn,chosen)
                st.rerun()
    st.subheader("Observation dates")
    obs=frame(data,"Observations")
    for field in ["Date added (ISO)","Source publication date (ISO)","Source checked (ISO)"]:
        if field in obs:
            dates=pd.to_datetime(obs[field],errors="coerce",utc=True)
            counts=dates.dropna().dt.strftime("%Y-%m-%d").value_counts().sort_index().rename_axis("Date").reset_index(name="Count")
            if not counts.empty: plot(st,px.bar(counts,x="Date",y="Count",title=field),use_container_width=True)
elif page=="Product intelligence":
    product_page(st,data,mat,pnames,cnames,cfg,show,demo_mode)
elif page=="Strategic intelligence":
    strategic_page(st,data,mat,cnames,cfg,show,demo_mode)
elif page=="Reports":
    st.header("Export and reporting")
    export_panel(st,data,cfg,snapshots,current,head,demo_mode,page,location="main")
    st.caption("Exports contain local intelligence. Do not commit reports or snapshots into a public repository.")
    st.download_button("Download full snapshot JSON",canonical(data),file_name="cie_snapshot.json",mime="application/json")
    try:
        st.download_button("Download full snapshot Excel",workbook_bytes(data,None if demo_mode else current),file_name="cie_snapshot.xlsx",mime=MIME,key="reports-full-xlsx")
    except (ValueError,TypeError,OverflowError) as exc:
        st.warning("Snapshot Excel export unavailable: "+str(exc)[:200])
    gaps=research_gaps(data,mat,cfg.get("priority_capabilities",[]))
    title="5PACE Competitive Intelligence Report"+(" — SYNTHETIC DEMO" if demo_mode else "")
    doc="<html><head><meta charset='utf-8'><title>"+html.escape(title)+"</title><style>body{font:15px system-ui;margin:32px;color:#182439}table{border-collapse:collapse;font-size:12px}td,th{padding:6px;border:1px solid #ccd3db;vertical-align:top}h1,h2{color:#203861}</style></head><body>"
    doc+="<h1>"+html.escape(title)+"</h1><p>Snapshot: "+html.escape(digest(data))+"</p><p>Source sync (UTC): "+html.escape("Not applicable (synthetic)" if demo_mode else last or "Not synchronised")+"</p>"
    doc+="<h2>Coverage</h2>"+pd.DataFrame([stats]).to_html(index=False,escape=True)
    doc+="<h2>Current assessments</h2>"+latest[latest["Product ID"].isin(selected_products)&latest["Capability ID"].isin(selected_caps)].to_html(index=False,escape=True)
    doc+="<h2>Top research questions</h2>"+gaps.head(100).to_html(index=False,escape=True)
    doc+="<p>Unknown is not unsupported. Vendor claims are not independent verification. Research priorities are heuristic.</p></body></html>"
    st.download_button("Download standalone HTML report",doc.encode("utf-8"),file_name="cie_report.html",mime="text/html")
    from advanced_ui import strategic_report
    st.download_button("Download strategic decision report",strategic_report(data,mat,cfg,demo_mode),file_name="cie_strategy.html",mime="text/html")
    show(gaps.head(100),"report_research_questions")
