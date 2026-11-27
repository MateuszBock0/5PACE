"""Offline market positioning UI. All views use the direct ledger and owner baseline."""
import pandas as pd
from excel_archive import download_analysis
import plotly.express as px
import plotly.graph_objects as go
from chart_theme import plot, tokens, role_colors, action_colors, reference_marker, rival_marker, heatmap_colors, colors as chart_colors
from core import value
from command_engine import direct_current, registry, ASSESS
from advanced_ui import save_settings
from product_intelligence import CRITERIA
from positioning import (VISTA,ALL,DIMENSIONS,COMMERCIAL,WORKFLOWS,EVIDENCE_MODES,taxonomy,axis_groups,
    interval_arrays,positioning_table,proximity,company_positions,advantage_portfolio,workflow_groups,workflow_context,workflow_benchmark,sensitivity_analysis)

def table(st,d,key):
    st.dataframe(d,use_container_width=True,hide_index=True)
    if not d.empty:
        st.download_button("Export CSV",d.to_csv(index=False).encode("utf-8"),file_name=key+".csv",key="pos-"+key)
        download_analysis(st,d,"pos-"+key,key)

def interval_chart(st,d,lower,upper,label,title):
    if d.empty: return
    d=d.dropna(subset=[lower,upper]).iloc[::-1]
    if d.empty: return
    f=go.Figure(go.Scatter(x=d[lower],y=d[label],mode="markers",error_x={"type":"data","symmetric":False,"array":(d[upper]-d[lower]).clip(lower=0),"arrayminus":[0]*len(d)}))
    f.update_layout(title=title,xaxis={"range":[0,1.04],"tickformat":".0%"},height=max(330,27*len(d)+100))
    plot(st,f,use_container_width=True)

