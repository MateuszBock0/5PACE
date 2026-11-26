"""Data contract and transactional, content-addressed local archive."""
from __future__ import annotations
import gzip
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DB = DATA / "intelligence.db"
SCHEMA_VERSION = 1
TABLES = {
    "Main": ("Observation ID", "Company ID"),
    "Observations": ("Observation ID", "Company ID"),
    "To be Confirmed": ("Lead ID",),
    "Key Competitors": ("Evidence ID",),
    "Archive": (),
    "Notes": ("Rule", "Description"),
    "Companies": ("Company ID", "Company Name"),
    "Products": ("Product ID", "Company ID", "Product Name"),
    "Capabilities": ("Capability ID", "Capability Name", "Category ID", "Taxonomy Status"),
    "Capability Assessment": ("Assessment ID", "Product ID", "Capability ID", "Availability Status", "Evidence Level", "Review Status", "Supersedes Assessment ID"),
    "Deployments": ("Deployment ID", "Product ID"),
    "Commercial Intelligence": ("Commercial Record ID", "Product ID"),
}
IDS = {k: v[0] for k, v in TABLES.items() if v and k != "Notes"}
STATUS = {"Supported", "Partially supported", "Announced", "Explicitly unsupported", "Unknown", "Not applicable"}
EVIDENCE = {"Independently verified", "Independently documented", "Official technical documentation", "Vendor claim", "Inferred", "Insufficient evidence"}
REVIEW = {"Proposed", "Reviewed", "Disputed", "Superseded"}

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def config():
    c = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
    p = ROOT / "config.local.json"
    if p.exists():
        c.update(json.loads(p.read_text(encoding="utf-8")))
    return c

def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()

def normalize(values):
    if not values:
        return {"headers": [], "rows": []}
    h = [str(v or "").strip() for v in values[0]]
    while h and not h[-1]:
        h.pop()
    if not h or any(not x for x in h) or len(set(h)) != len(h):
        raise ValueError("Blank or duplicate column headers")
    rows = []
    for raw in values[1:]:
        if any(v not in ("", None) for v in raw[len(h):]):
            raise ValueError("Data outside header width")
        if not any(v not in ("", None) for v in raw):
            continue
        rows.append(dict(zip(h, (list(raw) + [None]*len(h))[:len(h)])))
    return {"headers": h, "rows": rows}

def normalize_sheet(name, values):
    """Preserve the two side-by-side tables in the system-functions worksheet."""
    if name == "AIT-VISTA System Functions" and values:
        expected = ["Function ID", "Functionality", "Consolidated Capability ID", "Comparison criterion IDs", "", "Capability ID", "Functionality"]
        actual = [str(v or "").strip() for v in values[0][:7]]
        if actual == expected:
            if any(len(row)>4 and row[4] not in ("",None) for row in values[1:]):
                raise ValueError("System-function separator column is not empty")
            values = [["Function ID","Functionality","Consolidated Capability ID","Comparison criterion IDs","__separator__","Capability ID","Consolidated Functionality"]+list(values[0][7:])] + list(values[1:])
    table=normalize(values)
    if name in ("Observations","Main") and "Space industry" in table["headers"]:
        # Google Sheets checkbox defaults occupy otherwise blank grid rows.
        # Only discard a row when the unchecked checkbox is its sole content.
        # A real observation with a false checkbox or a missing ID is retained.
        table["rows"]=[
            r for r in table["rows"]
            if not (
                (r.get("Space industry") is False or
                 (isinstance(r.get("Space industry"),str) and r["Space industry"].strip().upper()=="FALSE"))
                and all(v in ("",None) for k,v in r.items() if k!="Space industry")
            )
        ]
    return table

def records(data, name):
    return data[name]["rows"]

def value(row, field):
    v = row.get(field)
    return "" if v is None else str(v).strip()

def split_ids(v):
    return [x.strip() for x in str(v or "").split(";") if x.strip()]

