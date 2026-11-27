"""Only GET requests to Google Sheets; no spreadsheet mutation API."""
from __future__ import annotations
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import quote
from filelock import FileLock, Timeout
from core import ROOT, DATA, TABLES, config, connect, due, log, normalize_sheet, state, store
from excel_archive import ARCHIVE_ROOT, archive_one, rebuild
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
TOKEN = ROOT / "credentials" / "token.json"
CLIENT = ROOT / "credentials" / "client_secret.json"

def credentials(interactive=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    c = Credentials.from_authorized_user_file(str(TOKEN), SCOPE) if TOKEN.exists() else None
    if c and not c.valid and c.refresh_token:
        try:
            c.refresh(Request())
        except Exception:
            if not interactive:
                raise RuntimeError("OAuth refresh failed. Run AUTHORISE_WINDOWS.bat while online.") from None
            c=None
    if not c or not c.valid:
        if not interactive:
            raise RuntimeError("Google OAuth not configured. Run AUTHORISE_WINDOWS.bat.")
        c = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPE).run_local_server(port=0)
    if not c.has_scopes(SCOPE):
        raise RuntimeError("Read-only Google Sheets scope not granted.")
    if c.granted_scopes and set(c.granted_scopes) - set(SCOPE):
        raise RuntimeError("Token includes unexpected scopes. Revoke and authorise with a dedicated client.")
    TOKEN.parent.mkdir(parents=True,exist_ok=True)
    tmp=TOKEN.with_suffix(".tmp")
    tmp.write_text(c.to_json(),encoding="utf-8")
    tmp.replace(TOKEN)
    return c

def download(cfg):
    from google.auth.transport.requests import AuthorizedSession
    sid=cfg["spreadsheet_id"].strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+",sid):
        raise ValueError("Set spreadsheet_id in config.local.json (ID only, not URL).")
    timeout=float(cfg["request_timeout_seconds"])
    base="https://sheets.googleapis.com/v4/spreadsheets/"+quote(sid,safe="")
    with AuthorizedSession(credentials()) as session:
        from requests.exceptions import Timeout as RequestTimeout, ConnectionError
        def get(url,params,label):
            for attempt in range(3):
                try:
                    response=session.get(url,params=params,timeout=(min(timeout,10),timeout))
                    if response.status_code in (429,500,502,503,504) and attempt<2:
                        print(f"{label}: temporary HTTP {response.status_code}; retrying",flush=True)
                    else:
                        response.raise_for_status()
                        return response.json()
                except (RequestTimeout,ConnectionError):
                    if attempt==2:
                        raise ValueError(f"{label}: network timeout or connection failure after 3 attempts") from None
                    print(f"{label}: temporary network failure; retrying",flush=True)
                time.sleep(2**attempt)
            raise ValueError(f"{label}: retry limit reached")
        meta=get(base,{"fields":"sheets(properties(title,gridProperties))"},"Workbook metadata")
        tabs=[s["properties"]["title"] for s in meta["sheets"]]
        if not set(TABLES).issubset(tabs):
            raise ValueError("Missing required worksheets")
        data={}
        for start in range(0,len(tabs),4):
            group=tabs[start:start+4]
            label=f"Worksheets {start+1}-{start+len(group)}/{len(tabs)}"
            print(label+": "+", ".join(group),flush=True)
            params=[("ranges","'"+t.replace("'","''")+"'") for t in group]
            params += [("valueRenderOption","FORMATTED_VALUE"),("majorDimension","ROWS")]
            raw=get(base+"/values:batchGet",params,label)
            results=raw["valueRanges"]
            if len(results)!=len(group):
                raise ValueError(label+": incomplete batch response")
            for t,v in zip(group,results):
                returned=v.get("range","").split("!",1)[0].strip("'").replace("''","'")
                if returned!=t:
                    raise ValueError(label+": batch response worksheet mismatch")
                data[t]=normalize_sheet(t,v.get("values",[]))
                print(f"  {t}: {len(data[t]['rows'])} imported rows",flush=True)
        print("Validating complete downloaded dataset...",flush=True)
        return data

def archive_latest(h):
    """Export after SQLite commit; Excel errors do not invalidate source sync."""
    try:
        with connect() as conn:
            archive_one(conn,h,ARCHIVE_ROOT,latest=True)
        return ""
    except Exception as exc:
        detail="Excel archive warning: "+type(exc).__name__+". SQLite snapshot retained. Close Excel files and rebuild the archive."
        with connect() as conn: log(conn,"archive_warning",detail)
        return "\n"+detail

def rebuild_excel_archive():
    DATA.mkdir(parents=True,exist_ok=True)
    with FileLock(str(DATA/"sync.lock"),timeout=0):
        with connect() as conn:
            result=rebuild(conn,ARCHIVE_ROOT)
            log(conn,"archive_rebuild",f"{result['snapshots']} snapshots; {len(result['errors'])} errors")
        return result

def run(force=False):
    DATA.mkdir(parents=True,exist_ok=True)
    try:
        with FileLock(str(DATA/"sync.lock"),timeout=0):
            with connect() as conn:
                cfg=config()
                fresh=not force and not due(conn,float(cfg["refresh_interval_hours"]))
                head=state(conn,"latest_hash")
            if fresh:
                return "Local data is fresh."+(archive_latest(head) if head else "")
            try:
                data=download(cfg)
                with connect() as conn:
                    h=store(conn,data)
                return "Synchronised: "+h[:12]+archive_latest(h)
            except Exception as exc:
                # Do not log OAuth tokens, response bodies or source URLs.
                detail=str(exc)[:2000] if isinstance(exc,ValueError) else type(exc).__name__
                with connect() as conn:
                    log(conn,"failed",detail)
                raise RuntimeError("Synchronisation failed; previous dataset retained. "+detail) from None
    except Timeout:
        return "Synchronisation already in progress."

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--force",action="store_true")
    p.add_argument("--if-stale",action="store_true")
    p.add_argument("--authorise",action="store_true")
    p.add_argument("--rebuild-excel",action="store_true")
    a=p.parse_args()
    if a.authorise:
        credentials(interactive=True)
        print("Read-only authorisation complete.")
    elif a.rebuild_excel:
        try:
            result=rebuild_excel_archive()
            print(json.dumps(result,indent=2))
            if result["errors"]: raise SystemExit(1)
        except Timeout:
            print("Synchronisation or archive rebuild already in progress.")
            raise SystemExit(1)
    else:
        try:
            print(run(force=a.force))
        except RuntimeError as e:
            print(e)
            raise SystemExit(1)
