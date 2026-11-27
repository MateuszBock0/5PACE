"""Founder-oriented navigation and profiles; advanced analytics remain intact."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core import value,connect,read_snapshot
from command_engine import registry,direct_matrix,profile,research_queue,comparison_changes,ASSESS
from product_intelligence import CRITERIA
from positioning import taxonomy,interval_arrays,workflow_benchmark,VISTA,ALL
from founder import summaries,priority_families,strategic_criteria,profile_records,timeline,advantage_summary,evidence_detail,profile_findings,recorded_market_changes
from excel_archive import download_analysis

PRIMARY=["Command Centre","Competitor Explorer","Market Positioning","Competitive Advantage","Intelligence Monitor","Advanced Analytics"]

def navigate(st,pid=None,cid=None,page="Competitor Explorer"):
    st.session_state["founder_workspace"]=page
    if cid:
        st.session_state["founder_company"]=cid
        st.session_state["founder-search"]=""
    if pid: st.session_state["founder_product_pending"]=pid

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
    st.markdown("**Recorded verdict: "+verdict+"**")
    if not active: st.caption("No direct assessment. This is not evidence of non-support.")
    else: source_records(st,active,key+"-active")
    with st.expander("Assessment history / superseded evidence"):
        source_records(st,history,key+"-history")

def heatmap(st,data,cfg,rows,key,ids=None):
    criteria=registry(data,CRITERIA,"Criterion ID")
    ids=ids or strategic_criteria(data)
    if not ids or rows.empty: st.info("Direct comparison criteria or products unavailable.");return
    ps=rows["Product ID"].tolist()
    mat=direct_matrix(data,ps,ids)
    names=rows.set_index("Product ID").Product.to_dict()
    # Keep all distinct evidence states available in hover.
    states=["Explicitly unsupported","Unassessed","Unknown","Disputed","Not applicable","Announced","Partially supported","Supported"]
    colors=["#b45b60","#727c8c","#727c8c","#ad78b5","#656970","#819fc1","#d1a54e","#339779"]
    code={v:i for i,v in enumerate(states)}
    labels=[value(criteria[c],"Product criterion") for c in ids]
    mat.loc[VISTA]=[profile(cfg,c,"As-Is") for c in ids]
    mat=mat.loc[[VISTA]+ps]
    marks={"Supported":"✓","Partially supported":"~","Explicitly unsupported":"×","Announced":"A","Disputed":"!","Not applicable":"N/A"}
    # Scatter-square heatmap enables native point selection and evidence drill-down.
    cells=[(j,i,p,c,mat.loc[p,c]) for i,c in enumerate(ids) for j,p in enumerate([VISTA]+ps)]
    current_labels=["AIT-VISTA"]+[names[p] for p in ps]
    fig=go.Figure(go.Scatter(x=[v[0] for v in cells],y=[v[1] for v in cells],mode="markers+text",
        marker={"symbol":"square","size":32,"color":[colors[code.get(v[4],1)] for v in cells]},
        text=[marks.get(v[4],"?") for v in cells],textfont={"color":"white","size":14},textposition="middle center",
        customdata=[[v[2],v[3],v[4],current_labels[v[0]],labels[v[1]]] for v in cells],
        hovertemplate="%{customdata[3]}<br>%{customdata[4]}<br>%{customdata[2]}<extra></extra>"))
    fig.update_layout(height=max(350,42*len(ids)+100),xaxis={"tickmode":"array","tickvals":list(range(len(current_labels))),"ticktext":current_labels,"range":[-.6,len(current_labels)-.4]},yaxis={"tickmode":"array","tickvals":list(range(len(labels))),"ticktext":labels,"range":[len(labels)-.5,-.5]},margin={"l":15,"r":15,"t":15,"b":80})
    event=st.plotly_chart(fig,use_container_width=True,key="heat-"+key,on_select="rerun",selection_mode="points")
    points=event.selection.points if event is not None and hasattr(event,"selection") else []
    clicked=points[0].get("customdata",[]) if points else []
    pc=clicked[0] if len(clicked)>1 and clicked[0] in ps else None
    cc=clicked[1] if len(clicked)>1 and clicked[1] in ids else None
    st.caption("Select a cell to inspect its evidence. ✓ Supported · ~ Partial · × Explicitly unsupported · ? Unknown/unassessed · ! Disputed · A Announced · N/A Not applicable. Vendor claims remain visible.")
    p=select_product(st,rows,key+"-profile","Inspect comparison product",pc)
    c=st.selectbox("Inspect criterion evidence",ids,index=ids.index(cc) if cc else 0,format_func=lambda c:value(criteria[c],"Product criterion"),key="heat-c-"+key+("-"+cc if cc else ""))
    if p:detail(st,data,p,c,key+"-evidence")
    with st.expander("Full comparison values"):
        table(st,mat.rename(index={VISTA:"AIT-VISTA",**names},columns=dict(zip(ids,labels))).rename_axis("Product").reset_index(),key+"-matrix",True)

def explorer(st,data,cfg,rows):
    st.header("Competitor Explorer")
    companies=registry(data,"Companies","Company ID")
    products=registry(data,"Products","Product ID")
    if not companies:st.info("No companies available.");return
    q=st.text_input("Search companies, products or technologies",key="founder-search").strip().lower()
    names={c:value(r,"Company Name") for c,r in companies.items()}
    ids=[c for c in sorted(names,key=lambda c:names[c].lower()) if not q or q in names[c].lower() or any(q in " ".join(value(p,f) for f in ["Product Name","Product Category","Primary Use Case","Product Description"]).lower() for p in products.values() if value(p,"Company ID")==c)]
    if not ids: st.info("No matching company.");return
    pending=st.session_state.pop("founder_product_pending",None)
    existing=st.session_state.get("founder_company")
    if existing not in ids: st.session_state["founder_company"]=ids[0]
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
    st.subheader(r.Product)
    st.markdown("**"+r["Review track"]+"**")
    st.write(value(p,"Product Description") or value(p,"Primary Use Case") or "Product description not recorded.")
    a,b=st.columns(2)
    with a:
        st.markdown("**Why 5PACE should care**")
        st.write(r["Why care"])
        st.markdown("**What remains unconfirmed**")
        st.write(r.Unresolved)
        st.caption(r["Buyer / procurement overlap"])
    with b:
        st.markdown("**Target customers & deployment**")
        for f in ["Primary Use Case","Target Customers","Target Industries","Deployment Architecture","Commercial Status","Space Industry Applicability"]:
            st.write("**"+f+":** "+(value(p,f) or "Not recorded"))
    if value(p,"Product URL").startswith(("https://","http://")):st.link_button("Product website",value(p,"Product URL"))
    findings=profile_findings(data,cfg,pid)
    with st.expander("Strategic strengths, differences and unresolved questions",expanded=True):
        for heading,items in findings.items():
            st.markdown("**"+heading+"**")
            if items:
                for item in items: st.write("• "+item)
            else: st.caption("None established in the strategic comparison set.")
        st.caption("Partial support is a categorical scope difference, not measured performance. Weak evidence does not establish a competitor weakness.")
    records=profile_records(data,pid)
    tabs=st.tabs(["Portfolio & commercial","Head-to-head","Evidence & developments"])
    with tabs[0]:
        st.markdown("**Products and families**")
        table(st,company_rows[["Product","Role","Commercial status","Family ID"]],"portfolio")
        st.markdown("**Customer cases & deployments**")
        source_records(st,records["Deployments"],"deployments")
        st.markdown("**Business model, price & implementation**")
        source_records(st,records["Commercial Intelligence"],"commercial")
        st.caption("Missing pricing or adoption records are unknown, not zero.")
        with st.expander("Original company and product records"):
            source_records(st,[co,p],"source-profile")
    with tabs[1]:
        heatmap(st,data,cfg,company_rows[company_rows["Product ID"]==pid],"profile",list(registry(data,CRITERIA,"Criterion ID")) if st.checkbox("Show all criteria",key="profile-all") else None)
    with tabs[2]:
        t=timeline(data)
        t=t[(t["Company ID"]==cid)&(t["Product ID"].isin(["",pid]))]
        st.caption("Company observations may concern other products; check the source. Recorded dates are not necessarily release dates.")
        table(st,t,"profile-timeline",True)
        for tab in ["Observations","Key Competitors","Capability Assessment","Comparison Assessment"]:
            with st.expander(tab):source_records(st,records[tab],"profile-"+tab)

def positioning(st,data,cfg,rows):
    st.header("Market Positioning")
    st.caption("Which products address similar AIT workflows and have credible space-market relevance?")
    if rows.empty:return
    f=priority_families(rows)
    candidates=f[f.Order<4]
    default=(candidates if not candidates.empty else f).head(12)["Product ID"].tolist()
    names=rows.set_index("Product ID").Product.to_dict()
    ids=st.multiselect("Products on strategic map",list(names),default=default,format_func=names.get,key="founder-map-products")
    d=rows[rows["Product ID"].isin(ids)].copy()
    if d.empty:st.info("Select products to compare.");return
    # Ordinal categories, not an invented customer-overlap score.
    xs=["No positive record / unresolved","Some recorded overlap","Material recorded overlap","Broad recorded overlap"]
    ys=["Current space-market fit unresolved","Space offering","Space deployment / adoption signal","AIT-VISTA target market"]
    d["X"]=d["Functional overlap"].map(dict(zip(xs,range(len(xs)))))
    d["Y"]=d["Space market evidence"].map(dict(zip(ys,range(len(ys)))))
    # Offsets only separate labels sharing a category; no numeric inference.
    for _,g in d.groupby(["X","Y"]):
        for k,(idx,_) in enumerate(g.iterrows()):
            d.loc[idx,"X"]+=(k-(len(g)-1)/2)*min(.10,.6/max(1,len(g)-1))
    fig=px.scatter(d,x="X",y="Y",color="Role",hover_name="Product",custom_data=["Product ID"],hover_data={"X":False,"Y":False,"Company":True,"Functional overlap":True,"Space market evidence":True,"Buyer / procurement overlap":True,"Why care":True})
    fig.add_trace(go.Scatter(x=[3],y=[3],mode="markers+text",text=["AIT-VISTA"],textposition="bottom left",name="AIT-VISTA declared reference",marker={"symbol":"star","size":19,"color":"#39aa83"},hovertemplate="Declared scope and target segment, not proven customer adoption<extra></extra>"))
    fig.update_layout(xaxis={"tickmode":"array","tickvals":list(range(4)),"ticktext":xs,"range":[-.5,3.5],"title":"Recorded strategic functional overlap"},yaxis={"tickmode":"array","tickvals":list(range(4)),"ticktext":ys,"range":[-.4,3.5],"title":"Space-market evidence (proxy, not shared procurement)"},height=510)
    event=st.plotly_chart(fig,use_container_width=True,on_select="rerun",selection_mode="points",key="founder-map")
    points=event.selection.points if event is not None and hasattr(event,"selection") else []
    clicked=points[0].get("customdata",[]) if points else []
    if clicked and clicked[0] in ids:
        r=d[d["Product ID"]==clicked[0]].iloc[0]
        st.write(r["Why care"]);open_profile(st,r["Product ID"],r["Company ID"],"map-click")
    select_product(st,d,"map")
    st.caption("Categories use observed weighted overlap over strategic criteria (partial = 0.5; thresholds 1/3 and 2/3). Missing evidence can hide overlap, so this is not a true low-threat designation. Shared buyer/budget is unresolved unless separately investigated. The AIT-VISTA star is a declared reference, not market leadership.")
    st.subheader("AIT workflow coverage")
    tax=taxonomy(data,cfg)
    m=direct_matrix(data,ids)
    lo,hi,_,_=interval_arrays(data,m,cfg,"As-Is","All recorded verdicts")
    w,b=workflow_benchmark(lo,hi,tax)
    if not w.empty:
        w["Product"]=w["Product ID"].map({VISTA:"AIT-VISTA",**names})
        w["Unresolved"]=w.Upper-w.Lower;w["Zero"]=0.
        fig=px.bar(w,x="Stage",y="Lower",color="Product",barmode="group",error_y="Unresolved",error_y_minus="Zero",hover_data=["Upper"])
        fig.update_layout(yaxis={"range":[0,1.05],"tickformat":".0%","title":"Recorded stage coverage"},height=440)
        st.plotly_chart(fig,use_container_width=True)
        select_product(st,d,"workflow")
        st.caption("Recorded features do not establish integrated end-to-end operation. Intervals are retained here for drill-down.")
    else:st.info("No workflow mapping available.")

def advantage(st,data,cfg,rows):
    st.header("Competitive Advantage")
    if rows.empty:return
    f=priority_families(rows)
    candidates=f[f.Order<4]
    default=(candidates if not candidates.empty else f).head(4)["Product ID"].tolist()
    names=rows.set_index("Product ID").Product.to_dict()
    ids=st.multiselect("Competitors to benchmark",list(names),default=default,format_func=names.get,key="founder-adv-products")
    selected=rows[rows["Product ID"].isin(ids)]
    if selected.empty:st.info("Select competitors.");return
    st.subheader("Strategic capability heatmap")
    heatmap(st,data,cfg,selected,"advantage",list(registry(data,CRITERIA,"Criterion ID")) if st.checkbox("Show all criteria",key="adv-all") else None)
    st.subheader("Differentiation portfolio")
    d=advantage_summary(data,cfg,ids)
    if d.empty:st.info("No comparable evidence.");return
    table(st,d[["Criterion","Finding","Customer importance","Customer demand","Decision"]],"advantage-findings",True)
    mapped=d[d["Customer importance"]!="Unknown"].copy()
    if mapped.empty:st.info("Customer importance is not recorded. The portfolio cannot yet establish commercial value. Functional findings remain available above.")
    else:
        mapped["Importance"]=mapped["Customer importance"].map({"Low":1,"Medium":2,"High":3});mapped["Width"]=mapped["Rarity upper"]-mapped["Rarity lower"];mapped["Zero"]=0.
        fig=px.scatter(mapped,x="Rarity lower",y="Importance",color="Finding",hover_name="Criterion",error_x="Width",error_x_minus="Zero")
        fig.update_layout(xaxis={"range":[0,1.05],"tickformat":".0%","title":"Evidence-bounded differentiation rarity"},yaxis={"range":[.5,3.5],"tickvals":[1,2,3],"ticktext":["Low","Medium","High"]})
        st.plotly_chart(fig,use_container_width=True)
    st.caption("Substantiated functional advantage requires technical-or-stronger competitor evidence across the selected cohort. Customer value and operational performance are distinct. No implementation evidence required for AIT-VISTA.")
    select_product(st,selected,"adv-portfolio")

def monitor(st,data,cfg,rows,snapshots,current,demo):
    st.header("Intelligence Monitor")
    st.subheader("Latest recorded developments")
    t=timeline(data)
    names=registry(data,"Companies","Company ID");pro=registry(data,"Products","Product ID")
    t["Company"]=t["Company ID"].map(lambda c:value(names.get(c,{}),"Company Name"))
    t["Product"]=t["Product ID"].map(lambda p:value(pro.get(p,{}),"Product Name"))
    types=st.multiselect("Development types",list(t["Date basis"].unique()),default=list(t["Date basis"].unique()),key="monitor-types")
    filtered=t[t["Date basis"].isin(types)]
    plot=filtered.copy()
    plot["Parsed date"]=pd.to_datetime(plot.Date,format="mixed",errors="coerce",utc=True)
    plot=plot[plot["Parsed date"].notna()].head(100)
    if not plot.empty:
        fig=px.scatter(plot,x="Parsed date",y="Company",color="Date basis",hover_name="Product",custom_data=["Product ID","Company ID"],hover_data=["Date","Development"])
        fig.update_layout(height=max(330,24*plot.Company.nunique()+120),xaxis_title="Recorded or reported date",yaxis_title="")
        ev=st.plotly_chart(fig,use_container_width=True,key="monitor-timeline-plot",on_select="rerun",selection_mode="points")
        pts=ev.selection.points if ev is not None and hasattr(ev,"selection") else []
        click=pts[0].get("customdata",[]) if pts else []
        if len(click)>1 and click[1] in names:open_profile(st,click[0] or None,click[1],"timeline-click")
    table(st,filtered[["Date","Date basis","Company","Product","Development","Strategic implication","Source"]].head(50),"timeline",True)
    if not rows.empty:select_product(st,rows,"timeline")
    st.caption("Dates are labelled by type. Assessment changes indicate recorded knowledge, not necessarily changes in the product.")
    if not demo and len(snapshots)>1:
        options=[s for s in snapshots if s[0]!=current]
        if options:
            old=st.selectbox("Compare against saved snapshot",[s[0] for s in options],format_func=lambda h:next(s[1] for s in options if s[0]==h),key="monitor-snapshot")
            with connect() as conn:before=read_snapshot(conn,old)
            if before:
                ch=comparison_changes(before,data)
                if ch.empty:st.info("No recorded direct assessment changes.")
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

def landing(st,data,cfg,rows,snapshots,current,demo):
    st.header("Command Centre")
    st.caption("What matters now — competitive relevance, differentiation and decisions.")
    if rows.empty:st.info("No product records yet.");return
    f=priority_families(rows)
    for order,title in [(0,"Core visual competition"),(1,"Workflow and customer-budget substitutes"),(2,"Adjacent market candidates"),(3,"Classification needs review")]:
        group=f[f.Order==order]
        if group.empty:continue
        st.subheader(title)
        for _,r in group.head(4 if order<2 else 2).iterrows():
            with st.container(border=True):
                a,b=st.columns([4,1])
                with a:
                    st.markdown("**"+r.Company+" · "+r.Product+"**")
                    st.write(r["Why care"])
                    st.caption("Unresolved: "+r.Unresolved)
                with b:open_profile(st,r["Product ID"],r["Company ID"],"landing-"+r["Product ID"])
        if len(group)>(4 if order<2 else 2):st.caption("More products are available in Competitor Explorer.")
    st.caption("Review order is role-based, then recorded overlap and evidence, not a probability of lost sales. All roles remain accessible. Source classifications are provisional.")
    st.button("Open full company directory",on_click=navigate,args=(st,None,None,"Competitor Explorer"),key="landing-directory")
    st.subheader("Where we may differentiate")
    families=f[f.Order<3]["Family ID"].tolist()
    candidates=rows[rows["Family ID"].isin(families)]["Product ID"].tolist()
    if candidates and registry(data,CRITERIA,"Criterion ID"):
        d=advantage_summary(data,cfg,candidates)
        if not d.empty:
            strong=d[d.Finding=="Substantiated functional advantage"]
            if strong.empty:st.info("No cohort-wide substantiated functional advantage under the technical-evidence scenario. This does not imply absence of differentiation.")
            else:table(st,strong[["Criterion","Finding","Decision"]],"verified-advantage")
            potential=d[d.Finding.str.contains("Potential|Insufficient",regex=True)]
            table(st,potential[["Criterion","Finding","Decision"]].head(6),"potential-advantage")
    st.button("Explore competitive advantage",on_click=navigate,args=(st,None,None,"Competitive Advantage"),key="landing-adv")
    st.subheader("Recently recorded intelligence")
    t=timeline(data)
    if not t.empty:
        latest=t[t["Date basis"]=="Observation recorded"].head(4)
        names=registry(data,"Companies","Company ID")
        for i,(_,r) in enumerate(latest.iterrows()):
            st.markdown("**"+value(names.get(r["Company ID"],{}),"Company Name")+" · "+r.Date+"**")
            st.write(r.Development)
            if r["Company ID"] in names:open_profile(st,None,r["Company ID"],"news-"+str(i))
    st.button("Review developments and research priorities",on_click=navigate,args=(st,None,None,"Intelligence Monitor"),key="landing-monitor")

def founder_page(st,page,data,cfg,snapshots,current,demo):
    rows=summaries(data)
    if ASSESS not in data:st.info("Direct comparison register absent in this snapshot. Company records remain available; sync a newer snapshot for benchmarking.")
    if page=="Command Centre":landing(st,data,cfg,rows,snapshots,current,demo)
    elif page=="Competitor Explorer":explorer(st,data,cfg,rows)
    elif page=="Market Positioning":positioning(st,data,cfg,rows)
    elif page=="Competitive Advantage":advantage(st,data,cfg,rows)
    else:monitor(st,data,cfg,rows,snapshots,current,demo)