def positioning_page(st,data,cfg,mat,weights,mode,demo_mode):
    st.header("Market Positioning Intelligence")
    st.caption("Shared axes for AIT-VISTA and competitors · direct comparison ledger · fixed denominators · no source writes")
    if mat.empty: st.info("Select a non-empty competitor cohort.");return
    if mode!="As-Is": st.warning("Planning scenario — positions do not establish current AIT-VISTA functionality.")
    tax=taxonomy(data,cfg);groups=axis_groups(tax)
    if tax.empty: st.info("No source comparison criteria.");return
    a,b=st.columns(2)
    evidence=a.selectbox("Competitor evidence scenario",list(EVIDENCE_MODES),index=1,key="pos-evidence")
    partial=b.select_slider("Partial-support convention",options=[.25,.5,.75],value=.5,key="pos-partial")
    lo,hi,state,basis=interval_arrays(data,mat,cfg,mode,evidence,partial)
    pos=positioning_table(data,lo,hi,groups,weights,cfg,mode)
    names=pos.set_index("Product ID").Product.to_dict()
    axes=list(groups)+COMMERCIAL
    view=st.radio("Positioning workspace",["Positioning map","Capability profile","Competitive proximity","Company portfolios","Advantage portfolio","Evidence sensitivity","Workflow differentiation","Methodology & settings"],horizontal=True,key="pos-view")
    st.caption("Intervals are scenario bounds, not probabilities. Unknown, disputed, weak evidence under the chosen threshold and non-comparable N/A remain unresolved. Fixed criterion denominators prevent incomparable percentages. AIT-VISTA's declared functionality needs no evidence input.")
    if view=="Positioning map":
        a,b=st.columns(2)
        x=a.selectbox("X axis",axes,index=0,key="pos-x")
        y=b.selectbox("Y axis",axes,index=axes.index("Visual verification") if "Visual verification" in axes else len(groups),key="pos-y")
        chosen_products=st.multiselect("Limit map to selected products (empty = all)",list(mat.index),format_func=names.get,key="pos-map-products")
        d=pos[pos["Product ID"].isin([VISTA]+chosen_products)].copy() if chosen_products else pos.copy()
        d["X width"]=(d[x+" upper"]-d[x+" lower"]).clip(lower=0)
        d["Y width"]=(d[y+" upper"]-d[y+" lower"]).clip(lower=0)
        d["Zero"]=0.
        d["Reference"]=d["Product ID"].map(lambda p:"AIT-VISTA" if p==VISTA else "Competitor")
        d["X lower"]=d[x+" lower"];d["X upper"]=d[x+" upper"];d["Y lower"]=d[y+" lower"];d["Y upper"]=d[y+" upper"]
        others=d[d["Product ID"]!=VISTA]
        fig=px.scatter(others,x="X lower",y="Y lower",color="Role",color_discrete_map=role_colors(),hover_name="Product",custom_data=["Product ID"],hover_data=["Company","X upper","Y upper"],error_x="X width",error_x_minus="Zero",error_y="Y width",error_y_minus="Zero")
        own=d[d["Product ID"]==VISTA].iloc[0]
        fig.add_trace(go.Scatter(x=[own["X lower"]],y=[own["Y lower"]],name=own.Product,mode="markers+text",text=[own.Product],textposition="bottom left",customdata=[[VISTA]],marker={"symbol":"star","size":20,"color":"#22b987"},error_x={"type":"data","symmetric":False,"array":[own["X width"]],"arrayminus":[0]},error_y={"type":"data","symmetric":False,"array":[own["Y width"]],"arrayminus":[0]},hovertemplate="AIT-VISTA reference<br>X lower %{x:.0%}<br>Y lower %{y:.0%}<extra></extra>"))
        fig.data[-1].marker=reference_marker(symbol="star")
        fig.data=(fig.data[-1],)+fig.data[:-1]
        for tr in fig.data[1:]:tr.update(marker=rival_marker(tr.name))
        fig.update_layout(xaxis={"range":[-.03,1.08],"tickformat":".0%","title":x},yaxis={"range":[-.03,1.08],"tickformat":".0%","title":y},height=580)
        event=plot(st,fig,use_container_width=True,on_select="rerun",selection_mode="points",key="pos-map")
        if own["X width"]>=.999 or own["Y width"]>=.999: st.info("AIT-VISTA has an unresolved axis. The star marks the lower interval endpoint, not a measured position.")
        st.caption("A star at 100% functional scope reflects the chosen internal criteria, not universal market leadership. Axes measure scope and ordinal commercial evidence, not measured performance.")
        points=event.selection.points if event is not None and hasattr(event,"selection") else []
        clicked=points[0].get("customdata",[]) if points else []
        options=d["Product ID"].tolist()
        chosen=clicked[0] if clicked and clicked[0] in options else VISTA
        p=st.selectbox("Inspect product",options,index=options.index(chosen),format_func=names.get,key="pos-inspect-"+chosen)
        detail=pd.DataFrame({"Criterion ID":list(mat.columns),"Criterion":tax.set_index("Criterion ID").loc[list(mat.columns),"Criterion"].tolist(),"Verdict":state.loc[p].tolist(),"Evidence basis":basis.loc[p].tolist(),"Lower":lo.loc[p].tolist(),"Upper":hi.loc[p].tolist()})
        table(st,detail,"axis-evidence")
        if p!=VISTA:
            with st.expander("Underlying comparison records and limitations"):
                table(st,pd.DataFrame([r for r in data[ASSESS]["rows"] if value(r,"Product ID")==p]),"map-ledger")
        d["X axis"]=x;d["Y axis"]=y;d["Evidence scenario"]=evidence;d["Partial support"]=partial;d["Baseline"]=mode
        table(st,d[["Product ID","Product","Company","Role","X axis","X lower","X upper","Y axis","Y lower","Y upper","Evidence scenario","Partial support","Baseline"]],"positions")
    elif view=="Capability profile":
        selected=st.multiselect("Competitors to benchmark",list(mat.index),default=list(mat.index)[:3],format_func=names.get,key="pos-benchmark")
        dims=[d for d in groups if d!=ALL] or [ALL]
        f=go.Figure()
        rows=[]
        palette=chart_colors()
        for i,p in enumerate([VISTA]+selected):
            r=pos[pos["Product ID"]==p].iloc[0]
            color=tokens()["reference"] if p==VISTA else palette[(i-1)%len(palette)]
            low=[r[d+" lower"] for d in dims];high=[r[d+" upper"] for d in dims]
            # Draw separate closed bounds, never a made-up midpoint.
            f.add_trace(go.Scatterpolar(r=low+[low[0]],theta=dims+[dims[0]],mode="lines+markers",line={"color":color},legendgroup=p,name=names[p]+" lower"))
            f.add_trace(go.Scatterpolar(r=high+[high[0]],theta=dims+[dims[0]],mode="lines",line={"dash":"dot","color":color},legendgroup=p,name=names[p]+" upper"))
            rows.extend({"Product ID":p,"Product":names[p],"Dimension":d,"Lower":l,"Upper":h} for d,l,h in zip(dims,low,high))
        f.update_layout(polar={"radialaxis":{"range":[0,1],"tickformat":".0%"}},height=520)
        plot(st,f,use_container_width=True)
        table(st,pd.DataFrame(rows),"capability-profile")
        st.caption("Solid = lower bound; dotted = upper bound. Dimensions are an analytical grouping, not an independent market-wide requirements standard.")
    elif view=="Competitive proximity":
        prox_groups={**groups,**{"Workflow: "+stage:ids for stage,ids in workflow_groups(tax).items() if ids}}
        dim=st.selectbox("Proximity dimension",list(prox_groups),key="pos-prox-dim")
        sim=proximity(lo,hi,{dim:prox_groups[dim]},weights).merge(pos[["Product ID","Product","Company","Role","Family ID","Commercial readiness lower","Commercial readiness upper","Space relevance lower","Space relevance upper"]],on="Product ID")
        sim=sim.sort_values(["Similarity lower","Similarity upper","Product ID"],ascending=[False,False,True])
        st.subheader("Strongest recorded functional proximity")
        interval_chart(st,sim.head(15),"Similarity lower","Similarity upper","Product","Similarity to selected AIT-VISTA baseline")
        st.subheader("Highest unresolved potential proximity")
        table(st,sim.sort_values(["Similarity upper","Similarity lower","Product ID"],ascending=[False,False,True]),"proximity")
        st.subheader("Commercially relevant substitution candidates")
        candidates=sim[sim.Role.isin(["Direct visual AIT candidate","Workflow / procurement substitute candidate","Cross-industry competitor candidate"])].copy()
        if candidates.empty: st.info("No classified substitution candidates in the selected cohort.")
        else:
            candidates["Proximity width"]=candidates["Similarity upper"]-candidates["Similarity lower"]
            candidates["Commercial width"]=candidates["Commercial readiness upper"]-candidates["Commercial readiness lower"]
            candidates["Zero"]=0.
            fig=px.scatter(candidates,x="Similarity lower",y="Commercial readiness lower",color="Role",hover_name="Product",error_x="Proximity width",error_x_minus="Zero",error_y="Commercial width",error_y_minus="Zero",hover_data=["Similarity upper","Commercial readiness upper","Company"])
            fig.update_layout(xaxis={"range":[0,1.05],"tickformat":".0%"},yaxis={"range":[0,1.05],"tickformat":".0%"},height=430)
            plot(st,fig,use_container_width=True)
        st.caption("Similarity is 1 minus weighted absolute criterion distance. With an all-supported reference it equals scope coverage; it cannot reveal capabilities outside our criteria. Commercial substitution remains a provisional classification, not inferred from proximity.")
    elif view=="Company portfolios":
        axis=st.selectbox("Company positioning dimension",axes,key="pos-company-axis")
        companies=company_positions(pos,axis)
        own=pos[pos["Product ID"]==VISTA].iloc[0]
        comparison=pd.concat([pd.DataFrame([{"Company":"5PACE · AIT-VISTA ("+mode+")","Portfolio lower":own[axis+" lower"],"Portfolio upper":own[axis+" upper"]}]),companies.head(15)],ignore_index=True)
        interval_chart(st,comparison,"Portfolio lower","Portfolio upper","Company","Best individual product exposure by company — with AIT-VISTA reference")
        table(st,companies,"companies")
        if not companies.empty:
            company=st.selectbox("Inspect company portfolio",companies["Company ID"].tolist(),format_func=companies.set_index("Company ID").Company.to_dict().get,key="pos-company")
            table(st,pos[pos["Company ID"]==company][["Product ID","Product","Role","Family ID",axis+" lower",axis+" upper"]],"company-products")
        st.caption("Bounds are maxima over actual member products. The best recorded and highest potential products may differ. No cross-product functionality union or integrated portfolio is assumed.")
    elif view=="Advantage portfolio":
        d=advantage_portfolio(data,lo,hi,state,cfg,mode)
        if d.empty: st.info("No applicable competitor comparisons.");return
        st.subheader("Functional differentiation vs strongest product")
        f=go.Figure(go.Scatter(x=d["Delta lower"],y=d.Criterion,mode="markers",error_x={"type":"data","symmetric":False,"array":(d["Delta upper"]-d["Delta lower"]).clip(lower=0),"arrayminus":[0]*len(d)},customdata=d[["Finding"]],hovertemplate="%{y}<br>%{customdata[0]}<br>Lower %{x:.0%}<extra></extra>"))
        f.add_vline(x=0,line_dash="dash");f.update_layout(xaxis={"range":[-1.05,1.05],"tickformat":".0%","title":"AIT-VISTA minus strongest competitor"},height=max(400,25*len(d)+100))
        plot(st,f,use_container_width=True)
        st.subheader("Rarity versus customer importance")
        mapped=d[d["Customer importance"]!="Unknown"].copy()
        if mapped.empty: st.info("Customer importance is not available in this workbook. No points are invented; enter optional estimates in Methodology & settings or use the existing other 5PACE sources after coordination.")
        else:
            mapped["Importance"]=mapped["Customer importance"].map({"Low":1,"Medium":2,"High":3})
            mapped["Rarity width"]=mapped["Rarity upper"]-mapped["Rarity lower"];mapped["Zero"]=0.
            fig=px.scatter(mapped,x="Rarity lower",y="Importance",color="Finding",hover_name="Criterion",error_x="Rarity width",error_x_minus="Zero")
            fig.update_layout(xaxis={"range":[0,1.05],"tickformat":".0%"},yaxis={"tickvals":[1,2,3],"ticktext":["Low","Medium","High"],"range":[.5,3.5]})
            plot(st,fig,use_container_width=True)
        table(st,d,"advantage-portfolio")
        st.caption("Rarity is an interval over distinct applicable product families. No competitor evidence does not establish advantage. Customer importance is an optional team estimate, not verified demand or performance.")
    elif view=="Evidence sensitivity":
        st.caption("Deterministic scenarios: all recorded / technical / independent evidence, partial support 0.25 / 0.5 / 0.75, criterion weights varied ±50%. Ranks are possible bounds across sampled weights and unresolved outcomes, not confidence intervals.")
        draws=st.select_slider("Weight variations per scenario",options=[10,40,100],value=40,key="pos-draws")
        summary,detail=sensitivity_analysis(data,mat,cfg,mode,weights,draws)
        if not summary.empty:
            summary["Product"]=summary["Product ID"].map(names)
            detail["Product"]=detail["Product ID"].map(names)
            f=go.Figure(go.Scatter(x=summary["Best possible rank"],y=summary.Product,mode="markers",error_x={"type":"data","symmetric":False,"array":summary["Worst possible rank"]-summary["Best possible rank"],"arrayminus":[0]*len(summary)}))
            f.update_layout(xaxis_title="Possible proximity rank across sampled scenarios (1 = closest)",height=max(400,22*len(summary)+100))
            plot(st,f,use_container_width=True)
            table(st,summary,"sensitivity-summary")
            with st.expander("Individual evidence and scoring scenarios"): table(st,detail,"sensitivity-detail")
    elif view=="Workflow differentiation":
        chosen=st.multiselect("Products for workflow comparison",list(mat.index),default=list(mat.index)[:3],format_func=names.get,key="pos-workflow-products")
        stages,bottleneck=workflow_benchmark(lo.loc[[VISTA]+chosen],hi.loc[[VISTA]+chosen],tax,weights)
        if stages.empty: st.info("No workflow-stage mapping; inspect the methodology.");return
        stages["Product"]=stages["Product ID"].map(names)
        bottleneck["Product"]=bottleneck["Product ID"].map(names)
        stages["Uncertainty"]=stages.Upper-stages.Lower
        stages["Zero"]=0.
        fig=px.bar(stages,x="Stage",y="Lower",color="Product",barmode="group",error_y="Uncertainty",error_y_minus="Zero",hover_data=["Upper","Criterion IDs"])
        fig.update_layout(yaxis={"range":[0,1.05],"tickformat":".0%","title":"Stage criterion coverage"},height=450)
        plot(st,fig,use_container_width=True)
        table(st,stages,"workflow-stages")
        table(st,bottleneck,"workflow-bottlenecks")
        context=workflow_context(lo.loc[[VISTA]+chosen],hi.loc[[VISTA]+chosen],tax,weights)
        if not context.empty:
            context["Product"]=context["Product ID"].map(names)
            st.subheader("Cross-cutting / unassigned workflow criteria")
            table(st,context,"workflow-context")
            st.caption("These criteria remain in the overall benchmark but are not forced into a process stage. Review the mapping before interpreting the stage bottleneck.")
        st.caption("Stages may share criteria. The weakest-stage interval identifies a potential coverage bottleneck. All mapped criteria bounds use the minimum criterion score (a conjunctive coverage proxy), not an average or proof of workflow integration. No full workflow qualification is claimed.")
        with st.expander("Workflow integration evidence to review"):
            for p in chosen:
                st.markdown("**"+names[p]+"**")
                table(st,pd.DataFrame([r for r in data.get("Deployments",{}).get("rows",[]) if value(r,"Product ID")==p]),"workflow-deploy-"+p)
    else:
        st.subheader("Criterion-to-dimension and workflow mapping")
        table(st,tax,"taxonomy")
        st.caption("Provisional generic label rules. All source criteria appear in the overall score. Unknown group assignments remain visible rather than being silently discarded.")
        cid=st.selectbox("Optional local mapping override",tax["Criterion ID"].tolist(),format_func=tax.set_index("Criterion ID").Criterion.to_dict().get,key="pos-map-edit")
        row=tax[tax["Criterion ID"]==cid].iloc[0]
        prof=dict(cfg.get("command_profiles",{}).get(cid,{}))
        with st.form("pos-settings-"+cid):
            dim=st.selectbox("Strategic dimension",DIMENSIONS,index=DIMENSIONS.index(row.Dimension))
            stages=st.multiselect("Workflow stages",WORKFLOWS,default=[s for s in WORKFLOWS if s in row["Workflow stages"].split("; ")])
            importance=["Unknown","Low","Medium","High"]
            current_importance=prof.get("customer_importance","Unknown")
            imp=st.selectbox("Customer importance (optional estimate)",importance,index=importance.index(current_importance) if current_importance in importance else 0)
            saved=st.form_submit_button("Save local mapping and importance",disabled=demo_mode)
        if saved:
            d=dict(cfg.get("positioning_dimensions",{}));d[cid]=dim
            w=dict(cfg.get("positioning_workflows",{}));w[cid]=stages
            profiles=dict(cfg.get("command_profiles",{}));prof["customer_importance"]=imp;profiles[cid]=prof
            save_settings({"positioning_dimensions":d,"positioning_workflows":w,"command_profiles":profiles});st.rerun()
        st.subheader("Optional AIT-VISTA commercial baseline")
        st.caption("No implementation evidence needed. Commercial inputs are independent of declared functionality and default to unknown.")
        own=cfg.get("positioning_vista_commercial",{})
        def opt(options,key,label):
            val=own.get(key,"Unknown")
            return st.selectbox(label,options,index=options.index(val) if val in options else 0)
        with st.form("pos-commercial"):
            status=opt(["Unknown","Commercial","Announced","Research","Historical","Internal / custom"],"commercial_status","Commercial availability")
            space=opt(["Unknown","Space offering","Space manufacturing deployment","Space AIT deployment","Space manufacturing adoption signal","Space AIT R&D","Space AIT R&D heritage","Space industry only","Planned space application"],"space_applicability","Space applicability")
            adoption=opt(["Unknown","Reported implementation","Documented implementation"],"adoption","Adoption status (team declaration)")
            save=st.form_submit_button("Save optional commercial baseline",disabled=demo_mode)
        if save:
            save_settings({"positioning_vista_commercial":{"commercial_status":status,"space_applicability":space,"adoption":adoption}});st.rerun()