def validate(data, previous=None):
    errors, warnings = [], []
    if not set(TABLES).issubset(data):
        return ["Missing worksheets: " + str(set(TABLES)-set(data))], warnings
    keys = {}
    for name, fields in TABLES.items():
        table = data[name]
        if not set(fields).issubset(table["headers"]):
            errors.append(f"{name}: missing required columns {set(fields)-set(table['headers'])}")
        if name in IDS:
            field = IDS[name]
            ids = [value(r, field) for r in records(data, name)]
            if any(not x for x in ids) or len(ids) != len(set(ids)):
                errors.append(f"{name}: blank or duplicate {field}")
            keys[name] = set(ids) - {""}
        for r in records(data, name):
            integrity = value(r, "Integrity Check")
            if integrity and integrity.upper() not in ("OK", "PASS"):
                errors.append(f"{name}: source integrity check is not OK")
            if any(value(r,k) in ("#REF!", "#N/A", "#VALUE!", "#ERROR!", "#DIV/0!") for k in ("Integrity Check", *fields)):
                errors.append(f"{name}: source formula error")
    def check(table, field, target, multiple=False, required=False):
        for r in records(data, table):
            v = value(r, field)
            if required and not v:
                errors.append(f"{table}: missing {field}")
            for k in split_ids(v) if multiple else ([v] if v else []):
                if k not in keys.get(target, set()):
                    errors.append(f"{table}: {field} {k} absent from {target}")
    check("Products", "Company ID", "Companies", required=True)
    check("Products", "Product Family", "Products")
    check("Capabilities", "Parent Capability ID", "Capabilities")
    for t in ("Main", "Observations"):
        check(t, "Company ID", "Companies", required=True)
        check(t, "Related observation ID", "Observations")
    check("Main", "Observation ID", "Observations", required=True)
    for t in ("Capability Assessment", "Deployments", "Commercial Intelligence"):
        check(t, "Product ID", "Products", required=True)
        check(t, "Related Observation IDs", "Observations", multiple=True)
        check(t, "Related Evidence IDs", "Key Competitors", multiple=True)
    check("Products", "Related Observation IDs", "Observations", multiple=True)
    check("Key Competitors", "Related Observation IDs", "Observations", multiple=True)
    check("Key Competitors", "Related Lead IDs", "To be Confirmed", multiple=True)
    check("To be Confirmed", "Related Observation IDs", "Observations", multiple=True)
    check("Capability Assessment", "Capability ID", "Capabilities", required=True)
    check("Capability Assessment", "Supersedes Assessment ID", "Capability Assessment")
    assessments = {value(r, "Assessment ID"): r for r in records(data, "Capability Assessment")}
    for k, r in assessments.items():
        if value(r,"Availability Status") not in STATUS or value(r,"Evidence Level") not in EVIDENCE or value(r,"Review Status") not in REVIEW:
            errors.append(f"Assessment {k}: invalid status")
        if value(r,"Availability Status") not in ("Unknown","Not applicable") and not (value(r,"Source URL") and value(r,"Evidence Description")):
            errors.append(f"Assessment {k}: missing source or evidence description")
        old = value(r,"Supersedes Assessment ID")
        if old in assessments:
            a = assessments[old]
            if any(value(a,f)!=value(r,f) for f in ("Product ID","Capability ID")):
                errors.append(f"Assessment {k}: supersedes different product/capability")
        seen = {k}
        while old in assessments:
            if old in seen:
                errors.append(f"Assessment {k}: supersession cycle")
                break
            seen.add(old)
            old = value(assessments[old],"Supersedes Assessment ID")
    for r in records(data,"Commercial Intelligence"):
        if any(value(r,f) for f in ("Subscription Cost","One-time Licence Cost","Deployment Cost","Integration Cost")) and not value(r,"Currency"):
            errors.append("Commercial price lacks currency")
    for t in ("Companies","Products","Capabilities","Capability Assessment","Observations"):
        if not records(data,t):
            errors.append(f"{t}: empty critical table")
    # The source may expose an optional, separately governed AIT-VISTA mapping.
    if "AIT-VISTA Capabilities" in data or "AIT-VISTA System Functions" in data:
        from product_intelligence import validate_mapping
        errors.extend(validate_mapping(data))
    if previous:
        for name in ("AIT-VISTA Capabilities","AIT-VISTA System Functions"):
            if name in previous and name not in data:
                errors.append(f"{name}: previously synchronised worksheet disappeared")
        for name, field in IDS.items():
            if name == "Main":  # derived current view, not immutable history
                continue
            before = {value(r,field) for r in records(previous,name)}
            missing = before - keys.get(name,set())
            if missing:
                errors.append(f"{name}: {len(missing)} previously recorded IDs disappeared; investigate before replacing local data")
    return sorted(set(errors)), warnings

