# Village coverage and period reporting implementation plan

Goal: deliver the approved v33 audit's operational reporting journey without redesigning the theme or changing submission/authentication rules.
Spec: supplied Bala_Vikasa_Reporting_Coverage_Gap_Audit_v33.md (G01-G17).

1. Write failing real-data tests for calendar periods, distinct village completion, full pending populations, filtered totals, cross-assignment attribution, active-record policy and export selection.
2. Build a framework-independent reporting engine and a SQLAlchemy adapter that starts from existing scoped_select authorization. Use current active village assignments. Legacy standalone attendance stays explicitly historical; complete village submissions establish Done.
3. Expose read-only coverage JSON/CSV/Excel and a responsive Coverage page with all/done/pending/other tabs, paginated lists, period and owner/submitter filters, performance matrix and matching export.
4. Connect Dashboard, Monitoring, Analytics, Maps and profile drill-downs to the common period/coverage contract. Correct Reports search/summary/export and expose per-row attendance totals.
5. Execute core/export/browser checks and attempt the full project suite/lint; document blocked checks rather than reporting them passed. Package full source, baseline patch and verification evidence.

Rulings: weeks Monday-Sunday in application local time; totals are committee attendance instances, not deduplicated people; new members are separate village-wide totals. Multi-month coverage is distinct villages in range, with month-by-month breakdown shown separately. No production writes, no schema migration, no changes to DA opening page or offline entry-date rules.

## Execution ledger

- Task 1: complete - 19 core tests and 3 export tests watched fail before the new modules, then pass against the implementation. Additional focused regressions reproduced mixed-parent export, period controls, map status and stale-cache problems before fixes.
- Task 2: complete in source - actual SQLAlchemy models/scoping/services pass SQLite fixture checks; real Flask bridge/auth and PostgreSQL remain untested.
- Task 3: complete in source - Coverage register, API, exports and scope/submitter semantics implemented. Chromium in-memory rendering passed 21 assertions including five widths; production navigation/auth are not exercised by this fixture.
- Task 4: complete in source - shared period engine wired across reporting pages; Reports search/export aligned; profiles updated; server error responses structured. Seven Flask acceptance cases are shipped but cannot execute in this runtime.
- Task 5: verified available test layers; full pytest and Ruff attempted and blocked by missing dependencies. Packaging is validated separately by ZIP/manifest/hash and baseline patch reproduction.

Additional ruling: reporting API data is network-only so a relative date preset cannot silently replay stale cached results. This may make reports unavailable offline; field data caching and queued attendance remain preserved.
Additional ruling: current operational parent submissions and standalone historical committee reports remain explicitly distinct. Promoting a partial historical committee record to complete village coverage would fabricate completion.
Additional ruling: custom-range monthly rows count only the selected dates within each month; they do not imply full-month obligations outside the selection.
Additional ruling: existing monthly report filename retained as a compatibility detail; actual period is explicit inside the workbook. Filename refinement is deferred.
Final review: self-review (no subagent tool). No production writes, migrations or shared-branch push. Full runtime/auth/PostgreSQL/CI checks remain a release gate.
Deferred minor: large-history query optimization, without truncating the coverage population.
