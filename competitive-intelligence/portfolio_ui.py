"""Native company portfolio chart and exact evidence drill-down."""
import plotly.graph_objects as go
from chart_theme import render_chart,tokens
from company_portfolio import portfolio_data,filter_companies,selected_company,SCOPES,ALL_COMPANIES,CUSTOM,NOTE

def reset(st,key):
    st.session_state[key+"-scope"]=ALL_COMPANIES
    st.session_state.pop(key+"-custom",None)

def route(st,key,ids):
    cid=selected_company(st.session_state.get(key+"-chart",{}),ids)
    if cid:st.session_state[key+"-company"]=cid

def portfolio_figure(frame,details):
    t=tokens();ids=frame["Company ID"].tolist()
    labels=[r.Company+(" *" if r["Portfolio flag"]=="Portfolio-only exposure" else "") for _,r in frame.iterrows()]
    custom=[[r["Company ID"],r.Company,r["Portfolio coverage"],r["Best product ties"],r["Best single product coverage"],r["Product count"],r["Recorded coverage"],r["Determinate coverage"],r["Integration status"],r["Portfolio flag"],"<br>".join(q["Criterion ID"]+": "+q["Contributing products"] for _,q in details[r["Company ID"]]["criteria"].iterrows() if q.Credit>0) or "No positive core record"] for _,r in frame.iterrows()]
    hover=("%{customdata[1]}<br>Portfolio: %{customdata[2]:.2%}<br>Best: %{customdata[3]} (%{customdata[4]:.2%})<br>Products: %{customdata[5]}<br>Recorded / determinate: %{customdata[6]:.1%} / %{customdata[7]:.1%}<br>%{customdata[8]}<br>%{customdata[9]}<br>%{customdata[10]}<extra></extra>")
    fig=go.Figure()
    for label,col,color in [("Best single product","Best single product coverage","#087E7B"),("Additional portfolio coverage","Additional portfolio coverage","#45E0CC")]:
        fig.add_trace(go.Bar(y=ids,x=frame[col],orientation="h",name=label,customdata=custom,hovertemplate=hover,marker={"color":color,"line":{"color":t["outline"],"width":.55}}))
    zero=frame[frame["Portfolio coverage"]==0]
    if not zero.empty:
        ix={p:i for i,p in enumerate(ids)}
        fig.add_trace(go.Scatter(x=[0]*len(zero),y=zero["Company ID"],mode="markers",name="No positive record",customdata=[custom[ix[p]] for p in zero["Company ID"]],hovertemplate=hover,marker={"size":12,"symbol":"circle-open","color":t["outline"],"line":{"width":1.5}},showlegend=False))
    for _,r in frame.iterrows():
        fig.add_annotation(x=r["Portfolio coverage"]+.012,y=r["Company ID"],text=f'{r["Portfolio coverage"]:.2%}'+(" *" if r["Portfolio flag"]=="Portfolio-only exposure" else ""),xanchor="left",showarrow=False,font={"size":11,"color":t["text"]})
    fig.update_layout(barmode="stack",bargap=.36,height=max(320,29*len(frame)+105),margin={"l":10,"r":20,"t":25,"b":70},legend={"orientation":"h","y":1.04,"x":0},xaxis={"range":[-.035,1.17],"tickformat":".0%","title":"Recorded portfolio coverage — eight core criteria"},yaxis={"categoryorder":"array","categoryarray":ids,"autorange":"reversed","tickmode":"array","tickvals":ids,"ticktext":labels,"automargin":True,"tickfont":{"size":11}},clickmode="event+select")
    return fig

