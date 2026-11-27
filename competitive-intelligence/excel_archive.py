"""Local values-only XLSX export and atomic snapshot archiving.

SQLite remains authoritative. No Google API, credentials or source writes.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
import math
import os
import re
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from core import ROOT, TABLES, history, read_snapshot, state

ARCHIVE_ROOT=ROOT.parent/"Excel Archive"
LATEST="Competition_LATEST.xlsx"
MIME="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ORDER=list(TABLES)+["AIT-VISTA Capabilities","AIT-VISTA System Functions","Comparison Assessment","Competitive Comparison"]

def scalar(v):
    """Preserve strings and booleans; normalise analytical missing values."""
    if v is None: return None
    if isinstance(v,str): return v
    if isinstance(v,(datetime,date)): return v.isoformat()
    if hasattr(v,"item"):
        try: v=v.item()
        except (ValueError,TypeError): pass
    if isinstance(v,float) and not math.isfinite(v): return None
    if isinstance(v,(bool,int,float)): return v
    try:
        if pd.isna(v): return None
    except (ValueError,TypeError): pass
    return str(v)

def set_cell(ws,i,j,v):
    v=scalar(v)
    if v is None: return
    if isinstance(v,str):
        if len(v.encode("utf-16-le"))//2>32767 or ILLEGAL_CHARACTERS_RE.search(v):
            raise ValueError(f"{ws.title}!{get_column_letter(j)}{i}: text exceeds Excel cell limits or contains unsupported characters")
    c=ws.cell(i,j,v)
    # Preserve formulas, error-like values and URLs as literal captured text.
    # Never execute formula strings from external research evidence.
    if isinstance(v,str): c.data_type="s"

def workbook_bytes(data,identifier=None):
    if not data: raise ValueError("No worksheets to export")
    wb=Workbook()
    wb.remove(wb.active)
    if identifier: wb.properties.identifier=identifier
    wb.properties.title="5PACE Competitive Intelligence — values-only export"
    wb.properties.description="Local captured values; formulas, original formatting and Google Sheets metadata are not retained."
    names=[n for n in ORDER if n in data]+[n for n in data if n not in ORDER]
    used=set()
    for name in names:
        if not name or len(name)>31 or re.search(r"[\[\]:*?/\\]",name) or name.lower() in used:
            raise ValueError("Worksheet name is not representable in Excel: "+name)
        used.add(name.lower())
        ws=wb.create_sheet(name)
        tab=data[name]; headers=list(tab["headers"]); rows=tab["rows"]
        if len(headers)>16384 or len(rows)+1>1048576:
            raise ValueError(f"{name}: exceeds Excel worksheet limits")
        for j,h in enumerate(headers,1):
            set_cell(ws,1,j,h)
            cell=ws.cell(1,j)
            cell.font=Font(bold=True,color="FFFFFF")
            cell.fill=PatternFill("solid",fgColor="24405C")
            cell.alignment=Alignment(wrap_text=True,vertical="center")
        widths=[len(str(h)) for h in headers]
        for i,r in enumerate(rows,2):
            for j,h in enumerate(headers,1):
                v=r.get(h)
                set_cell(ws,i,j,v)
                if i<=202 and v is not None:
                    widths[j-1]=max(widths[j-1],min(46,len(str(v))))
        if headers:
            ws.freeze_panes="A2"
            ws.row_dimensions[1].height=32
            # The side-by-side tables and two-row comparison heading are not
            # one ordinary filter range; preserve their structure.
            if name not in {"AIT-VISTA System Functions","Competitive Comparison"}:
                ws.auto_filter.ref=f"A1:{get_column_letter(len(headers))}{max(1,len(rows)+1)}"
            for j,w in enumerate(widths,1):
                ws.column_dimensions[get_column_letter(j)].width=min(48,max(12,w+2))
    out=BytesIO()
    wb.save(out)
    return out.getvalue()

def dataframe_bytes(df):
    headers=[str(c) for c in df.columns]
    if len(set(headers))!=len(headers): raise ValueError("Duplicate analysis column labels")
    rows=[dict(zip(headers,row)) for row in df.itertuples(index=False,name=None)]
    return workbook_bytes({"Analysis":{"headers":headers,"rows":rows}})

def download_analysis(st,df,key,filename=None):
    try:
        payload=dataframe_bytes(df)
        st.download_button("Export Excel (.xlsx)",payload,file_name=(filename or key)+".xlsx",mime=MIME,key="xlsx-"+key)
    except (ValueError,TypeError,OverflowError) as exc:
        st.warning("Excel export unavailable for this table: "+str(exc)[:200])

def archive_path(root,captured,h):
    if not re.fullmatch(r"[0-9a-f]{64}",h): raise ValueError("Invalid snapshot hash")
    t=datetime.fromisoformat(captured)
    if t.tzinfo is None: raise ValueError("Snapshot capture time has no timezone")
    t=t.astimezone(timezone.utc)
    return Path(root)/t.strftime("%Y-%m")/("Competition_"+t.strftime("%Y-%m-%d_%H-%M-%SZ")+"_"+h[:16]+".xlsx")

def atomic_write(path,payload):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=None
    try:
        with NamedTemporaryFile(dir=path.parent,prefix=".xlsx-",suffix=".tmp",delete=False) as f:
            tmp=Path(f.name); f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp is not None: tmp.unlink(missing_ok=True)

def matches(path,h):
    """Check existing package integrity and snapshot identifier."""
    if not Path(path).is_file(): return False
    try:
        with ZipFile(path) as z:
            if z.testzip() is not None: return False
        wb=load_workbook(path,read_only=True,data_only=True)
        try: return wb.properties.identifier==h
        finally: wb.close()
    except Exception:
        # A damaged or non-XLSX archive is reconstructed from SQLite.
        return False

def export_snapshot(conn,h):
    row=next((r for r in history(conn) if r[0]==h),None)
    if row is None: raise ValueError("Snapshot not found")
    data=read_snapshot(conn,h)
    return workbook_bytes(data,h),row[1]

def archive_one(conn,h,root=ARCHIVE_ROOT,latest=False):
    row=next((r for r in history(conn) if r[0]==h),None)
    if row is None: raise ValueError("Snapshot not found")
    path=archive_path(root,row[1],h)
    last=Path(root)/LATEST
    # On every call verify the SQLite checksum, including unchanged snapshots.
    data=read_snapshot(conn,h)
    need_archive=not matches(path,h)
    need_latest=latest and not matches(last,h)
    if need_archive or need_latest:
        payload=workbook_bytes(data,h)
        if need_archive: atomic_write(path,payload)
        if need_latest: atomic_write(last,payload)
    return path

def rebuild(conn,root=ARCHIVE_ROOT):
    """Backfill every existing snapshot; never restore/change the current pointer."""
    result={"snapshots":0,"errors":[],"latest":None}
    latest_hash=state(conn,"latest_hash")
    for h,_,_,_ in reversed(history(conn)):
        try:
            archive_one(conn,h,root,latest=(h==latest_hash))
            result["snapshots"]+=1
            if h==latest_hash: result["latest"]=str(Path(root)/LATEST)
        except Exception as exc:
            result["errors"].append(h[:12]+": "+type(exc).__name__)
    return result
