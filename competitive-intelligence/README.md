# Competitive Intelligence Engine

Version 1.0.0-rc1 — integrated operational release candidate.

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

The application does not equate market scarcity with demand or observed research activity with product releases. Commercial records preserve currencies and price bases. The commercial MCDA module combines functional overlap, space-sector relevance, commercial availability and documented adoption as explicit scenario intervals, with user-adjustable criterion weights and sensitivity scenarios. Price is deliberately not scored because price bases and currencies are not comparable without additional evidence. No calibrated threat probability is claimed.

## Roadmap completion and acceptance

| Version | Delivered capability |
| --- | --- |
| 0.1 | Read-only API, validation, SQLite history and 24-hour offline-first refresh |
| 0.2 | Intelligence overview, company and product exploration |
| 0.3 | Capability matrix and evidence-level comparison |
| 0.4 | Ownership, capability, deployment and evidence graph |
| 0.5 | Research prioritisation and stale-source review queue |
| 0.6 | Functional overlap bounds, commercial MCDA, sensitivity and sparse similarity/clustering |
| 0.7 | Snapshot changes, evidence-state transitions and fixed-cohort convergence analysis |
| 0.8 | Source-based AIT-VISTA criterion and function traceability, local maturity assessment |
| 0.9 | Opportunity hypotheses, supplier/integration diligence, local demand-evidence register, strategic HTML report |
| 1.0 RC | Integrated Windows workflows, offline import/export, regression and UI tests |

The workbook's optional AIT-VISTA Capabilities and AIT-VISTA System Functions tabs are imported and validated together when present. The latter has two side-by-side registers: its blank separator and duplicate Functionality heading are represented by distinct internal column names. Existing 12-tab snapshots remain readable. Mapped market capabilities are comparison proxies only. Listed system functions default to Implemented under the product owner declaration; optional maturity overrides and demand validation remain local. Competitor unknown remains unknown.

The strategic workspace identifies hypotheses and potential suppliers, not verified partners or validated opportunities. A user-declared demand reference is required before marking demand validated; the application does not independently verify it. Market evolution distinguishes new research evidence from actual commercial releases. Automated external research remains the responsibility of the existing spreadsheet process.

## Updating an existing checkout

If the repository was cloned from a feature branch, close the application and switch once to main after the release PR has merged:

    git fetch origin
    git switch main
    git pull --ff-only

If main does not exist locally, use git switch --track origin/main. Afterwards run UPDATE_WINDOWS.bat for routine code updates. Your ignored local files are not part of Git. Do not use git clean -x or hard reset to update the application.

## Acceptance checklist on the target computer

1. Run INSTALL_WINDOWS.bat and open START_WINDOWS.bat with no internet after dependencies have been installed.
2. Check the synthetic demo, then leave demo mode and configure the real workbook.
3. Authorise read-only OAuth and run SYNC_NOW.bat. Inspect the source validation result and mapping counts.
4. Disconnect internet and restart. Verify company profiles, matrices, graph, reports and strategy pages are available.
5. Force sync offline and confirm that the prior local snapshot is retained. Reconnect, sync and confirm distinct snapshots are archived and identical payloads are deduplicated.
6. Verify historical comparison and restore, then sync again to return to the current source.
7. Close the app and run UPDATE_WINDOWS.bat. Verify the SQLite archive, config and credentials remain.
8. Verify the source workbook remains unchanged.

Release candidate status is intentional until real Windows/OAuth acceptance is completed. Automated tests use synthetic data, not a live Google account.

## Tests

From the application directory, after installation:

    .venv\Scripts\python.exe -m pytest -q

On Linux/macOS, install requirements in a virtual environment and run python -m pytest -q.

Tests use synthetic fixtures, never real competitive data or OAuth. First live sync, Windows launchers and OAuth consent must be verified on the target computer.


## Command Centre (v1.1.0-rc1)

Default workspace uses Comparison Assessment as authoritative direct evidence. Competitive Comparison is checked, not used as a second verdict source. Superseded rows remain in history; contradictory active verdicts become Disputed. The source matrix's descriptive second header row is not a product. Existing snapshots without the new ledger can use legacy workspaces.

Select a competitor cohort and As-Is (default, owner-declared implemented criteria), MVP (optional planning scenario) or Target (optional planning scenario). All listed AIT-VISTA criteria are treated as Supported in As-Is unless explicitly overridden locally. No implementation reference or maturity declaration is required. Source competition classifications determine review group, not a verified substitution verdict. Threat interval combines weighted direct overlap, documented space relevance, commercial status and implementation records. Unknowns are intervals, partial support is 0.5 by convention; no market share or threat probability is inferred. Commercial-axis values are ordinal evidence scenarios. A functional advantage is relative to the selected cohort and the owner-declared AIT-VISTA baseline; sufficiently documented competitor evidence is required for a conclusive comparison. Customer demand and commercial advantage are separate questions. The competition workbook is one input to the wider 5PACE project, not its sole source of truth. Other spreadsheets are not connected by default.

Product baseline settings, effort, strategic value and delivery rationale are local only. The map excludes unknown estimates. Direct benchmark, evidence history, proxy evidence, watchlist and research CSV exports are offline. Snapshot comparisons indicate recorded evidence changes, not actual product release dates. No external research or source writes from this application. Full automated build/buy/partner cost and requirements-ticket integration remain future work.


## Database alignment (v1.2.0-rc1)

Existing Products fields support transparent provisional classification into direct visual AIT candidates, workflow/procurement substitutes, cross-industry candidates, enabling and complementary tools, internal/custom, research/entrant, historical and unresolved roles. These rules are hypotheses, not verified buyer overlap. Source role is retained. Explicit Product Family links group platform/module review entries: family interval is maximum member bounds, never additive or a combined functional offer. Unlinked same-company products are not merged. All products remain individually inspectable. Threat scenario order uses upper then lower bounds; high exposure threshold 0.65 is a heuristic, not a probability. Missing evidence widens exposure rather than automatically reducing it. The map displays commercial status via symbols and provisional role via colour. Select a point or product to see verdicts, rationale and limitations. Head-to-head comparison treats owner-declared functionality as established and does not claim quantitative superiority from a categorical verdict. Customer value and operational performance are separate; no evidence gate on AIT-VISTA support. Research CSV exports the complete selected queue with the eight requested fields and actual local snapshot capture time. No spreadsheet changes or independent scoring database.
