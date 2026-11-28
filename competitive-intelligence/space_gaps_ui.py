"""Space discovery tab; derived from local snapshot only."""
import pandas as pd
from space_knowledge_gaps import space_knowledge_gaps
from core import digest
from portfolio_ui import source_links
from excel_archive import download_analysis

def space_gaps_view(st,data,snapshots,current,demo,navigate,table):
    st.subheader("Space — Knowledge Gaps")
    st.caption("Find space-linked companies that are insufficiently understood, including zero recorded overlap. This is a research backlog, not a threat ranking.")
    minimum=st.slider("Minimum distinct core gaps for mapped products",1,8,3,key="space-gaps-min")
    frame,details=space_knowledge_gaps(data,minimum)
    st.session_state["space-gap-company-ids"]=frame["Company ID"].tolist()
    a,b,c=st.columns(3)
    a.metric("Companies requiring research",len(frame))
    b.metric("No mapped space product",int((frame["Space product count"]==0).sum()))
    c.metric("Zero recorded overlap",int((frame["Best recorded overlap"]==0).sum()))
    st.caption("No mapped space product always qualifies; otherwise at least the selected number of distinct unresolved or weakly evidenced core criteria. Company heritage is never inherited by a product. Missing knowledge does not mean missing capability.")
    scope=st.radio("Research scope",["All","Product discovery","Technical research"],horizontal=True,key="space-gaps-scope")
    query=st.text_input("Search space companies",key="space-gaps-search").strip().casefold()
    shown=frame.copy()
    if scope=="Product discovery":shown=shown[shown["Space product count"]==0]
    elif scope=="Technical research":shown=shown[shown["Space product count"]>0]
    if query:shown=shown[shown.Company.str.casefold().str.contains(query,regex=False)|shown["Company ID"].str.casefold().str.contains(query,regex=False)]
    st.caption(f"{len(shown)} of {len(frame)} companies shown. Evidence counts refer only to mapped space products; N/A means not yet mapped.")
    if shown.empty:
        st.info("No companies meet these research filters.");return
    cols=["Research priority","Company","Space basis","Product count","Space product count","Best recorded overlap","Gap criteria","Unassessed pairs","Unresolved pairs","Weak evidence pairs","Technical determinate coverage","Reason","Next Action"]
    display=shown[cols].copy()
    for col in ["Best recorded overlap","Technical determinate coverage"]:
        display[col]=display[col].map(lambda x:"N/A" if pd.isna(x) else f"{x:.2%}")
    display["Gap criteria"]=display["Gap criteria"].map(lambda x:"N/A" if pd.isna(x) else str(int(x)))
    table(st,display,"space-gap-summary")
    stamp=next((s[1] for s in snapshots if s[0]==current),"")
    export=shown.assign(**{"Snapshot ID":("synthetic-"+digest(data)) if demo else current or digest(data),"Snapshot date":"" if demo else stamp,"Dataset mode":"SYNTHETIC DEMO" if demo else "LOCAL SNAPSHOT","Minimum gap criteria":minimum})
    download_analysis(st,export,"space-knowledge-gaps","5PACE_space_knowledge_gaps")
    st.download_button("Export space research CSV",export.to_csv(index=False).encode("utf-8-sig"),file_name="5PACE_space_knowledge_gaps.csv",key="space-gaps-csv")
    names=shown.set_index("Company ID").Company.to_dict()
    cid=st.selectbox("Inspect space company",list(names),format_func=lambda x:names[x]+" | "+x,key="space-gaps-company")
    r=shown[shown["Company ID"]==cid].iloc[0]
    st.markdown("**"+r.Company+" — "+r["Research priority"]+"**")
    st.write(r.Reason);st.write(r["Next Action"])
    st.caption("Space evidence: "+(r["Space evidence IDs"] or "No linked record ID"))
    source_links(st,r["Space sources"])
    st.button("Open space company profile",key="space-gap-profile",on_click=navigate,args=(st,r["Best Product ID"] or None,cid))
    d=details[cid];d=d[d["Gap reason"]!=""].reset_index(drop=True)
    if d.empty:st.info("First establish product-specific space relevance; no criterion gaps are fabricated.")
    else:
        table(st,d,"space-gap-details",True)
        names={i:x.Product+" | "+x["Criterion ID"]+" | "+x.Verdict for i,x in d.iterrows()}
        i=st.selectbox("Inspect space research question",list(names),format_func=names.get,key="space-gap-question-"+cid)
        x=d.iloc[i]
        st.write("Verify "+x.Criterion+" for "+x.Product+".")
        source_links(st,x["Source URLs"])
        ref=x["Comparison IDs"].split("; ")[0] if x["Comparison IDs"] else None
        st.button("Open space criterion evidence",key="space-gap-evidence-"+cid,on_click=navigate,args=(st,x["Product ID"],cid,"Competitor Explorer",x["Criterion ID"],"Comparison Assessment" if ref else None,ref))
