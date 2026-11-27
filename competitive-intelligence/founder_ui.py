"""Founder-oriented navigation and profiles; advanced analytics remain intact."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from chart_theme import plot, tokens, role_colors, action_colors, reference_marker, rival_marker, heatmap_colors, colors as chart_colors
from core import value,connect,read_snapshot
from command_engine import registry,direct_matrix,profile,research_queue,comparison_changes,ASSESS
from product_intelligence import CRITERIA
from positioning import taxonomy,interval_arrays,workflow_benchmark,VISTA,ALL
from founder import summaries,priority_families,strategic_criteria,profile_records,timeline,advantage_summary,evidence_detail,profile_findings,recorded_market_changes,brief_criteria,WORKFLOW_EXAMPLES,search_companies,short_reason,relationship_lane,commercial_summary
from excel_archive import download_analysis
from founder import strategic_map_cohort,map_exclusions,DEFAULT_MAP_SCOPE,MAP_SCOPES
from threat_watch import exposure,spread_points,short_criterion,selected_criteria,threat_cohort,exposure_records,headline_records,material_pairs,priority_records
from decision import CUSTOMER_LANES,FUNCTION_LANES,company_brief,differentiation_questions,signals,importance_lane

PRIMARY=["Command Centre","Competitor Explorer","Market Positioning","Competitive Advantage","Intelligence Monitor","Advanced Analytics"]

def navigate(st,pid=None,cid=None,page="Competitor Explorer",criterion=None,register=None,reference=None):
    st.session_state["founder_workspace"]=page
    if cid:
        st.session_state["founder_company_pending"]=cid
        st.session_state["founder-search"]=""
    if pid: st.session_state["founder_product_pending"]=pid
    if page=="Competitor Explorer":
        st.session_state["profile_section_pending"]={"Deployments":"Deployments","Commercial Intelligence":"Pricing","Observations":"Evidence"}.get(register,"Compare" if criterion else "Overview")
        st.session_state["profile_criterion_pending"]=criterion
        st.session_state["profile_reference_pending"]=(register,reference) if reference else None
        st.session_state.pop("profile_reference_active",None)

def chart_route(st,key,data,kind):
    event=st.session_state.get(key,{})
    pts=event.get("selection",{}).get("points",[])
    if not pts:return
    d=pts[0].get("customdata",[])
    if not d:return
    pid=d[0]
    if kind=="signal":
        if len(d)>3 and d[1]:navigate(st,pid or None,d[1],register=d[2],reference=d[3])
        return
    if pid==VISTA:return
    p=registry(data,"Products","Product ID").get(pid)
    if p:
        criterion=d[1] if kind in {"criterion","record"} and len(d)>1 else None
        reference=d[2] if kind=="record" and len(d)>2 else None
        navigate(st,pid,value(p,"Company ID"),criterion=criterion,register="Comparison Assessment" if reference else None,reference=reference)

def render_map(st,data,rows,key,compact=False):
    d=rows.copy()
    d["X"]=d["Functional overlap"].map(dict(zip(FUNCTION_LANES,range(4)))).astype(float)
    d["Y"]=d["Customer position"].map(dict(zip(CUSTOMER_LANES,range(4)))).astype(float)
    d=spread_points(d,reference=(3,2))
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=[3],y=[2],mode="markers+text",text=["AIT-VISTA"],textposition="top center",name="AIT-VISTA reference",customdata=[[VISTA]],marker=reference_marker(),hovertemplate="Declared scope / target; not market share<extra></extra>"))
    if not d.empty:
        rivals=px.scatter(d,x="Display X",y="Display Y",color="Role",color_discrete_map=role_colors(),hover_name="Product",custom_data=["Product ID"],hover_data={"Display X":False,"Display Y":False,"Functional overlap":True,"Customer position":True,"Customer basis":True,"Procurement":True})
        for tr in rivals.data:
            tr.update(marker=rival_marker(tr.name))
            fig.add_trace(tr)
    fig.add_hrect(y0=-.45,y1=.45,fillcolor=tokens()["band"],line_width=0,layer="below")
    fig.update_layout(height=340 if compact else 465,legend={"orientation":"h","y":-0.27,"font":{"size":10}},xaxis={"tickmode":"array","tickvals":list(range(4)),"ticktext":["Unresolved","Some","Material","Broad"],"range":[-.5,3.5],"title":"Recorded functional overlap","automargin":True},yaxis={"tickmode":"array","tickvals":list(range(4)),"ticktext":["Unresolved","Adjacent sector","Space AIT target","Space AIT case"],"range":[-.5,3.5],"title":"Customer evidence","automargin":True},margin={"t":12,"b":95,"l":15,"r":15})
    plot(st,fig,use_container_width=True,key=key,on_select=lambda:chart_route(st,key,data,"product"),selection_mode="points")
    if len(d)>0:
        st.caption("Dense points: use the product selector below the chart as an exact-ID fallback; zoom to inspect nearby points.")
        dense=d.groupby(["X","Y"]).size()
        if (dense>1).any():
            with st.expander("Inspect co-located products by category"):
                cells=[(x,y) for (x,y),n in dense.items() if n>1]
                cell=st.selectbox("Shared category",cells,format_func=lambda v:FUNCTION_LANES[int(v[0])]+" / "+CUSTOMER_LANES[int(v[1])],key=key+"-cell")
                select_product(st,d[(d.X==cell[0])&(d.Y==cell[1])],key+"-cell-product-"+str(cell),"Product in shared category")
    st.caption("Select a product to open its profile. Customer-segment evidence is independent of functional overlap; shared procurement remains unresolved. Positions are categories, not scores or market share. Display-only offsets separate co-located products; full names and categories appear on hover. Marker size is visual emphasis.")

def open_profile(st,pid,cid,key):
    st.button("Open profile",key="open-"+key,on_click=navigate,args=(st,pid,cid))

def table(st,d,key,export=False):
    st.dataframe(d,use_container_width=True,hide_index=True)
    if export and not d.empty: download_analysis(st,d,"founder-"+key,key)

def source_records(st,rows,key):
    if not rows: st.caption("No recorded evidence in this register.");return
    table(st,pd.DataFrame(rows),key,True)
    # Sources are kept as literal text in table; safe HTTP(S) links separately.
    urls=[]
    for r in rows:
        for f in ["Source URL","Source URLs","Product URL","Documentation URL","Website"]:
            raw=value(r,f)
            for u in raw.replace("\n",";").split(";"):
                u=u.strip()
                if u.startswith(("https://","http://")) and not any(ch.isspace() for ch in u) and u not in urls: urls.append(u)
    for i,u in enumerate(urls[:20]): st.link_button("Source "+str(i+1),u)

def select_product(st,rows,key,label="Inspect product",default=None):
    if rows.empty:return None
    names={r["Product ID"]:r["Company"]+" · "+r["Product"] for r in rows.to_dict("records")}
    p=st.selectbox(label,list(names),index=list(names).index(default) if default in names else 0,format_func=names.get,key="pick-"+key+("-"+default if default in names else ""))
    r=rows[rows["Product ID"]==p].iloc[0]
    open_profile(st,p,r["Company ID"],key)
    return p

def detail(st,data,pid,cid,key):
    verdict,active,history=evidence_detail(data,pid,cid)
    criterion=registry(data,CRITERIA,"Criterion ID").get(cid,{})
    st.markdown("**"+value(criterion,"Product criterion")+" — "+verdict+"**")
    if value(criterion,"Type"): st.caption("Criterion type: "+value(criterion,"Type"))
    if not active: st.caption("No direct assessment. This is not evidence of non-support.")
    else:
        for i,r in enumerate(active):
            with st.container(border=True):
                st.caption(" · ".join(value(r,k) for k in ["Comparison ID","Evidence level","Assessment date"] if value(r,k)))
                st.write(value(r,"Assessment rationale") or "Rationale not recorded.")
                st.caption("Limitations: "+(value(r,"Limitations") or "Not recorded"))
                for j,u in enumerate(value(r,"Source URLs").replace("\n",";").split(";")):
                    u=u.strip()
                    if u.startswith(("https://","http://")) and not any(ch.isspace() for ch in u):st.link_button("Source: "+u.split("/")[2]+" ("+str(i+1)+"."+str(j+1)+")",u)
        with st.expander("Original active records"):source_records(st,active,key+"-active")
    with st.expander("Assessment history / superseded evidence"):
        source_records(st,history,key+"-history")

def heatmap(st,data,cfg,rows,key,ids=None,stage_labels=None):
    criteria=registry(data,CRITERIA,"Criterion ID")
    ids=ids or brief_criteria(data)
    if not ids or rows.empty: st.info("Direct comparison criteria or products unavailable.");return
    ps=rows["Product ID"].tolist()
    mat=direct_matrix(data,ps,ids)
    names=rows.set_index("Product ID").Product.to_dict()
    # Keep all distinct evidence states available in hover.
    states=["Explicitly unsupported","Unassessed","Unknown","Disputed","Not applicable","Announced","Partially supported","Supported"]
    colors=[heatmap_colors()[s] for s in states]
    code={v:i for i,v in enumerate(states)}
    labels=[stage_labels.get(c,short_criterion(c,value(criteria[c],"Product criterion"))) if stage_labels else short_criterion(c,value(criteria[c],"Product criterion")) for c in ids]
    mat.loc[VISTA]=[profile(cfg,c,"As-Is") for c in ids]
    mat=mat.loc[[VISTA]+ps]
    marks={"Supported":"Full","Partially supported":"Partial","Explicitly unsupported":"No","Unassessed":"—","Unknown":"?","Announced":"A","Disputed":"!","Not applicable":"N/A"}
    # Scatter-square heatmap enables native point selection and evidence drill-down.
    cells=[(j,i,p,c,mat.loc[p,c]) for i,c in enumerate(ids) for j,p in enumerate([VISTA]+ps)]
    current_labels=["AIT-VISTA"]+[names[p] for p in ps]
    fig=go.Figure(go.Scatter(x=[v[0] for v in cells],y=[v[1] for v in cells],mode="markers+text",
        marker={"symbol":"square","size":36,"opacity":0.01},
        text=[marks.get(v[4],"Unknown") for v in cells],textfont={"color":tokens()["text"],"size":13},textposition="middle center",
        customdata=[[v[2],v[3],v[4],current_labels[v[0]],value(criteria[v[3]],"Product criterion")] for v in cells],
        hovertemplate="%{customdata[3]}<br>%{customdata[4]}<br>%{customdata[2]}<extra></extra>"))
    for j,i,p,c,s in cells:
        fig.add_shape(type="rect",x0=j-.46,x1=j+.46,y0=i-.38,y1=i+.38,fillcolor=colors[code.get(s,1)],line={"width":0},layer="below")
    fig.update_layout(height=max(320,40*len(ids)+100),plot_bgcolor=tokens()["plot"],paper_bgcolor=tokens()["background"],xaxis={"tickmode":"array","tickvals":list(range(len(current_labels))),"ticktext":[n if len(n)<=18 else n[:15]+"…" for n in current_labels],"tickangle":-30,"automargin":True,"range":[-.6,len(current_labels)-.4]},yaxis={"tickmode":"array","tickvals":list(range(len(labels))),"ticktext":labels,"automargin":True,"range":[len(labels)-.5,-.5]},margin={"l":15,"r":15,"t":15,"b":80})
    chartkey="heat-"+key
    plot(st,fig,use_container_width=True,key=chartkey,on_select=lambda:chart_route(st,chartkey,data,"criterion"),selection_mode="points")
    pc=ps[0] if key=="profile" else None
    pending=st.session_state.pop("profile_criterion_pending",None) if key=="profile" else None
    cc=pending if pending in ids else None
    st.caption("Full = Supported · Partial = Partially supported · No = explicitly unsupported · ? = Unknown · — = Not assessed · ! = Disputed · A = Announced. Select a cell for full criterion, source and evidence. Vendor claims remain visible.")
    p=pc if key=="profile" else select_product(st,rows,key+"-profile","Inspect comparison product",pc)
    ck="heat-c-"+key
    if cc:st.session_state[ck]=cc
    elif st.session_state.get(ck) not in ids:st.session_state[ck]=ids[0]
    c=st.selectbox("Inspect criterion evidence",ids,format_func=lambda c:value(criteria[c],"Product criterion"),key=ck)
    if p:
        with st.expander("Selected cell — evidence and source",expanded=bool(pc)):
            detail(st,data,p,c,key+"-evidence")
    with st.expander("Full comparison values"):
        table(st,mat.rename(index={VISTA:"AIT-VISTA",**names},columns=dict(zip(ids,labels))).rename_axis("Product").reset_index(),key+"-matrix",True)

def explorer(st,data,cfg,rows):
    st.header("Competitor Explorer")
    companies=registry(data,"Companies","Company ID")
    products=registry(data,"Products","Product ID")
    if not companies:st.info("No companies available.");return
    q=st.text_input("Search companies, products or technologies",key="founder-search").strip().lower()
    names={c:value(r,"Company Name") for c,r in companies.items()}
    ids=search_companies(data,q)
    if not ids: st.info("No matching company.");return
    pending=st.session_state.pop("founder_product_pending",None)
    target=st.session_state.pop("founder_company_pending",None)
    existing=target or st.session_state.get("founder_company")
    if existing not in ids: existing=ids[0]
    st.session_state["founder_company"]=existing
    cid=st.selectbox("Company",ids,format_func=names.get,key="founder_company")
    co=companies[cid]
    st.title(names[cid])
    st.caption(" · ".join(v for v in [value(co,"Country"),value(co,"Organisation Type"),value(co,"Ownership")] if v))
    if value(co,"Website").startswith(("https://","http://")):st.link_button("Company website",value(co,"Website"))
    if value(co,"Notes"):st.write(value(co,"Notes"))
    company_rows=rows[rows["Company ID"]==cid] if not rows.empty else rows
    if company_rows.empty:st.info("No product record for this company.");return
    names_p=company_rows.set_index("Product ID").Product.to_dict()
    options=list(names_p)
    if pending in options:st.session_state["founder-product-"+cid]=pending
    pid=st.selectbox("Product / module",options,format_func=names_p.get,key="founder-product-"+cid)
    p=products[pid];r=company_rows[company_rows["Product ID"]==pid].iloc[0]
    brief=company_brief(data,cid)
    with st.container(border=True):
        st.markdown("**Company business and portfolio**")
        st.write(" · ".join(dict.fromkeys(value(x,"Primary Use Case") or value(x,"Product Description") for x in brief["Products"] if value(x,"Primary Use Case") or value(x,"Product Description"))) or "Business description not recorded.")
        st.caption("Products: "+", ".join(value(x,"Product Name") for x in brief["Products"]))
        st.caption("Commercial positioning: "+"; ".join(dict.fromkeys(value(x,"Commercial Status") or "Unknown" for x in brief["Products"])))
    st.subheader(r.Product)
    st.markdown("**"+r["Review track"]+"**")
    st.write(value(p,"Product Description") or value(p,"Primary Use Case") or "Product description not recorded.")
    records=profile_records(data,pid)
    cards=st.columns(3)
    with cards[0]:
        with st.container(border=True):
            st.markdown("**Customers / cases**")
            customers=list(dict.fromkeys(value(x,"Customer Organisation") for x in records["Deployments"] if value(x,"Customer Organisation") and value(x,"Deployment Status") in {"Documented implementation","Reported implementation"}))
            st.write(", ".join(customers) if customers else "No customer implementation cases recorded.")
            other=[x for x in records["Deployments"] if value(x,"Deployment Status") not in {"Documented implementation","Reported implementation"}]
            if other:st.caption("Additional demonstration / other records: "+str(len(other))+" (see Deployments).")
            st.caption(value(p,"Target Customers") or "Target customer not recorded.")
    with cards[1]:
        with st.container(border=True):
            st.markdown("**Architecture**")
            st.write(value(p,"Deployment Architecture") or "Not recorded")
            st.caption(value(p,"Space Industry Applicability") or "Space applicability unresolved.")
    with cards[2]:
        with st.container(border=True):
            st.markdown("**Commercial model**")
            st.write(commercial_summary(records)[0])
            st.caption("See Pricing for basis, dates and implementation limitations.")
    a,b=st.columns(2)
    with a:
        st.markdown("**Why it matters**")
        st.write(r["Why care"])
        st.markdown("**Decision affected**")
        st.write(r.Decision)
    with b:
        st.markdown("**What needs confirmation**")
        st.write(r.Unresolved)
        st.caption(r["Customer basis"])
        st.caption(r.Procurement)
    if value(p,"Product URL").startswith(("https://","http://")):st.link_button("Product website",value(p,"Product URL"))
    findings=profile_findings(data,cfg,pid)
    with st.expander("Strategic strengths, differences and unresolved questions"):
        for heading,items in findings.items():
            st.markdown("**"+heading+"**")
            if items:
                for item in items: st.write("• "+item)
            else: st.caption("None established in the strategic comparison set.")
        st.caption("Partial support is a categorical scope difference, not measured performance. Weak evidence does not establish a competitor weakness.")
    records=profile_records(data,pid)
    pending_section=st.session_state.pop("profile_section_pending",None)
    if pending_section:st.session_state["profile-section"]=pending_section
    section=st.radio("Profile section",["Overview","Products","Compare","Deployments","Pricing","Evidence","Timeline"],horizontal=True,key="profile-section")
    incoming=st.session_state.pop("profile_reference_pending",None)
    if incoming:st.session_state["profile_reference_active"]=(cid,pid,incoming)
    reference_record=st.session_state.get("profile_reference_active")
    reference=reference_record[2] if reference_record and reference_record[:2]==(cid,pid) else None
    if reference and reference[0] in records:
        field={"Observations":"Observation ID","Deployments":"Deployment ID","Commercial Intelligence":"Commercial Record ID","Comparison Assessment":"Comparison ID"}.get(reference[0])
        exact=[x for x in records[reference[0]] if field and value(x,field)==reference[1]]
        if exact:
            st.markdown("**Selected evidence record**")
            source_records(st,exact,"selected-reference")
        else:st.info("The selected source record is not linked to this product; inspect the company evidence.")

    if section=="Overview":
        st.write(value(p,"Primary Use Case") or "Primary use case not recorded.")
        st.caption("Target industries: "+(value(p,"Target Industries") or "Not recorded"))
        with st.expander("Original company and product records"):source_records(st,[co,p],"source-profile")
    elif section=="Products":
        table(st,company_rows[["Product","Role","Commercial status","Family ID"]],"portfolio")
    elif section=="Compare":
        selected_criterion=st.session_state.get("profile_criterion_pending")
        all_ids=list(registry(data,CRITERIA,"Criterion ID"))
        if selected_criterion and selected_criterion not in brief_criteria(data):st.session_state["profile-all"]=True
        heatmap(st,data,cfg,company_rows[company_rows["Product ID"]==pid],"profile",all_ids if st.checkbox("Show all criteria",key="profile-all") else None)
    elif section=="Deployments":
        source_records(st,records["Deployments"],"deployments")
    elif section=="Pricing":
        source_records(st,records["Commercial Intelligence"],"commercial")
        st.caption("Missing price or cost is unknown, not zero.")
    elif section=="Evidence":
        for tab in ["Observations","Key Competitors","Capability Assessment","Comparison Assessment"]:
            with st.expander(tab):source_records(st,records[tab],"profile-"+tab)
    else:
        t=timeline(data)
        t=t[(t["Company ID"]==cid)&(t["Product ID"].isin(["",pid]))]
        st.caption("Company observations may concern other products; check the source. Recorded dates are not necessarily release dates.")
        table(st,t,"profile-timeline",True)

def positioning(st,data,cfg,rows):
    st.header("Market Positioning")
    st.caption("Which products address similar AIT workflows and have credible space-market relevance?")
    if rows.empty:return
    f=priority_families(rows)
    scope=st.selectbox("Market map scope",MAP_SCOPES+["Custom selection"],key="market-map-scope")
    candidates=strategic_map_cohort(rows,scope)
    names=rows.set_index("Product ID").Product.to_dict()
    default=strategic_map_cohort(rows)["Product ID"].tolist()
    if scope=="Custom selection":
        ids=st.multiselect("Products on strategic map",list(names),default=default,format_func=names.get,key="market-custom-products")
    else:ids=candidates["Product ID"].tolist()
    st.session_state["founder-map-products"]=ids
    d=rows[rows["Product ID"].isin(ids)].copy()
    render_map(st,data,d,"founder-map")
    st.caption(f"{len(d)} of {len(rows)} product records shown. Hidden products are not assessed as low threat.")
    if d.empty:return
    select_product(st,d,"map")
    with st.expander("Map exclusions"):
        excluded=map_exclusions(rows,d,scope)
        if excluded.empty:st.caption("All products included.")
        else:table(st,excluded[["Company","Product","Role","Reason not shown"]],"market-map-exclusions")
    st.subheader("AIT workflow coverage")
    criteria=registry(data,CRITERIA,"Criterion ID")
    stages={c:label for label,c in WORKFLOW_EXAMPLES if c in criteria}
    if stages:
        workflow_ids=st.multiselect("Workflow products",ids,default=ids[:6],format_func=names.get,key="workflow-products-"+str(scope))
        heatmap(st,data,cfg,d[d["Product ID"].isin(workflow_ids)],"workflow",list(stages),stage_labels=stages)
        st.caption("Selected criterion examples by workflow stage, not proof of complete or integrated stage coverage.")
    else:
        st.info("Workflow example criteria are absent in this snapshot. Open Advanced Analytics for mapped stage coverage.")

def advantage(st,data,cfg,rows):
    st.header("Competitive Advantage")
    if rows.empty:return
    f=priority_families(rows)
    candidates=f[f.Order<4]
    default=threat_cohort(data,rows)["Product ID"].tolist()
    names=rows.set_index("Product ID").Product.to_dict()
    ids=st.multiselect("Competitors to benchmark",list(names),default=default,format_func=names.get,key="founder-adv-products")
    selected=rows[rows["Product ID"].isin(ids)]
    if selected.empty:st.info("Select competitors.");return
    st.subheader("Strategic capability heatmap")
    tax=taxonomy(data,cfg)
    dims=["Strategic selection","All criteria"]+list(dict.fromkeys(tax.Dimension))
    group=st.selectbox("Capability group",dims,key="adv-group")
    cids=list(registry(data,CRITERIA,"Criterion ID")) if group=="All criteria" else tax.loc[tax.Dimension==group,"Criterion ID"].tolist() if group!="Strategic selection" else brief_criteria(data)
    order=st.selectbox("Criterion order",["Strategic order","Name"],key="adv-sort")
    if order=="Name":cids=sorted(cids,key=lambda c:value(registry(data,CRITERIA,"Criterion ID")[c],"Product criterion"))
    heatmap(st,data,cfg,selected,"advantage",cids)
    st.subheader("Response priority map")
    response_view(st,data,cfg,selected,"adv-response")
    st.subheader("Differentiation portfolio")
    d=advantage_summary(data,cfg,ids)
    if d.empty:st.info("No comparable evidence.");return
    d["Importance evidence"]=d["Criterion ID"].map(lambda c:importance_lane(cfg,c))
    # Separate unresolved lane: no invented y score or implied customer value.
    d["Functional finding"]=d.Finding
    d["Display criterion"]=d.Criterion
    fig=px.scatter(d,x="Functional finding",y="Display criterion",color="Importance evidence",hover_data=["Delta lower","Delta upper","Rarity lower","Rarity upper","Customer demand"],custom_data=["Criterion ID"])
    fig.update_layout(height=max(430,24*len(d)+120),xaxis_title="Evidence-bounded functional finding",yaxis_title="",legend={"orientation":"h"})
    event=plot(st,fig,use_container_width=True,key="adv-findings-plot",on_select="rerun",selection_mode="points")
    points=event.selection.points if event is not None and hasattr(event,"selection") else []
    chosen=points[0].get("customdata",[]) if points else []
    if chosen:
        st.write("Selected criterion: "+value(registry(data,CRITERIA,"Criterion ID").get(chosen[0],{}),"Product criterion"))
        for _,r in selected.iterrows():
            st.button("Inspect "+r.Product,key="adv-point-"+r["Product ID"],on_click=navigate,args=(st,r["Product ID"],r["Company ID"],"Competitor Explorer",chosen[0]))
    mapped=d[d["Importance evidence"]!="Unresolved"].copy()
    if mapped.empty:st.info("Customer importance unresolved: the visual portfolio shows functional findings only. No commercial advantage score is invented.")
    else:
        mapped["Width"]=mapped["Rarity upper"]-mapped["Rarity lower"];mapped["Zero"]=0.
        fig=px.scatter(mapped,x="Rarity lower",y="Importance evidence",color="Finding",hover_name="Criterion",error_x="Width",error_x_minus="Zero")
        fig.update_layout(xaxis={"range":[0,1.05],"tickformat":".0%","title":"Evidence-bounded differentiation rarity"},yaxis={"categoryorder":"array","categoryarray":["Low","Medium","High"]})
        plot(st,fig,use_container_width=True)
    with st.expander("Portfolio evidence and decisions"):table(st,d[["Criterion","Finding","Importance evidence","Customer demand","Decision"]],"advantage-findings",True)
    st.caption("Functional advantage is conditional on the selected cohort and evidence. Unknown competitor scope and unvalidated importance do not establish commercial advantage.")
    select_product(st,selected,"adv-portfolio")

def monitor(st,data,cfg,rows,snapshots,current,demo):
    st.header("Intelligence Monitor")
    st.subheader("Latest recorded developments")
    t=signals(data)
    names=registry(data,"Companies","Company ID");pro=registry(data,"Products","Product ID")
    t["Company"]=t["Company ID"].map(lambda c:value(names.get(c,{}),"Company Name"))
    t["Product"]=t["Product ID"].map(lambda p:value(pro.get(p,{}),"Product Name"))
    types=st.multiselect("Development types",list(t["Date basis"].unique()),default=list(t["Date basis"].unique()),key="monitor-types")
    filtered=t[t["Date basis"].isin(types)]
    plot=filtered.copy()
    plot["Parsed date"]=pd.to_datetime(plot.Date,format="mixed",errors="coerce",utc=True)
    plot=plot[plot["Parsed date"].notna()].head(100)
    if not plot.empty:
        fig=px.scatter(plot,x="Parsed date",y="Company",color="Date basis",hover_name="Product",custom_data=["Product ID","Company ID","Register","Reference"],hover_data=["Date","Development","Strategic implication","Discovery / review date"])
        fig.update_layout(height=max(330,24*plot.Company.nunique()+120),xaxis_title="Recorded or reported date",yaxis_title="")
        plot(st,fig,use_container_width=True,key="monitor-timeline-plot",on_select=lambda:chart_route(st,"monitor-timeline-plot",data,"signal"),selection_mode="points")
    table(st,filtered[["Date","Date basis","Discovery / review date","Company","Product","Development","Strategic implication","Limitations","Source"]].head(50),"timeline",True)
    with st.expander("Full research and assessment history"):table(st,timeline(data),"raw-timeline",True)
    if not rows.empty:select_product(st,rows,"timeline")
    st.caption("Default signals prioritise reported deployments, commercial information and observations with explicit strategic implications. Dates are labelled by type; records are not necessarily new market events.")
    if not demo and len(snapshots)>1:
        options=[s for s in snapshots if s[0]!=current]
        if options:
            old=st.selectbox("Compare against saved snapshot",[s[0] for s in options],format_func=lambda h:next(s[1] for s in options if s[0]==h),key="monitor-snapshot")
            with connect() as conn:before=read_snapshot(conn,old)
            if before:
                ch=comparison_changes(before,data)
                if not ch.empty:
                    ch=ch[(ch["Before"]!=ch["After"])|(ch["Evidence before"]!=ch["Evidence after"])]
                if ch.empty:st.info("No material recorded verdict or evidence-level changes.")
                else:
                    ch["Product"]=ch["Product ID"].map(lambda p:value(pro.get(p,{}),"Product Name"))
                    table(st,ch,"recorded-changes",True)
                    select_product(st,rows[rows["Product ID"].isin(ch["Product ID"])],"changes")
                st.subheader("Recorded commercial, deployment and positioning changes")
                changes=recorded_market_changes(before,data)
                if changes.empty:st.info("No new or revised commercial, deployment or selected positioning records.")
                else:
                    table(st,changes,"market-changes",True)
                    select_product(st,rows[rows["Product ID"].isin(changes["Product ID"])],"market-changes")
    st.subheader("Research priorities")
    if not rows.empty and registry(data,CRITERIA,"Criterion ID"):
        stamp=next((s[1] for s in snapshots if s[0]==current),"")
        q=research_queue(data,direct_matrix(data),cfg,stamp)
        if not q.empty:
            view=q.copy();view["Product"]=view["Product ID"].map(lambda p:value(pro.get(p,{}),"Product Name"))
            table(st,view[["Product","Research question","Strategic decision affected","Reason for uncertainty"]].head(15),"research-preview")
            download_analysis(st,q,"founder-research","priority-research")
            st.download_button("Export complete research queue CSV",q.to_csv(index=False).encode(),file_name="priority-research.csv",key="founder-research-csv")
            select_product(st,rows[rows["Product ID"].isin(q.head(15)["Product ID"])],"research")

def response_view(st,data,cfg,rows,key,cids=None):
    e=exposure(data,cfg,rows["Product ID"].tolist(),cids)
    if e.empty:return
    xs=["No positive record / unresolved","Partial recorded","Full recorded"]
    ys=["Unresolved","Low","Medium","High"]
    e["X"]=e.Overlap.map(dict(zip(xs,range(len(xs)))))
    e["Y"]=e.Importance.map(dict(zip(ys,range(len(ys)))))
    points=spread_points(e,radius=.30)
    fig=px.scatter(points,x="Display X",y="Display Y",color="Action",color_discrete_map=action_colors(),hover_name="Criterion",custom_data=["Product ID","Criterion ID","Comparison ID"],hover_data={"Display X":False,"Display Y":False,"Overlap":True,"Importance":True,"Product":True,"Verdict":True,"Evidence":True,"Assessment date":True,"Next decision":True})
    fig.update_traces(marker={"size":14,"opacity":1,"line":{"width":1.7,"color":tokens()["outline"]}})
    fig.update_layout(height=340,xaxis={"tickmode":"array","tickvals":list(range(3)),"ticktext":["Unresolved","Partial","Full"],"range":[-.5,2.5],"title":"Recorded overlap"},yaxis={"tickmode":"array","tickvals":list(range(4)),"ticktext":ys,"range":[-.5,3.5],"title":"Customer importance"},legend={"orientation":"h"})
    plot(st,fig,use_container_width=True,key=key,on_select=lambda:chart_route(st,key,data,"record"),selection_mode="points")
    st.caption("Unresolved importance is separate. React requires high provenance-bearing importance and technical-or-stronger positive evidence; Benchmark / Research / Monitor are action categories, not risk percentages.")
    c=st.selectbox("Inspect response criterion",e["Criterion ID"].tolist(),format_func=e.set_index("Criterion ID")["Short criterion"].to_dict().get,key=key+"-criterion")
    r=e[e["Criterion ID"]==c].iloc[0]
    st.write(r.Action+" — "+r["Next decision"])
    if r["Product ID"]:
        p=registry(data,"Products","Product ID")[r["Product ID"]]
        st.button("Open exact criterion evidence",key=key+"-open",on_click=navigate,args=(st,r["Product ID"],value(p,"Company ID"),"Competitor Explorer",c,"Comparison Assessment",r["Comparison ID"]))
    with st.expander("All response recommendations"):table(st,e[["Short criterion","Product","Verdict","Evidence","Importance","Action","Next decision"]],key+"-table",True)

def threat_view(st,data,cfg,rows,before=None):
    st.subheader("Threat Watch")
    cohort=threat_cohort(data,rows)
    names=rows.set_index("Product ID").Product.to_dict()
    ids=st.multiselect("Threat Watch products",list(names),default=cohort["Product ID"].tolist(),format_func=names.get,key="threat-products")
    selected=rows[rows["Product ID"].isin(ids)]
    all_criteria=list(registry(data,CRITERIA,"Criterion ID"))
    cids=all_criteria if st.checkbox("All 34 criteria",key="threat-all") else selected_criteria(data)
    st.caption(f"{len(ids)} of {len(rows)} products · {len(cids)} criteria across headlines, heatmap and response map. Provisional review order, not a threat probability.")
    if selected.empty:return
    with st.expander("Products outside this Threat Watch cohort"):
        table(st,rows[~rows["Product ID"].isin(ids)][["Company","Product","Role"]],"threat-omitted")
    records=exposure_records(data,cfg,ids,cids)
    changes=material_pairs(before,data)
    if not records.empty:
        for i,(_,r) in enumerate(headline_records(records,changes).iterrows()):
            p=registry(data,"Products","Product ID")[r["Product ID"]]
            with st.container(border=True):
                a,b=st.columns([4,1])
                with a:
                    st.markdown("**"+r.Action+" · "+r["Short criterion"]+" — "+r.Product+"**")
                    st.caption(" · ".join(x for x in [r.Verdict,r.Evidence,r["Assessment date"],r["Comparison ID"]] if x))
                    st.write(r["Next decision"])
                    if r["Material recorded change"]:st.caption("Verdict or evidence changed since prior saved snapshot (recorded knowledge).")
                with b:st.button("Evidence",key="threat-head-"+str(i),on_click=navigate,args=(st,r["Product ID"],value(p,"Company ID"),"Competitor Explorer",r["Criterion ID"],"Comparison Assessment",r["Comparison ID"] or None))
        with st.expander("All relevant products, alternate verdicts and unresolved comparisons"):
            ranked=priority_records(records,changes)
            table(st,ranked[["Product","Short criterion","Verdict","Record verdict","Evidence","Assessment date","Comparison ID","Importance","Action","Material recorded change","Limitations","Source"]],"threat-records",True)
            labels={i:r.Product+" | "+r["Short criterion"]+" | "+r["Record verdict"]+" | "+(r["Comparison ID"] or "Not assessed") for i,r in ranked.reset_index(drop=True).iterrows()}
            idx=st.selectbox("Inspect exact comparison",list(labels),format_func=labels.get,key="threat-exact")
            r=ranked.reset_index(drop=True).iloc[idx];p=registry(data,"Products","Product ID")[r["Product ID"]]
            st.button("Open selected evidence",key="threat-exact-open",on_click=navigate,args=(st,r["Product ID"],value(p,"Company ID"),"Competitor Explorer",r["Criterion ID"],"Comparison Assessment",r["Comparison ID"] or None))
    budget=selected[selected.Role=="Workflow / procurement substitute candidate"]
    if not budget.empty:
        r=budget.iloc[0]
        with st.container(border=True):
            st.markdown("**Research · potential budget substitution — "+r.Product+"**")
            st.write(r["Customer basis"]);st.caption(r.Procurement+" "+r.Decision)
            open_profile(st,r["Product ID"],r["Company ID"],"threat-budget")
    st.caption("Functional overlap and procurement substitution are separate. Full support is not performance equivalence.")
    heatmap(st,data,cfg,selected,"threat",cids)
    response_view(st,data,cfg,selected,"threat-response",cids)

def landing(st,data,cfg,rows,snapshots,current,demo):
    st.header("Competitive Command Centre")
    st.caption("What should 5PACE pay attention to today?")
    if rows.empty:st.info("No product records yet.");return
    f=priority_families(rows)
    stamp=next((x[1] for x in snapshots if x[0]==current),"Not captured")
    st.caption("Snapshot capture: "+("Synthetic demo (not stored)" if demo else stamp))
    cards=st.columns(4)
    visual=f[f.Order==0]
    tech=f[f.Order.isin([0,2])].sort_values(["Recorded overlap fraction","Technical or stronger"],ascending=False)
    target=visual[visual["Customer position"].isin(CUSTOMER_LANES[2:])]
    lead=tech.head(1)
    market=target[~target["Family ID"].isin(lead["Family ID"])]
    groups=[("Visual technology benchmark",lead,"Highest recorded overlap in selected visual / adjacent roles"),
            ("Market-facing visual candidates",market,"Recorded spacecraft target customers; adoption may be unresolved"),
            ("Budget substitution candidates",f[f.Order==1],"Workflow / purchasing alternatives; same budget unconfirmed"),
            ("Research / emerging watch",f[f.Role=="Research / emerging entrant"],"Research demonstrators and potential entrants; commercial offer unconfirmed")]
    for col,(title,g,caption) in zip(cards,groups):
        with col:
            with st.container(border=True):
                st.caption(title)
                st.markdown("**"+(" · ".join(g.Company.drop_duplicates().head(1)) if not g.empty else "Unresolved")+"**")
                st.caption(caption)
                if not g.empty:
                    first=g.iloc[0]
                    st.caption("Uncertainty: "+("Commercial offer" if title.startswith("Research") else "Shared buyer / actual scope"))
                    st.caption("Action: "+("Benchmark workflow" if title.startswith("Visual") else "Verify procurement" if title.startswith("Budget") else "Verify deployment and scope"))
                    open_profile(st,first["Product ID"],first["Company ID"],"strategic-card-"+title)
    st.subheader("Technology × customer positioning")
    scope=st.selectbox("Map scope",MAP_SCOPES,key="landing-map-scope")
    mapped=strategic_map_cohort(rows,scope)
    render_map(st,data,mapped,"landing-map",True)
    if not mapped.empty:select_product(st,mapped,"landing-map-fallback","Inspect mapped product")
    st.caption(f"{len(mapped)} of {len(rows)} product records shown. Default: Space AIT case OR Space AIT target OR material OR broad functional overlap. No role, family or rank exclusion. Hidden does not mean low threat.")
    with st.expander("Why are other products not on this map?"):
        excluded=map_exclusions(rows,mapped,scope)
        if excluded.empty:st.caption("All products are included.")
        else:
            table(st,excluded[["Company","Product","Role","Reason not shown"]],"map-exclusions")
            select_product(st,excluded,"excluded-map")
    prior=None
    if not demo:
        stamps=[s[0] for s in snapshots]
        if current in stamps and stamps.index(current)+1<len(stamps):
            try:
                with connect() as conn:prior=read_snapshot(conn,stamps[stamps.index(current)+1])
            except (ValueError,OSError):pass
    threat_view(st,data,cfg,rows,prior)
    left,right=st.columns([1.6,1])
    with left:
        st.subheader("Why watch these companies?")
        items=pd.concat([g.head(2) for _,g,_ in groups]).drop_duplicates("Family ID").head(7)
        if items.empty:items=f.head(4)
        for _,r in items.iterrows():
            with st.container(border=True):
                a,b=st.columns([3,1])
                with a:
                    st.markdown("**"+r.Company+" · "+r.Product+"**")
                    st.caption(r["Review track"])
                    st.write(short_reason(r))
                    st.caption(r.Decision)
                with b:open_profile(st,r["Product ID"],r["Company ID"],"landing-"+r["Product ID"])
        st.button("Open full company directory",on_click=navigate,args=(st,None,None,"Competitor Explorer"),key="landing-directory")
    with right:
        st.subheader("Recent strategic signals")
        t=signals(data)
        names=registry(data,"Companies","Company ID")
        latest=t.drop_duplicates("Company ID").head(4)
        if latest.empty:st.caption("No observations recorded.")
        for i,(_,r) in enumerate(latest.iterrows()):
            with st.container(border=True):
                st.markdown("**"+(value(names.get(r["Company ID"],{}),"Company Name") or "Observation")+"**")
                st.caption(r.Date+" · "+r["Date basis"])
                st.write(r.Development[:210]+("…" if len(r.Development)>210 else ""))
                st.caption("Decision: "+r["Strategic implication"][:190]+("…" if len(r["Strategic implication"])>190 else ""))
                with st.expander("Full signal and source"):
                    st.write(r.Development);st.write(r["Strategic implication"])
                    u=r.Source.strip()
                    if u.startswith(("https://","http://")) and not any(ch.isspace() for ch in u):st.link_button("Source: "+u.split("/")[2],u)
                if r["Company ID"] in names:st.button("Open profile",key="news-"+str(i),on_click=navigate,args=(st,r["Product ID"] or None,r["Company ID"],"Competitor Explorer",None,r.Register,r.Reference))
        st.button("Intelligence Monitor",on_click=navigate,args=(st,None,None,"Intelligence Monitor"),key="landing-monitor")
    st.caption("Qualitative review order, not a calibrated threat score. Full rationale, source dates and unresolved questions are in each profile.")
    st.subheader("Where we may differentiate")
    families=f[(f.Order<3)|(f.Role=="Research / emerging entrant")]["Family ID"].tolist()
    candidates=rows[rows["Family ID"].isin(families)]["Product ID"].tolist()
    if candidates and registry(data,CRITERIA,"Criterion ID"):
        d=advantage_summary(data,cfg,candidates)
        if not d.empty:
            strong=d[d.Finding=="Substantiated functional advantage"]
            if strong.empty:st.info("No cohort-wide substantiated functional advantage under the technical-evidence scenario. Differentiation is still possible.")
            else:table(st,strong[["Criterion","Finding","Decision"]],"verified-advantage")
            questions=differentiation_questions(data,["AV-CR-005","AV-CR-008","AV-CR-022","AV-CR-021"],candidates)
            if not questions.empty:
                for _,q in questions.iterrows():
                    with st.container(border=True):
                        st.markdown("**"+q.Criterion+"**")
                        st.write(q.Finding)
                        st.caption(q["Evidence needed"])
            else:
                potential=d[d.Finding.str.contains("Potential|Insufficient",regex=True)]
                table(st,potential[["Criterion","Finding","Decision"]].head(5),"potential-advantage")
    st.button("Explore competitive advantage",on_click=navigate,args=(st,None,None,"Competitive Advantage"),key="landing-adv")

def founder_page(st,page,data,cfg,snapshots,current,demo):
    rows=summaries(data)
    if ASSESS not in data:st.info("Direct comparison register absent in this snapshot. Company records remain available; sync a newer snapshot for benchmarking.")
    if page=="Command Centre":landing(st,data,cfg,rows,snapshots,current,demo)
    elif page=="Competitor Explorer":explorer(st,data,cfg,rows)
    elif page=="Market Positioning":positioning(st,data,cfg,rows)
    elif page=="Competitive Advantage":advantage(st,data,cfg,rows)
    else:monitor(st,data,cfg,rows,snapshots,current,demo)
