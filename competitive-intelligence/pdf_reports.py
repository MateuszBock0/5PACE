"""Offline PDF reports for the current immutable dataset; no credential or network access."""
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
import os, re
from xml.sax.saxutils import escape,quoteattr
import pandas as pd
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,Rect,Circle,String,Line
from core import value,digest,validate
from command_engine import registry,direct_matrix,direct_current,matrix_audit,research_queue,profile
from product_intelligence import CRITERIA
from founder import DEFAULT_MAP_SCOPE,summaries,strategic_map_cohort,brief_criteria,profile_records,advantage_summary,profile_findings,WORKFLOW_EXAMPLES
from decision import signals,CUSTOMER_LANES,FUNCTION_LANES,importance_lane
from threat_watch import exposure,report_provenance,selected_criteria,spread_points,exposure_records,priority_records

REPORTS=["Strategic overview","Competitor profile","Market positioning & workflow","Competitive advantage","Intelligence monitor","QA & data integrity","Combined strategic report"]
MIME="application/pdf"
NAVY=colors.HexColor("#172B3A");TEAL=colors.HexColor("#087E7B");PALE=colors.HexColor("#EAF0F3")
STATUS_COLORS={"Supported":"#D9EEEA","Partially supported":"#F8E8CD","Explicitly unsupported":"#F3D5D5","Unknown":"#C8D6E3","Unassessed":"#E9EEF2","Disputed":"#E5D6EF","Announced":"#DBE5F9","Not applicable":"#D9DCE1"}
FONT="Helvetica";BOLD="Helvetica-Bold"
def fonts():
    global FONT,BOLD
    if FONT!="Helvetica":return
    win=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
    for a,b in [(win/"arial.ttf",win/"arialbd.ttf"),(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),(Path(reportlab.__file__).parent/"fonts/Vera.ttf",Path(reportlab.__file__).parent/"fonts/VeraBd.ttf")]:
        if a.is_file() and b.is_file():
            pdfmetrics.registerFont(TTFont("CIEReport",str(a)));pdfmetrics.registerFont(TTFont("CIEReportBold",str(b)))
            FONT="CIEReport";BOLD="CIEReportBold";return

def text(v):
    if v is None:return ""
    try:
        if pd.isna(v):return ""
    except (ValueError,TypeError):pass
    return str(v)

