"""Local archive browser and XLSX download controls."""
import os
from pathlib import Path
from core import connect
from excel_archive import ARCHIVE_ROOT,LATEST,MIME,archive_path,export_snapshot

def archive_page(st,snapshots,head,demo_mode):
    st.header("Excel Archive")
    st.caption("Values-only copies of distinct validated snapshots. SQLite remains authoritative; original formulas, cell formatting, empty grid rows and spreadsheet metadata are not retained.")
    st.code(str(ARCHIVE_ROOT),language=None)
    st.write("Latest accepted snapshot:",head[:16] if head else "None")
    if demo_mode:
        st.info("Disable synthetic demo mode to access the operational archive.")
        return
    if not snapshots:
        st.info("No saved snapshots. Run a successful synchronisation first.")
        return
    a,b=st.columns(2)
    if a.button("Rebuild Excel archive from SQLite",key="archive-rebuild"):
        from sync import rebuild_excel_archive
        try:
            result=rebuild_excel_archive()
            st.write(result)
            if result["errors"]: st.warning("Some files could not be written. Close open Excel workbooks and retry.")
            else: st.success("Archive rebuilt from local snapshots; no network needed.")
        except Exception as exc: st.error("Archive rebuild failed: "+type(exc).__name__)
    if b.button("Open archive folder",disabled=os.name!="nt",key="archive-open"):
        try:
            ARCHIVE_ROOT.mkdir(parents=True,exist_ok=True)
            os.startfile(str(ARCHIVE_ROOT))
        except OSError: st.error("Could not open archive folder.")
    labels={h:t+" · "+h[:16]+" · "+src for h,t,src,_ in snapshots}
    chosen=st.selectbox("Historical snapshot to download",list(labels),index=list(labels).index(head) if head in labels else 0,format_func=labels.get,key="archive-snapshot")
    try:
        with connect() as conn: payload,captured=export_snapshot(conn,chosen)
        st.download_button("Download selected snapshot XLSX",payload,file_name=archive_path(ARCHIVE_ROOT,captured,chosen).name,mime=MIME,key="archive-download")
    except Exception as exc:
        st.error("Snapshot Excel export failed: "+type(exc).__name__)
    st.subheader("Local archive files")
    rows=[]
    for h,t,src,_ in snapshots:
        p=archive_path(ARCHIVE_ROOT,t,h)
        rows.append({"Captured UTC":t,"Snapshot":h[:16],"Source":src,"Archived":p.is_file(),"File":str(p.relative_to(ARCHIVE_ROOT))})
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.caption("Archive status shows file existence. Rebuild checks package integrity and the stored snapshot identifier. Latest is the latest accepted snapshot, not the restored historical view.")