def portfolio_view(st,data,rows,navigate,table,key="portfolio"):
    st.subheader("Company Portfolio Coverage")
    st.caption("One row per registered company with products. Historical, research and announced products are identifiable in the detail. No inherited deployment or integration.")
    frame,details=portfolio_data(data,rows)
    if frame.empty:st.info("No companies with products.");return
    scope=st.selectbox("Portfolio company scope",SCOPES,key=key+"-scope")
    st.button("Reset portfolio scope",key=key+"-reset",on_click=reset,args=(st,key))
    names=frame.set_index("Company ID").Company.to_dict()
    ids=st.multiselect("Companies",list(names),format_func=lambda c:names[c]+" | "+c,key=key+"-custom") if scope==CUSTOM else None
    shown=filter_companies(frame,scope,ids)
    st.session_state["portfolio-company-ids"]=shown["Company ID"].tolist()
    st.caption(f"{len(shown)} of {len(frame)} companies · * Portfolio-only exposure: same 40/60 review rule applied to union, with space context only from recorded product customer evidence; no change to product qualification.")
    if shown.empty:st.info("No companies in selected scope.");return
    allowed=shown["Company ID"].tolist()
    if st.session_state.get(key+"-company") not in allowed:st.session_state[key+"-company"]=allowed[0]
    render_chart(st,portfolio_figure(shown,details),use_container_width=True,key=key+"-chart",on_select=lambda:route(st,key,allowed),selection_mode="points")
    st.caption(NOTE)
    st.caption("0% means no recorded positive core support, not confirmed technical absence. Criterion coverage counts any recorded / determinate pair for each criterion; pair coverage includes every product × criterion.")
    cid=st.selectbox("Inspect company portfolio (including 0%)",allowed,format_func=lambda c:names[c]+" | "+c,key=key+"-company")
    r=shown[shown["Company ID"]==cid].iloc[0];detail=details[cid]
    st.markdown("**"+r.Company+" — "+r["Portfolio flag"]+"**")
    a,b,c=st.columns(3)
    a.metric("Portfolio",f'{r["Portfolio coverage"]:.2%}')
    b.metric("Best single product",f'{r["Best single product coverage"]:.2%}')
    c.metric("Additional coverage",f'{r["Additional portfolio coverage"]*100:.2f} pp')
    st.caption("Best product(s): "+r["Best product ties"]+" · Commercial-only sensitivity: "+f'{r["Commercial-only coverage"]:.2%}'+" · Recorded / determinate criteria: "+f'{r["Recorded coverage"]:.2%} / {r["Determinate coverage"]:.2%}'+" · Recorded / determinate product pairs: "+f'{r["Pair recorded coverage"]:.2%} / {r["Pair determinate coverage"]:.2%}')
    st.caption("Space threshold basis (product IDs): "+r["Space threshold basis"])
    st.write("Integration status: "+r["Integration status"])
    st.caption("Documented or potential integration refers only to explicitly named product pairs, not the entire portfolio. No evidence is not incompatibility.")
    for i,e in enumerate(detail["integration"]):
        with st.expander(e["Status"]+" · "+" / ".join(e["Product IDs"])):
            st.write(e["Statement"]);st.caption(e["Register"]+" | "+e["Reference"]+" | "+e["Limitations"]);st.write(e["Source"])
    p=detail["products"].copy()
    for col in ["Recorded overlap","Evidence coverage","Determinate coverage"]:p[col]=p[col].map(lambda x:f"{x:.2%}")
    table(st,p,key+"-products-"+cid,True)
    st.button("Open company profile",key=key+"-profile",on_click=navigate,args=(st,p.iloc[0]["Product ID"],cid))
    st.markdown("**Eight criterion attribution**")
    table(st,detail["criteria"][["Criterion ID","Criterion","Portfolio verdict","Contributing products","Product states"]],key+"-criteria-"+cid,True)
    records=detail["records"]
    with st.expander("All active evidence, tied contributors and unresolved product states"):
        table(st,records,key+"-records-"+cid,True)
        labels={i:r["Criterion ID"]+" | "+r.Product+" | "+r["Pair verdict"]+" | "+(r["Comparison ID"] or "No record") for i,r in records.iterrows()}
        idx=st.selectbox("Inspect exact product / criterion record",list(labels),format_func=labels.get,key=key+"-record-"+cid)
        e=records.loc[idx]
        st.write(e.Rationale or "No active comparison rationale.")
        st.caption(e["Evidence level"]+" · "+e["Assessment date"]+" · "+e.Limitations)
        st.write(e["Source URLs"])
        st.button("Open exact criterion evidence",key=key+"-evidence-"+cid,on_click=navigate,args=(st,e["Product ID"],cid,"Competitor Explorer",e["Criterion ID"],"Comparison Assessment" if e["Comparison ID"] else None,e["Comparison ID"] or None))
    with st.expander("Company portfolio summary — all selected companies"):
        table(st,shown[["Company","Portfolio coverage","Best single product coverage","Additional portfolio coverage","Recorded coverage","Determinate coverage","Portfolio flag","Integration status"]],key+"-summary",True)
