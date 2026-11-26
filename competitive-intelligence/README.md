# Competitive Intelligence Engine

Version 0.1.0 — initial integrated prototype.

## First-time installation and authentication

1. Install Git for Windows and Python 3.11 or 3.12 (with the Python launcher).
2. Clone the repository and run the root INSTALL_WINDOWS.bat while online.
3. In Google Cloud Console, create/select a project, enable Google Sheets API, configure the OAuth consent screen and add your account as a test user if necessary.
4. Create an OAuth client ID of type Desktop app; download the JSON file to competitive-intelligence/credentials/client_secret.json. Never commit this file.
5. Run START_WINDOWS.bat and open Synchronisation centre. Enter the spreadsheet ID (the segment between /d/ and /edit in the workbook URL), then save local settings. Alternatively edit config.local.json manually.
6. Run AUTHORISE_WINDOWS.bat to sign in with the Google account that already has access to the workbook. Grant only spreadsheets.readonly access. This does not require changing workbook sharing.
7. Run SYNC_NOW.bat and refresh the application. The first successful sync creates the local database.

A public Google Sheets link is not needed. Do not publish the workbook. Authentication is per computer/account; a ChatGPT connector cannot provide its token to the installed Python program. Google OAuth consent-screen testing mode may require reauthorisation after token expiry.

## Daily operation

START_WINDOWS.bat starts the interface and independently checks for stale data. If the last successful Google Sheets sync is at least 24 hours old, it attempts a refresh. The interval can be changed locally. A failed download, invalid dataset, duplicate ID, broken foreign key, disappearing immutable ID, or invalid assessment status retains the last valid dataset. A separate process and interprocess file lock prevent overlapping data refreshes. No external AI service is used.

With a previously downloaded valid dataset, disconnect the network and launch START_WINDOWS.bat: all analytic views and report exports remain local. Initial installation, Git updates and OAuth require internet. First use without a dataset offers explicitly labelled synthetic demo mode; demo records never enter the live database.

The application binds to 127.0.0.1 and disables Streamlit telemetry. External evidence URLs require connectivity if opened.

## Files and persistence

- core.py: normalisation, required headers, identifiers, referential validation, archive and change detection.
- sync.py: OAuth and read-only GET requests to Google Sheets.
- analytics.py: current assessment interpretation, comparison matrices, uncertainty bounds, sensitivity, similarity, clustering, graph and research priorities.
- app.py: local Streamlit interface and exports.
- demo.py: fictitious test fixture only.
- data/intelligence.db: SQLite database containing immutable compressed JSON snapshots, current and latest pointers, last successful refresh and log.
- credentials/: local OAuth client and token.
- config.local.json: local spreadsheet ID and analytical settings.
- tests/: synthetic unit and regression tests.

All local data, credentials, config, caches and generated reports are ignored by Git. Back up the data directory while the application and sync process are stopped (including SQLite WAL files if present), and keep credentials separately secured. SQLite storage is not encrypted at rest: use OS disk encryption and account access controls if required.

Each distinct validated payload is archived by SHA-256. Identical successful reads refresh last_successful_sync without duplicating the snapshot. Snapshot insertion and pointer update occur in one SQLite transaction. Historical restore changes only the local current pointer. A subsequent source sync uses the latest source snapshot as its validation baseline.

The archived payload includes every source worksheet's displayed values, not original Google Sheets formulas, colours or comments. This is a data archive, not a complete workbook backup. New tabs are archived automatically; required existing headers remain validated. The source may change concurrently with a read; batchGet reduces but does not eliminate this risk.

## Analytical modules

- Overview, company/product profiles, source observations and evidence registers.
- Capability matrix with explicit unknown, unassessed, announced, disputed and proposed states.
- Landscape and configurable weighted functional-overlap MCDA bounds; partial support = 0.5 by convention, unknown states [0,1], non-applicable excluded. Separate evidence completeness and weight sensitivity.
- Knowledge graph from product ownership, documented capabilities and evidence references.
- Research gap prioritisation, weak-evidence discovery, and unresolved leads.
- Similarity based on shared determinate capabilities; complete-linkage clustering on a comparable subset.
- Technology gap analysis with manually selected AIT-VISTA maturity and optional local system-function mappings.
- Historical snapshot comparison, observations by date type, restore and record-count trends.
- Standalone HTML, CSV and JSON exports.

Configuration keys: priority_capabilities (list of real Capability IDs), vista_capabilities (ID to Planned/Implemented/Demonstrated/Verified), function_mapping (capability ID to list of internal function IDs), min_shared_capabilities.

The application does not equate market scarcity with demand or observed research activity with product releases. Commercial records preserve currencies and price bases. Full commercial threat modelling, automated external research, exact product-release reconstruction, uncertainty calibration and integration with a separate systems-engineering repository require reviewed methodology and additional data; they are not claimed as implemented. Similarity and gap analysis are exploratory on sparse data.

## Tests

From the application directory, after installation:

    .venv\Scripts\python.exe -m pytest -q

On Linux/macOS, install requirements in a virtual environment and run python -m pytest -q.

Tests use synthetic fixtures, never real competitive data or OAuth. First live sync, Windows launchers and OAuth consent must be verified on the target computer.
