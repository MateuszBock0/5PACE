# 5PACE

## Competitive Intelligence Engine

A local, offline-first analytical application for a structured competitive-intelligence workbook. Google Sheets is a read-only source; all analysis and historical data are retained locally.

### Windows workflow

1. Clone the repository (Git is required).
2. Run **INSTALL_WINDOWS.bat** once (Python 3.11 or 3.12 required).
3. Run **START_WINDOWS.bat**. The interface opens locally in your browser.
4. Use **UPDATE_WINDOWS.bat** when you want to fetch new application code.
5. Use **SYNC_NOW.bat** to explicitly refresh the data from Google Sheets.

The Git updater performs a fast-forward-only pull on the checked-out branch and installs dependencies. It refuses a dirty working tree, never performs a hard reset, and never deletes local data. Do not run it while the application is open. Downloading code and synchronising intelligence are independent operations.

See [application documentation](competitive-intelligence/README.md) for first-time read-only authentication, offline behaviour and analytical limitations.

The repository does not contain private workbook identifiers, OAuth credentials, or real intelligence snapshots.
