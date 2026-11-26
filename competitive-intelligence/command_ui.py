"""Executive command centre; existing analytical workspaces remain available."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core import value, connect, read_snapshot
from advanced_ui import save_settings
from analytics import matrix, DISPLAY
from product_intelligence import criterion_matrix, CRITERIA, mappings
from command_engine import (ASSESS, VIEW, registry, direct_matrix, direct_current, matrix_audit,
    profile, scope_ids, threat_table, advantages, research_queue, comparison_changes, overlap_history, BASE_STATES, MATURITY, SCOPE)

def table(st,df,key):
    st.dataframe(df,use_container_width=True,hide_index=True)
    if not df.empty:
        st.download_button("Export CSV",df.to_csv(index=False).encode("utf-8"),file_name=key+".csv",key="cmd-"+key)

def intervals(st,df,lower,upper,label,axis):
    d=df.dropna(subset=[lower,upper]).iloc[::-1]
    if d.empty: return
    fig=go.Figure(go.Scatter(x=d[lower],y=d[label],mode="markers",error_x={"type":"data","symmetric":False,"array":(d[upper]-d[lower]).clip(lower=0),"arrayminus":[0]*len(d)},marker={"size":9}))
    fig.update_layout(xaxis={"range":[0,1],"tickformat":".0%","title":axis},height=max(330,28*len(d)+100),margin={"l":10,"r":20})
    st.plotly_chart(fig,use_container_width=True)

def command_page(st,data,cfg,demo_mode,snapshots,current):
    st.header("Competitive Command Centre")
    st.caption("Decision support · direct criterion evidence · local scenarios · no source writes")
    criteria=registry(data,CRITERIA,"Criterion ID")
    products=registry(data,"Products","Product ID")
    if not criteria or ASSESS not in data:
        st.info("Direct comparison requires AIT-VISTA Capabilities and Comparison Assessment. Synchronise the latest source; historical snapshots may not contain these registers.")
        return
    labels={k:value(r,"Product criterion") for k,r in criteria.items()}
    names={k:value(r,"Product Name")+" · "+k for k,r in products.items()}
    audit=matrix_audit(data)
    if audit:
        st.warning(f"Derived comparison matrix has {len(audit)} discrepancy notices. Ledger remains authoritative; inspect before relying on the affected results.")
        with st.expander("Source matrix cross-check"): st.write(audit[:100])
    roles=sorted({value(r,"Competition Type") or "Unclassified" for r in products.values()})
    default_roles=[x for x in ["Direct","Adjacent / substitute","Potential entrant"] if x in roles] or roles
    left,right=st.columns(2)
    mode=left.radio("AIT-VISTA comparison baseline",["Target","MVP","As-Is"],horizontal=True,key="cmd-mode")
    selected_roles=right.multiselect("Competitor cohort",roles,default=default_roles,key="cmd-roles")
    ids=[p for p,r in products.items() if (value(r,"Competition Type") or "Unclassified") in selected_roles]
    if mode!="As-Is": st.info("Target/MVP describe intended scope, not implemented capability. Planned overlap is not a verified advantage.")
    view=st.radio("Command workspace",["Executive dashboard","Benchmark & competitor profile","Product baseline & priorities","Watchlist & evolution","Research queue"],horizontal=True,key="cmd-view")
    allmat=direct_matrix(data,ids)
    weights={c:cfg.get("command_profiles",{}).get(c,{}).get("importance",3) for c in criteria}
    scope=scope_ids(data,cfg,mode)
    mat=allmat[scope]
    if not ids: st.warning("Select at least one competitor role.")
    if not scope: st.warning("No established criteria in this baseline. Configure the local product baseline. Unknown scope is not scored.")
    threat_weights=dict(cfg.get("commercial_weights",{}))
    with st.expander("Threat scenario weights and interpretation"):
        st.caption("Ordinal evidence scenario, not a calibrated threat probability. Source role determines review group; lower bound orders within group. Missing evidence retains uncertainty. Partial support = 0.5. Space relevance, commercial status and documented adoption are proxies, not market share.")
        for k in ["Functional overlap","Space relevance","Commercial availability","Documented adoption"]:
            threat_weights[k]=st.slider(k,0,10,int(threat_weights.get(k,3)),key="cmd-w-"+k)
        if not any(threat_weights.values()) or not any(threat_weights[k] for k in threat_weights if k!="Functional overlap"):
            st.warning("Use at least one commercial-axis weight; default weights applied for invalid scenario.")
            threat_weights={"Functional overlap":5,"Space relevance":3,"Commercial availability":2,"Documented adoption":2}
    threat=threat_table(data,mat,weights,threat_weights)
    av=advantages(data,allmat,cfg,mode) if ids else pd.DataFrame()
    if view=="Executive dashboard":
        if threat.empty: return
        direct=threat[threat.Role=="Direct"]
        st.subheader("Who to watch first")
        st.caption("Source-classified direct competitors take review priority; within each role order is the lower evidence-backed threat scenario bound, not definitive ranking.")
        top=threat.head(12).copy()
        top["Threat interval"]=top.apply(lambda r:f"{r['Threat lower']:.0%}–{r['Threat upper']:.0%}",axis=1)
        top["Determinate scope"]=top["Known weight"].map(lambda v:f"{v:.0%}")
        table(st,top[["Product","Company","Role","Threat interval","Determinate scope","Why watch","Review action"]],"watch-first")
        st.subheader("Competitive landscape")
        d=threat.dropna(subset=["Overlap lower","Market lower"]).copy()
        d["Overlap uncertainty"]=(d["Overlap upper"]-d["Overlap lower"]).clip(lower=0)
        d["Market uncertainty"]=(d["Market upper"]-d["Market lower"]).clip(lower=0)
        if not d.empty:
            d["Zero"]=0.
            fig=px.scatter(d,x="Overlap lower",y="Market lower",color="Role",hover_name="Product",hover_data=["Company","Product ID","Overlap upper","Market upper","Known weight","Commercial status","Space relevance","Why watch"],error_x="Overlap uncertainty",error_x_minus="Zero",error_y="Market uncertainty",error_y_minus="Zero")
            fig.update_traces(marker={"size":10})
            fig.add_vline(x=.5,line_dash="dot");fig.add_hline(y=.5,line_dash="dot")
            fig.update_layout(xaxis={"range":[0,1.05],"tickformat":".0%","title":"Functional scope overlap (lower bound + uncertainty)"},yaxis={"range":[0,1.05],"tickformat":".0%","title":"Commercial / space / adoption evidence (lower + uncertainty)"},height=550)
            st.plotly_chart(fig,use_container_width=True)
        st.subheader("Threat intervals — priority review cohort")
        intervals(st,top,"Threat lower","Threat upper","Product","Weighted threat scenario")
        st.subheader("Where AIT-VISTA stands")
        st.caption("Compared against best observed competitor in the chosen cohort. Missing evidence prevents definitive market-wide claims.")
        candidate=av[av["AIT-VISTA"]!="Not applicable"].copy()
        candidate["Existing positive verdicts"]=(candidate["Existing full support"]+candidate["Existing partial support"])/candidate["Eligible competitors"].replace(0,float("nan"))
        candidate["Unresolved share"]=candidate["Unresolved"]/candidate["Eligible competitors"].replace(0,float("nan"))
        if not candidate.empty:
            fig=go.Figure(go.Bar(x=candidate["Existing positive verdicts"],y=candidate["Criterion ID"],orientation="h",name="Observed positive verdicts",customdata=candidate[["Criterion","Assessment"]],hovertemplate="%{customdata[0]}<br>%{customdata[1]}<br>Positive: %{x:.0%}<extra></extra>"))
            fig.add_trace(go.Bar(x=candidate["Unresolved share"],y=candidate["Criterion ID"],orientation="h",name="Unresolved (possible overlap)",marker={"color":"#828b99"},hovertemplate="Unresolved: %{x:.0%}<extra></extra>"))
            fig.update_layout(barmode="stack",xaxis={"range":[0,1],"tickformat":".0%","title":"Share of selected applicable competitors"},height=max(420,24*len(candidate)+100),title="Existing competition vs unresolved differentiation hypotheses")
            st.plotly_chart(fig,use_container_width=True)
        table(st,av[["Criterion","AIT-VISTA","Assessment","Existing full support","Existing partial support","Unresolved","Demand"]],"position-summary")
        actual=av.dropna(subset=["Delta lower","Delta upper"]).copy()
        if not actual.empty:
            fig=go.Figure(go.Scatter(x=actual["Delta lower"],y=actual.Criterion,mode="markers",error_x={"type":"data","symmetric":False,"array":actual["Delta upper"]-actual["Delta lower"],"arrayminus":[0]*len(actual)}))
            fig.add_vline(x=0,line_dash="dash");fig.update_layout(xaxis={"range":[-1,1],"title":"AIT-VISTA minus best competitor (interval)"},height=max(380,28*len(actual)+100))
            st.plotly_chart(fig,use_container_width=True)
        else: st.info("No current implementation baseline with evidence references; relative current advantage cannot yet be calculated.")
    elif view=="Benchmark & competitor profile":
        if not ids: return
        default=threat["Product ID"].head(6).tolist() if not threat.empty else ids[:6]
        chosen=st.multiselect("Products for direct comparison",ids,default=default,format_func=names.get,key="cmd-bench")
        if not chosen: return
        statuses=DISPLAY+["Target"]
        colors=["#596579","#9299a3","#b85155","#7998c7","#c5a05b","#379976","#656565","#cd79c7","#8f86b4","#377da3"]
        code=dict(zip(statuses,range(len(statuses))))
        bm=allmat.loc[chosen].copy()
        bm.loc["AIT-VISTA ("+mode+")"]=[profile(cfg,c,mode) for c in bm.columns]
        bm=bm.iloc[::-1]
        scale=[]
        for i,c in enumerate(colors): scale.extend([[i/len(colors),c],[(i+1)/len(colors),c]])
        fig=go.Figure(go.Heatmap(z=bm.apply(lambda s:s.map(code)).to_numpy(),x=list(bm.columns),y=[names.get(p,p) for p in bm.index],text=bm.to_numpy(),zmin=-.5,zmax=len(colors)-.5,colorscale=scale,colorbar={"tickmode":"array","tickvals":list(code.values()),"ticktext":statuses},hovertemplate="%{y}<br>%{x}<br>%{text}<extra></extra>"))
        fig.update_layout(height=max(380,40*len(bm)+130))
        st.plotly_chart(fig,use_container_width=True)
        table(st,bm.rename(index=names,columns=labels).rename_axis("Product").reset_index(),"direct-matrix")
        pid=st.selectbox("Competitor profile",chosen,format_func=names.get,key="cmd-pid")
        st.write({k:value(products[pid],k) for k in ["Competition Type","Strategic Priority","Primary Use Case","Target Customers","Commercial Status","Deployment Architecture","Space Industry Applicability","Product URL"]})
        if not threat.empty: table(st,threat[threat["Product ID"]==pid].drop(columns=["Rank group"]),"profile-threat")
        table(st,advantages(data,allmat.loc[[pid]],cfg,mode),"profile-relative-position")
        cid=st.selectbox("Inspect criterion evidence",list(criteria),format_func=lambda c:c+" · "+labels[c],key="cmd-cid")
        cur=direct_current(data).get((pid,cid),{})
        st.write("Direct verdict:",cur.get("status","Unassessed"))
        st.write("Current direct records")
        table(st,pd.DataFrame(cur.get("rows",[])),"active-direct-evidence")
        st.write("Full ledger history")
        table(st,pd.DataFrame([r for r in data[ASSESS]["rows"] if value(r,"Product ID")==pid and value(r,"Criterion ID")==cid]),"direct-history")
        st.caption("Market capability proxies below are separate candidate evidence; they never establish a direct verdict.")
        proxies=criterion_matrix(data,matrix(data,[pid]))
        table(st,proxies[proxies["Criterion ID"]==cid],"market-proxies")
        st.write("Related deployments and commercial records")
        for tab in ["Deployments","Commercial Intelligence"]:
            table(st,pd.DataFrame([r for r in data[tab]["rows"] if value(r,"Product ID")==pid]),"cmd-"+tab)
    elif view=="Product baseline & priorities":
        st.subheader("AIT-VISTA local baseline")
        st.caption("Enter engineering evidence and customer validation manually. Source criteria describe intended scope only. Never infer implementation from a function mapping.")
        cid=st.selectbox("Edit criterion",list(criteria),format_func=lambda c:c+" · "+labels[c],key="cmd-edit")
        r=cfg.get("command_profiles",{}).get(cid,{})
        def idx(options,v): return options.index(v) if v in options else 0
        with st.form("cmd-baseline-"+cid):
            a,b=st.columns(2)
            stage=a.selectbox("Implementation maturity",MATURITY,index=idx(MATURITY,r.get("stage")))
            status=b.selectbox("Current support verdict",BASE_STATES,index=idx(BASE_STATES,r.get("status")))
            ref=st.text_input("Implementation evidence / verification reference",value=r.get("reference",""))
            a,b=st.columns(2)
            mvp=a.selectbox("MVP scope",SCOPE,index=idx(SCOPE,r.get("mvp")))
            target=b.selectbox("Target scope",SCOPE,index=idx(SCOPE,r.get("target","Included")))
            demand=st.selectbox("Customer demand",["Unvalidated","Hypothesis","Validated"],index=idx(["Unvalidated","Hypothesis","Validated"],r.get("demand")))
            dref=st.text_input("Customer demand evidence reference",value=r.get("demand_reference",""))
            importance=st.slider("Criterion importance (scenario weight)",1,5,int(r.get("importance",3)))
            effort=st.selectbox("Development effort (team estimate)",["Unknown","Low","Medium","High"],index=idx(["Unknown","Low","Medium","High"],r.get("effort")))
            strategic=st.selectbox("Strategic value (team estimate)",["Unknown","Low","Medium","High"],index=idx(["Unknown","Low","Medium","High"],r.get("strategic_value")))
            route=st.selectbox("Delivery option",["Unassessed","Build","Buy","Partner"],index=idx(["Unassessed","Build","Buy","Partner"],r.get("route")))
            trade=st.text_area("Trade-off rationale / cost, IP, dependencies and risks",value=r.get("tradeoff",""))
            submit=st.form_submit_button("Save local criterion profile",disabled=demo_mode)
        if submit:
            if status!="Unknown" and (not ref.strip() or stage not in {"Implemented","Demonstrated","Verified"}):
                st.error("Current support claim requires implementation maturity and an evidence reference.")
            elif demand=="Validated" and not dref.strip(): st.error("Validated demand requires a reference.")
            else:
                allp=dict(cfg.get("command_profiles",{}));allp[cid]={"stage":stage,"status":status,"reference":ref.strip(),"mvp":mvp,"target":target,"demand":demand,"demand_reference":dref.strip(),"importance":importance,"effort":effort,"strategic_value":strategic,"route":route,"tradeoff":trade}
                save_settings({"command_profiles":allp});st.rerun()
        rows=[]
        for c in criteria:
            r=cfg.get("command_profiles",{}).get(c,{})
            rows.append({"Criterion ID":c,"Criterion":labels[c],"As-Is":profile(cfg,c,"As-Is"),"MVP":profile(cfg,c,"MVP"),"Target":profile(cfg,c,"Target"),"Maturity":r.get("stage","Unknown"),"Effort":r.get("effort","Unknown"),"Strategic value":r.get("strategic_value","Unknown"),"Delivery option":r.get("route","Unassessed"),"Trade-off":r.get("tradeoff",""),"Implementation reference":r.get("reference",""),"Demand reference":r.get("demand_reference","")})
        df=pd.DataFrame(rows)
        st.subheader("Strategic priority map")
        scale={"Low":1,"Medium":2,"High":3}
        d=df.copy();d["Effort level"]=d.Effort.map(scale);d["Value level"]=d["Strategic value"].map(scale)
        d=d.dropna(subset=["Effort level","Value level"])
        if d.empty: st.info("Enter effort and strategic value estimates to position criteria. Unknown estimates are excluded, not imputed.")
        else:
            fig=px.scatter(d,x="Effort level",y="Value level",color="Delivery option",text="Criterion ID",hover_name="Criterion",hover_data=["Maturity","Trade-off"])
            fig.update_layout(xaxis={"range":[.5,3.5],"tickvals":[1,2,3],"ticktext":["Low","Medium","High"],"title":"Development effort"},yaxis={"range":[.5,3.5],"tickvals":[1,2,3],"ticktext":["Low","Medium","High"],"title":"Strategic value"},height=450)
            st.plotly_chart(fig,use_container_width=True)
        table(st,df,"baseline-roadmap")
        st.subheader("Engineering traceability")
        table(st,mappings(data),"criterion-function-trace")
        if not av.empty: table(st,av,"advantage-register")
    elif view=="Watchlist & evolution":
        st.subheader("Watchlist")
        if not threat.empty: table(st,threat.drop(columns=["Rank group"]),"watchlist")
        if not demo_mode and len(snapshots)>1:
            alternatives=[s for s in snapshots if s[0]!=current]
            if alternatives:
                baseline=st.selectbox("Compare selected snapshot against current view",[s[0] for s in alternatives],format_func=lambda h:next(s[1]+" · "+h[:10] for s in alternatives if s[0]==h))
                with connect() as conn: old=read_snapshot(conn,baseline)
                changes=comparison_changes(old,data)
                st.caption("New recorded knowledge and changed verdicts are not evidence of new product releases.")
                if changes.empty: st.info("No direct assessment changes.")
                else:
                    table(st,changes,"comparison-changes")
                    st.plotly_chart(px.bar(changes.groupby(["Product ID","Interpretation"]).size().reset_index(name="Changes"),x="Changes",y="Product ID",color="Interpretation",orientation="h"),use_container_width=True)
        else: st.info("A second distinct snapshot is needed to compare recorded changes.")
        st.subheader("Recorded overlap evolution")
        if not demo_mode and len(snapshots)>1 and scope and ids:
            chosen=st.multiselect("Track products",ids,default=(threat["Product ID"].head(4).tolist() if not threat.empty else ids[:4]),format_func=names.get,key="cmd-track")
            if chosen:
                with connect() as conn:
                    historical=[(s[1],read_snapshot(conn,s[0])) for s in reversed(snapshots[:30])]
                historical=[(stamp,d) for stamp,d in historical if d is not None]
                evolution=overlap_history(historical,chosen,scope,weights)
                if evolution.empty: st.info("No comparable historical direct assessment data.")
                else:
                    fig=go.Figure()
                    for p,g in evolution.groupby("Product ID",sort=False):
                        fig.add_trace(go.Scatter(x=g.Snapshot,y=g.Lower,mode="lines+markers",name=names.get(p,p)+" lower",customdata=g[["Upper","Known weight"]],hovertemplate="Lower %{y:.0%}<br>Upper %{customdata[0]:.0%}<br>Determinate %{customdata[1]:.0%}<extra></extra>"))
                        fig.add_trace(go.Scatter(x=g.Snapshot,y=g.Upper,mode="lines",line={"dash":"dot"},name=names.get(p,p)+" upper"))
                    fig.update_layout(yaxis={"range":[0,1],"tickformat":".0%","title":"Recorded functional overlap interval"},height=420)
                    st.plotly_chart(fig,use_container_width=True)
                    table(st,evolution,"comparison-evolution")
                st.caption("Fixed selected criterion set and weights. Not applicable treated as unresolved here for a stable denominator. Changes in recorded evidence do not establish product evolution.")
        else: st.info("At least two distinct snapshots and a selected baseline scope are required.")
        st.subheader("Latest source observations")
        obs=pd.DataFrame(data["Observations"]["rows"])
        if not obs.empty: table(st,obs.sort_values("Date added (ISO)",ascending=False).head(20) if "Date added (ISO)" in obs else obs.head(20),"watch-observations")
    else:
        st.subheader("Actionable direct comparison research")
        q=research_queue(data,allmat,cfg)
        st.caption("Heuristic triage: source competition classification, criterion importance, uncertainty, weak and ageing evidence. Export questions to the authorised research workflow; no write to source.")
        if not q.empty: table(st,q.head(300),"priority-research")
        else: st.info("No selected research questions.")