@contextmanager
def connect(path=DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS snapshots (hash TEXT PRIMARY KEY, captured_at TEXT NOT NULL, source TEXT NOT NULL, schema_version INTEGER NOT NULL, payload BLOB NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS sync_log (at TEXT, status TEXT, detail TEXT)")
        conn.commit()
        with conn:
            yield conn
    finally:
        conn.close()

def state(conn, key, default=None):
    row=conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return row[0] if row else default

def set_state(conn,key,v):
    conn.execute("INSERT INTO state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(v)))

def read_snapshot(conn,h=None):
    h = h or state(conn,"current_hash")
    row=conn.execute("SELECT payload FROM snapshots WHERE hash=?",(h,)).fetchone()
    if not row:
        return None
    data=json.loads(gzip.decompress(row[0]))
    if digest(data)!=h:
        raise ValueError("Snapshot checksum mismatch")
    return data

def history(conn):
    return conn.execute("SELECT hash,captured_at,source,schema_version FROM snapshots ORDER BY captured_at DESC,hash").fetchall()

def due(conn,hours=24,now=None):
    last=state(conn,"last_successful_sync")
    if not last or not state(conn,"current_hash"):
        return True
    try:
        age=((now or datetime.now(timezone.utc))-datetime.fromisoformat(last)).total_seconds()
        return age<0 or age>=3600*hours
    except (TypeError,ValueError):
        return True

def log(conn,status,detail):
    conn.execute("INSERT INTO sync_log VALUES (?,?,?)",(utcnow(),status,str(detail)[:4000]))

def store(conn,data,source="Google Sheets",mark_synced=True):
    previous=read_snapshot(conn,state(conn,"latest_hash"))
    errors,_=validate(data,previous)
    if errors:
        raise ValueError("; ".join(errors[:20]))
    h=digest(data)
    captured=utcnow()
    conn.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?)",(h,captured,source,SCHEMA_VERSION,gzip.compress(canonical(data))))
    set_state(conn,"current_hash",h)
    set_state(conn,"latest_hash",h)
    if mark_synced:
        set_state(conn,"last_successful_sync",utcnow())
    log(conn,"success" if mark_synced else "import",h)
    return h

def restore(conn,h):
    if read_snapshot(conn,h) is None:
        raise ValueError("Snapshot not found")
    set_state(conn,"current_hash",h)
    log(conn,"restore",h)

def diff(before,after):
    changes=[]
    for name,field in IDS.items():
        if name=="Main":
            continue
        a={value(r,field):r for r in records(before,name)}
        b={value(r,field):r for r in records(after,name)}
        for k in sorted(set(a)|set(b)):
            if k not in a:
                changes.append({"Table":name,"ID":k,"Change":"Added","Fields":""})
            elif k not in b:
                changes.append({"Table":name,"ID":k,"Change":"Removed","Fields":""})
            else:
                fields=[f for f in sorted(set(a[k])|set(b[k])) if a[k].get(f)!=b[k].get(f) and not (f.endswith(" Count") or f=="Integrity Check")]
                if fields:
                    changes.append({"Table":name,"ID":k,"Change":"Modified","Fields":"; ".join(fields)})
    return changes
