"""Only GET requests to Google Sheets; no spreadsheet mutation API."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote
from filelock import FileLock, Timeout
from core import ROOT, DATA, TABLES, config, connect, due, log, normalize_sheet, state, store
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
TOKEN = ROOT / "credentials" / "token.json"
CLIENT = ROOT / "credentials" / "client_secret.json"

def credentials(interactive=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    c = Credentials.from_authorized_user_file(str(TOKEN), SCOPE) if TOKEN.exists() else None
    if c and not c.valid and c.refresh_token:
        c.refresh(Request())
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
        def get(url,params):
            response=session.get(url,params=params,timeout=timeout)
            response.raise_for_status()
            return response.json()
        meta=get(base,{"fields":"sheets(properties(title,gridProperties)" + ")"})
        tabs=[s["properties"]["title"] for s in meta["sheets"]]
        if not set(TABLES).issubset(tabs):
            raise ValueError("Missing required worksheets")
        params=[("ranges","'"+t.replace("'","''")+"'") for t in tabs]
        params += [("valueRenderOption","FORMATTED_VALUE"),("majorDimension","ROWS")]
        raw=get(base+"/values:batchGet",params)
        results=raw["valueRanges"]
        if len(results)!=len(tabs):
            raise ValueError("Incomplete batch response")
        for t,v in zip(tabs,results):
            returned=v.get("range","").split("!",1)[0].strip("'").replace("''","'")
            if returned!=t:
                raise ValueError("Batch response worksheet mismatch")
        return {t:normalize_sheet(t,v.get("values",[])) for t,v in zip(tabs,results)}

def run(force=False):
    DATA.mkdir(parents=True,exist_ok=True)
    try:
        with FileLock(str(DATA/"sync.lock"),timeout=0):
            with connect() as conn:
                cfg=config()
                if not force and not due(conn,float(cfg["refresh_interval_hours"])):
                    return "Local data is fresh."
            try:
                data=download(cfg)
                with connect() as conn:
                    h=store(conn,data)
                return "Synchronised: "+h[:12]
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
    a=p.parse_args()
    if a.authorise:
        credentials(interactive=True)
        print("Read-only authorisation complete.")
    else:
        try:
            print(run(force=a.force))
        except RuntimeError as e:
            print(e)
            raise SystemExit(1)