def render_report(data,cfg,kind,product_ids=None,mode="LOCAL SNAPSHOT",captured="",snapshot_hash="",source="",criterion_ids=None,map_scope=None):
    if kind not in REPORTS:raise ValueError("Unknown report type")
    captured,snapshot_hash,source=report_provenance(data,mode,captured,snapshot_hash,source)
    fonts()
    companies=registry(data,"Companies","Company ID");products=registry(data,"Products","Product ID")
    criteria=registry(data,CRITERIA,"Criterion ID");ledger=direct_current(data)
    rows=summaries(data)
    if product_ids is None:
        chosen=strategic_map_cohort(rows)["Product ID"].tolist() if not rows.empty else []
    else:chosen=list(dict.fromkeys(p for p in product_ids if p in products))
    d=rows[rows["Product ID"].isin(chosen)] if not rows.empty else rows
    ids=d["Product ID"].tolist() if not d.empty else []
    cids=selected_criteria(data) if criterion_ids is None else [c for c in criterion_ids if c in criteria]
    map_scope=map_scope or (DEFAULT_MAP_SCOPE if product_ids is None else "Explicit product selection")
    buf=BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=39,leftMargin=39,topMargin=48,bottomMargin=43,title="5PACE | "+kind,author="5PACE")
    width=A4[0]-78
    styles={
        "title":ParagraphStyle("title",fontName=BOLD,fontSize=24,leading=29,textColor=NAVY,spaceAfter=13),
        "h":ParagraphStyle("h",fontName=BOLD,fontSize=15,leading=19,textColor=TEAL,spaceBefore=14,spaceAfter=7,keepWithNext=True),
        "sub":ParagraphStyle("sub",fontName=BOLD,fontSize=11,leading=14,textColor=NAVY,spaceBefore=8,spaceAfter=4,keepWithNext=True),
        "body":ParagraphStyle("body",fontName=FONT,fontSize=9,leading=13,textColor=NAVY,spaceAfter=6,splitLongWords=True),
        "small":ParagraphStyle("small",fontName=FONT,fontSize=7.5,leading=10,textColor=NAVY,spaceAfter=3,splitLongWords=True),
        "head":ParagraphStyle("head",fontName=BOLD,fontSize=8,leading=10,textColor=colors.white,splitLongWords=True),
    }
    story=[]
    def p(v,style="body"):
        raw=text(v);parts=[];last=0
        for m in re.finditer(r'https?://[^\s<>]+',raw):
            parts.append(escape(raw[last:m.start()]))
            url=m.group(0).rstrip(".,;)")
            parts.append("<link href="+quoteattr(url)+" color=\"#087E7B\">"+escape(url)+"</link>"+escape(m.group(0)[len(url):]))
            last=m.end()
        parts.append(escape(raw[last:]))
        return Paragraph("".join(parts).replace("\n","<br/>"),styles[style])
    def add(v,style="body"):story.append(p(v,style))
    def heading(v):add(v,"h")
    def table(headers,values,ratios=None,status_cols=()):
        vals=list(values)
        if not vals:add("No records in selected scope.","small");return
        cols=len(headers); widths=[width*x/sum(ratios) for x in ratios] if ratios else [width/cols]*cols
        # splitInRow allows unusually long source descriptions to flow over pages.
        t=Table([[p(x,"head") for x in headers]]+[[p(x,"small") for x in r] for r in vals],colWidths=widths,repeatRows=1,splitByRow=1,splitInRow=1,hAlign="LEFT")
        ts=[("BACKGROUND",(0,0),(-1,0),NAVY),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LINEBELOW",(0,0),(-1,0),.6,TEAL),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE])]
        for i,r in enumerate(vals,1):
            for j in status_cols:
                if text(r[j]) in STATUS_COLORS:ts.append(("BACKGROUND",(j,i),(j,i),colors.HexColor(STATUS_COLORS[text(r[j])])))
        t.setStyle(TableStyle(ts));story.extend([t,Spacer(1,8)])
    def overview():
        heading("Strategic watchlist")
        add("Recorded roles are provisional; actual procurement overlap is unresolved. Research entrants are included independently of commercial ranking.")
        table(["Company / product","Competitive role and decision","Evidence / uncertainty"],[(r.Company+"\n"+r.Product,r.Role+"\n"+r.Decision,r["Why care"]+"\n"+r.Unresolved) for _,r in d.iterrows()],[1.2,1.6,2.5])
    def threat():
        heading("Threat Watch and response priorities")
        add("Threat Watch scope: "+str(len(ids))+" products; "+str(len(cids))+" criteria. Provisional review order; changes between snapshots are not included in this static report.")
        e=exposure(data,cfg,ids,cids)
        if not e.empty:
            xs=["No positive record / unresolved","Partial recorded","Full recorded"];ys=["Unresolved","Low","Medium","High"]
            dr=Drawing(width,164);left=75;bottom=27;cw=(width-left-6)/3;ch=30
            for i,lab in enumerate(ys):
                dr.add(String(0,bottom+i*ch+12,lab,fontName=FONT,fontSize=8,fillColor=NAVY))
                for j in range(3):dr.add(Rect(left+j*cw,bottom+i*ch,cw,ch,strokeColor=colors.white,fillColor=PALE))
            for j,lab in enumerate(["Unresolved overlap","Partial support","Full support"]):
                dr.add(String(left+(j+.5)*cw,10,lab,fontName=FONT,fontSize=8,textAnchor="middle",fillColor=NAVY))
            for (x,y),g in e.groupby(["Overlap","Importance"]):
                if x not in xs or y not in ys:continue
                dr.add(String(left+(xs.index(x)+.5)*cw,bottom+ys.index(y)*ch+12,str(len(g))+" criteria",fontName=BOLD,fontSize=8,textAnchor="middle",fillColor=TEAL))
            story.append(dr)
            add("Response map: customer importance by recorded overlap. Counts group criteria in the same category; exact action and evidence are listed below.","small")
            table(["Criterion / action","Product / verdict","Evidence and next decision"],[(r["Short criterion"]+"\n"+r.Action,r.Product+"\n"+r.Verdict,r.Evidence+" | "+r["Assessment date"]+" | "+r["Comparison ID"]+"\n"+r["Next decision"]+"\n"+r.Source) for _,r in e.iterrows()],[1,1,2.5])
            records=priority_records(exposure_records(data,cfg,ids,cids))
            if not records.empty:
                add("All active comparison records (including alternate and conflicting verdicts); absent records remain unresolved.","sub")
                table(["Product / criterion","Pair / record verdict","Evidence, ID, date / decision"],[(r.Product+"\n"+r["Short criterion"],r.Verdict+" / "+r["Record verdict"],r.Evidence+" | "+r["Comparison ID"]+" | "+r["Assessment date"]+"\n"+r.Action+"\n"+r.Limitations+"\n"+r.Source) for _,r in records.iterrows() if r["Comparison ID"]],[1.2,1,2.5])
            add("Importance without provenance is unresolved. Recorded support is not performance or commercial substitution.")
    def market():
        heading("Technology × customer positioning")
        add("Categorical map: recorded functional overlap versus customer-segment evidence. Marker locations within a cell only separate labels. AIT-VISTA is the declared reference, not proven adoption.")
        if not d.empty:
            dr=Drawing(width,245);left=132;bottom=36;cw=(width-left-12)/4;ch=44
            for i,lab in enumerate(["Unresolved","Adjacent sector","Space AIT target","Space AIT case"]):
                dr.add(String(0,bottom+i*ch+19,lab,fontName=FONT,fontSize=7,fillColor=NAVY))
                for j in range(4):dr.add(Rect(left+j*cw,bottom+i*ch,cw,ch,strokeColor=colors.white,fillColor=PALE))
            for j,lab in enumerate(["Unresolved","Some","Material","Broad"]):dr.add(String(left+j*cw+cw/2,18,lab,fontName=FONT,fontSize=7,textAnchor="middle",fillColor=NAVY))
            rx=left+3.5*cw;ry=bottom+2.5*ch
            dr.add(Circle(rx,ry,17,fillColor=colors.HexColor("#D9EEEA"),strokeColor=TEAL,strokeWidth=1.2))
            dr.add(String(rx,ry+19,"AIT-VISTA",fontName=BOLD,fontSize=7,textAnchor="middle",fillColor=TEAL))
            for (x,y),g in d.groupby(["Functional overlap","Customer position"]):
                if x not in FUNCTION_LANES or y not in CUSTOMER_LANES:continue
                j=FUNCTION_LANES.index(x);i=CUSTOMER_LANES.index(y)
                # For dense maps label groups, and supply exact membership below.
                label=str(len(g))+" products" if len(g)>1 else str(ids.index(g.iloc[0]["Product ID"])+1)
                xx=left+j*cw+cw/2;yy=bottom+i*ch+ch/2
                if j==3 and i==2:xx+=cw*.23;yy-=ch*.15
                dr.add(Circle(xx,yy,6,fillColor=colors.HexColor("#466D8A"),strokeColor=colors.white,strokeWidth=.8))
                if len(g)>1:
                    dr.add(String(xx,yy-2,str(len(g))+"×",fontName=BOLD,fontSize=6,textAnchor="middle",fillColor=colors.white))
                else:dr.add(String(xx,yy-2,label,fontName=BOLD,fontSize=8,textAnchor="middle",fillColor=colors.white))
            story.append(dr)
            add("AIT-VISTA is the outlined reference beneath rival marks. Numbered markers identify single products; dense cells show group size. Exact product categories follow. Marker size is visual emphasis.","small")
        table(["# / product","Functional overlap","Customer position / evidence"],[(str(i+1)+". "+r.Company+" / "+r.Product,r["Functional overlap"],r["Customer position"]+"\n"+r["Customer basis"]) for i,(_,r) in enumerate(d.iterrows())],[1.1,1,2.2])
        heading("Map scope and exclusions")
        add(map_scope+" — "+str(len(ids))+" of "+str(len(rows))+" products. Default union uses original categories; no family or role restriction.")
        from founder import map_exclusions
        excluded=map_exclusions(rows,d,map_scope)
        if not excluded.empty:table(["Product","Reason not shown"],[(r.Product,r["Reason not shown"]) for _,r in excluded.iterrows()],[1,2])
        else:add("All products included.")
        heading("AIT workflow criterion examples")
        stage={c:l for l,c in WORKFLOW_EXAMPLES if c in criteria}
        matrix_table(list(stage),stage)
        add("Individual criteria are examples, not evidence of full workflow integration.")
    def matrix_table(cids,stage=None):
        m=direct_matrix(data,ids,cids)
        for start in range(0,len(ids),4):
            chunk=ids[start:start+4]
            table(["Criterion","AIT-VISTA"]+[value(products[q],"Product Name") for q in chunk],
                [[((stage or {}).get(c,"")+" / " if stage and c in stage else "")+value(criteria[c],"Product criterion"),profile(cfg,c,"As-Is")]+[m.loc[q,c] for q in chunk] for c in cids],
                [2.2,1]+[1]*len(chunk),tuple(range(1,len(chunk)+2)))
    def advantage():
        heading("Competitive advantage")
        if not ids or not criteria:add("No direct comparison scope.");return
        matrix_table(cids)
        threat()
        a=advantage_summary(data,cfg,ids)
        if not a.empty:
            table(["Criterion","Finding","Customer importance","Decision"],[(r.Criterion,r.Finding,importance_lane(cfg,r["Criterion ID"]),r.Decision) for _,r in a.iterrows()],[1.5,1.5,1,1])
        add("Technical-documentation-or-stronger scenario for differentiation. Vendor claims are visible in the comparison matrix, but do not independently establish an advantage. Unknown is not unsupported.")
    def profile_report():
        heading("Company and product profiles")
        for q in ids:
            r=d[d["Product ID"]==q].iloc[0];pr=products[q];co=companies.get(r["Company ID"],{})
            add(r.Company+" / "+r.Product,"sub")
            add(value(pr,"Product Description") or value(pr,"Primary Use Case") or "Description not recorded.")
            table(["Field","Recorded information"],[(k,value(pr,k) or "Not recorded") for k in ["Primary Use Case","Target Customers","Target Industries","Deployment Architecture","Commercial Status","Space Industry Applicability","Product URL","Documentation URL"]],[1,3])
            add("Competitive relevance: "+r["Why care"]);add("Decision: "+r.Decision);add(r.Procurement)
            rec=profile_records(data,q)
            for name,fields in [("Deployments",["Customer Organisation","Deployment Status","Use Case","Deployment Date","Evidence Limitations","Source URL"]),("Commercial Intelligence",["Business Model","Pricing Model","Subscription Cost","One-time Licence Cost","Deployment Cost","Integration Cost","Currency","Price Basis","Applicable Date","Evidence Limitations","Source URL"])]:
                add(name,"sub")
                table(["Record details"],[["\n".join(k+": "+value(x,k) for k in fields if value(x,k))] for x in rec[name]])
            add("Active head-to-head evidence","sub")
            values=[]
            for c in criteria:
                e=ledger.get((q,c),{})
                refs=e.get("rows",[])
                values.append([value(criteria[c],"Product criterion"),profile(cfg,c,"As-Is"),e.get("status","Unassessed"),
                    "\n".join(" | ".join(value(x,k) for k in ["Comparison ID","Evidence level","Assessment date","Assessment rationale","Limitations","Source URLs"] if value(x,k)) for x in refs) or "No direct assessment"])
            table(["Criterion","AIT-VISTA","Competitor","Evidence / date / source"],values,[1.5,.75,.85,2.6],(1,2))
    def monitor():
        heading("Intelligence monitor")
        sig=signals(data)
        if product_ids is not None:sig=sig[sig["Product ID"].isin(ids)|((sig["Product ID"]=="")&sig["Company ID"].isin(d["Company ID"] if not d.empty else []))]
        add("Most recent 30 recorded signals. Event dates, commercial applicable dates and research discovery dates are distinct.")
        table(["Date / type","Company / development","Decision, limitations and source"],[(r.Date+"\n"+r["Date basis"],value(companies.get(r["Company ID"],{}),"Company Name")+"\n"+r.Development,r["Strategic implication"]+"\n"+r.Limitations+"\n"+r.Reference+"\n"+r.Source) for _,r in sig.head(30).iterrows()],[1,2,2])
        if ids and criteria:
            q=research_queue(data,direct_matrix(data,ids),cfg,captured)
            add("Top 20 research questions in report cohort","sub")
            table(["Product / priority","Research question","Decision / evidence IDs"],[(value(products.get(r["Product ID"],{}),"Product Name")+"\n"+text(r.Priority),r["Research question"],r["Strategic decision affected"]+"\n"+r["Existing evidence IDs"]+"\n"+r["Reason for uncertainty"]) for _,r in q.head(20).iterrows()],[1,2,2])
    def qa():
        heading("Snapshot data quality")
        errors,warnings=validate(data);mismatches=matrix_audit(data)
        table(["Check","Result"],[["Source schema / relationships",str(len(errors))+" errors; "+str(len(warnings))+" warnings"],["Derived matrix cross-check",str(len(mismatches))+" findings"],["Snapshot SHA-256",digest(data)],["Scope","Entire selected snapshot; not software regression or visual acceptance"]],[1,3])
        for title,items in [("Validation errors",errors),("Validation warnings",warnings),("Matrix findings",mismatches)]:
            add(title,"sub")
            table(["Finding"],[[x] for x in items])
    add("5PACE / INTELLIGENCE","small");add(kind,"title")
    add("INTERNAL • "+mode,"sub")
    add("Captured UTC: "+(captured or "Not recorded")+" | Source: "+(source or "Not recorded"))
    add("Snapshot: "+(snapshot_hash or digest(data)),"small")
    add("Generated UTC: "+datetime.now(timezone.utc).isoformat(timespec="seconds"),"small")
    add("Report cohort: "+str(len(ids))+" products; Threat Watch criteria: "+str(len(cids))+". AIT-VISTA: As-Is, owner-declared functionality. All findings are conditional on recorded evidence and report scope.")
    def overview_with_threat():
        overview()
        threat()
    funcs={"Strategic overview":overview_with_threat,"Competitor profile":profile_report,"Market positioning & workflow":market,"Competitive advantage":advantage,"Intelligence monitor":monitor,"QA & data integrity":qa}
    if kind=="Combined strategic report":
        for i,fn in enumerate([overview_with_threat,market,advantage,monitor,qa]):
            if i:story.append(PageBreak())
            fn()
    else:funcs[kind]()
    add("Interpretation boundary: this report does not establish market share, verified shared procurement, calibrated threat probabilities, or operational performance. Keep reports local.","small")
    def footer(c,doc):
        c.setStrokeColor(TEAL);c.line(39,34,A4[0]-39,34);c.setFont(FONT,7)
        c.setFillColor(NAVY);c.drawString(39,23,"5PACE  |  "+mode+"  |  Internal");c.drawRightString(A4[0]-39,23,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
