"""Local watchlist workspace: independent filters, evidence drill-down and exports."""
import pandas as pd
from company_watchlist import watchlist, watchlist_changes
from core import connect,read_snapshot,digest
from excel_archive import download_analysis
from portfolio_ui import source_links
from space_gaps_ui import space_gaps_view

PERCENT=["Best Product Overlap","Portfolio Overlap","Commercial-only overlap","Evidence Completeness","Determinate completeness"]
def reset(st):
    st.session_state["watch-threshold"]=20
    st.session_state["watch-min-gaps"]=3
    st.session_state["watch-scope"]="All"
    st.session_state["watch-priorities"]=["P0","P1","P2","P3"]
    st.session_state["watch-search"]=""

def watchlist_view(st,data,cfg,snapshots,current,demo,navigate,table):
    st.header("Company Watchlist")
    general,space=st.tabs(["All watchlist companies","Space — Knowledge Gaps"])
    with general:
        general_watchlist_view(st,data,cfg,snapshots,current,demo,navigate,table)
    with space:
        space_gaps_view(st,data,snapshots,current,demo,navigate,table)

def general_watchlist_view(st,data,cfg,snapshots,current,demo,navigate,table):
    st.caption("Research priority, not threat probability. Full snapshot, independent of strategic core (40/60). Company-level space activity does not establish product-level adoption.")
    a,b=st.columns(2)
    threshold=a.slider("Technology overlap threshold (%)",0,100,20,5,key="watch-threshold")/100
    min_gaps=b.slider("Minimum distinct core criteria requiring review",1,8,3,key="watch-min-gaps")
    st.button("Reset watchlist filters",key="watch-reset",on_click=reset,args=(st,))
    frame,details=watchlist(data,threshold,min_gaps)
    st.session_state["watchlist-company-ids"]=frame["Company ID"].tolist()
    a,b,c=st.columns(3)
    a.metric("Companies to watch",len(frame))
    b.metric("Confirmed space activity",int(frame["Space Confirmed"].astype(bool).sum()))
    c.metric("High research priority (P0/P1)",int(frame.Priority.isin(["P0","P1"]).sum()))
    st.caption("Qualification: space target OR documented company/product space activity OR reported/research space signal OR (recorded technology overlap strictly above threshold AND sufficient distinct evidence gaps). Reported implementation is not independently verified.")
    st.caption("Weak positive claims, unknown/unassessed/announced/disputed states and explicitly unresolved partial scope count as gaps. The technology trigger uses positively overlapping products only. Pair counts can exceed eight; distinct criteria cannot.")
    scope=st.radio("Watch scope",["All","Space","Technology"],horizontal=True,key="watch-scope")
    priorities=st.multiselect("Priority",["P0","P1","P2","P3"],default=["P0","P1","P2","P3"],key="watch-priorities")
    query=st.text_input("Search company",key="watch-search").strip().casefold()
    shown=frame[frame.Priority.isin(priorities)].copy()
    if scope=="Space":
        shown=shown[shown[["Space Target","Space Confirmed","Reported space implementation","Space research / other signal"]].astype(bool).any(axis=1)]
    elif scope=="Technology":shown=shown[shown["Watch Reason"].str.contains("Technology exposure",regex=False)]
    if query:shown=shown[shown.Company.str.casefold().str.contains(query,regex=False)|shown["Company ID"].str.casefold().str.contains(query,regex=False)]
    st.caption(f"{len(shown)} of {len(frame)} qualifying companies shown. Exports below use this selection.")
    if not shown.empty:
        cols=["Priority","Company","Watch Reason","Best Product","Best Product Overlap","Portfolio Overlap","Gap criteria","Unverified Claims","Unknown","Unassessed","Announced","Disputed","Evidence Completeness","Last Reviewed","Next Action"]
        display=shown[cols].copy()
        for col in set(PERCENT)&set(display.columns):display[col]=display[col].map(lambda x:f"{x:.2%}")
        table(st,display,"watchlist-summary")
        stamp=next((s[1] for s in snapshots if s[0]==current),"")
        source=next((s[2] for s in snapshots if s[0]==current),"")
        mode="SYNTHETIC DEMO" if demo else "LOCAL SNAPSHOT"
        export=shown.assign(**{"Snapshot ID":("synthetic-"+digest(data)) if demo else current or digest(data),"Snapshot date":"" if demo else stamp,"Technology threshold":threshold,"Minimum gap criteria":min_gaps,"Dataset mode":mode})
        download_analysis(st,export,"watchlist","5PACE_company_watchlist")
        st.download_button("Export watchlist CSV",export.to_csv(index=False).encode("utf-8-sig"),file_name="5PACE_company_watchlist.csv",key="watchlist-csv")
        signature=(digest(data),tuple(shown["Company ID"]),threshold,min_gaps,mode,stamp,source)
        if st.button("Generate watchlist PDF",key="watchlist-pdf-generate"):
            from pdf_reports import render_report
            st.session_state["watchlist-pdf"]=(signature,render_report(data,cfg,"Intelligence monitor",mode=mode,captured=stamp,snapshot_hash=current,source=source,watchlist_selection=shown["Company ID"].tolist(),watchlist_threshold=threshold,watchlist_min_gaps=min_gaps))
        saved=st.session_state.get("watchlist-pdf")
        if saved and saved[0]==signature:
            st.download_button("Download watchlist PDF",saved[1],file_name="5PACE_company_watchlist.pdf",mime="application/pdf",key="watchlist-pdf-download")
        names=shown.set_index("Company ID").Company.to_dict()
        cid=st.selectbox("Inspect company",list(names),format_func=lambda x:names[x]+" | "+x,key="watch-company")
        r=shown[shown["Company ID"]==cid].iloc[0]
        st.markdown("**"+r.Company+" — "+r.Priority+"**")
        for col in ["Space Target","Space Confirmed","Reported space implementation","Space research / other signal","Research basis","Next Action"]:
            st.write(col+": "+(str(r[col]) or "Not recorded"))
        st.caption("Space evidence: "+(r["Space evidence IDs"] or "No linked record ID"))
        source_links(st,r["Space sources"])
        st.button("Open company profile",key="watch-open-company",on_click=navigate,args=(st,r["Best Product ID"] or None,cid))
        gaps=details[cid];gaps=gaps[gaps["Gap reason"]!=""].reset_index(drop=True)
        st.subheader("Evidence gaps by product and criterion")
        if gaps.empty:st.info("No qualifying criterion gaps in the selected research basis.")
        else:
            table(st,gaps[["Product","Criterion","Verdict","Evidence level","Gap reason","Comparison IDs","Assessment date"]],"watch-gaps",True)
            labels={i:g["Product"]+" | "+g["Criterion ID"]+" | "+g["Verdict"] for i,g in gaps.iterrows()}
            i=st.selectbox("Inspect research question",list(labels),format_func=labels.get,key="watch-gap-"+cid)
            g=gaps.iloc[i]
            st.write("Verify "+g.Criterion+" for "+g.Product+".")
            st.write(g.Rationale or "No active comparison rationale.")
            st.caption(g.Limitations or "No recorded limitations.")
            source_links(st,g["Source URLs"])
            ref=g["Comparison IDs"].split("; ")[0] if g["Comparison IDs"] else None
            st.button("Open criterion evidence",key="watch-gap-open-"+cid,on_click=navigate,args=(st,g["Product ID"],cid,"Competitor Explorer",g["Criterion ID"],"Comparison Assessment" if ref else None,ref))
    else:st.info("No companies meet the selected watchlist filters.")
    st.subheader("Watchlist changes")
    hashes=[s[0] for s in snapshots]
    if not demo and current in hashes and hashes.index(current)+1<len(hashes):
        older=snapshots[hashes.index(current)+1:]
        stamps={s[0]:s[1] for s in older}
        old=st.selectbox("Compare against earlier snapshot",list(stamps),format_func=lambda h:stamps[h]+" | "+h[:12],key="watch-before")
        with connect() as conn:before=read_snapshot(conn,old)
        if before:
            previous,_=watchlist(before,threshold,min_gaps)
            changes=watchlist_changes(previous,frame)
            st.caption("Complete watchlist before and after, using the same thresholds. Recorded knowledge changes, not confirmed product releases.")
            if changes.empty:st.info("No recorded watchlist changes.")
            else:table(st,changes,"watchlist-changes",True)
    else:st.info("An earlier local snapshot is required for change comparison.")
