# Hotfix 2026.27.4

Fixes two issues found by the Windows local test run:

1. Windows `zoneinfo` could not load `Asia/Kolkata` when the IANA timezone database was absent.
   `tzdata` is now an explicit dependency, and the server has a safe fixed IST fallback.
2. Automatic master-workbook header discovery treated `Village_ID` / `Committee_ID` / `Member_ID`
   as display-name columns because of tolerant prefix matching. Stable ID headers now have explicit
   aliases, so the approved normalized workbook imports by its intended name columns.

No database migration is required from 2026.27.3 to 2026.27.4.
