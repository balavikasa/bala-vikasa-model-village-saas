# Acceptance Criteria — SaaS Rebuild

1. Existing normalized data upgrades without loss: 2 PMs, 2 PCs, 9 DAs, 42 villages, 351 committees,
   2,433 committee members and 351 legacy ActionPlan templates remain present.
2. Cluster is persisted only on PC; DA/Village inherit cluster.
3. PM is global read-only; PC cannot read/manage another PC's hierarchy; DA cannot submit outside its
   own villages/plans; Admin does not submit DA field entries.
4. Admin can see disabled rows; PM/PC/DA cannot.
5. Action Plans default to the configured program's current month and preserve months independently.
6. Prepare Next Month copies committee structure, Type and Notes but never copies Assigned Date.
7. Past/completed/overdue plan scheduling is immutable to PC edits.
8. Action-plan Export/Import is user- and month-bound and always previews before an atomic confirm.
9. Attendance status is server-derived: Early / On-time / Postponed; Early and Postponed require Reason.
10. Overdue unsubmitted plans appear as Failure without inserting fake field rows.
11. Committee Member Name selection is master-driven: one name selects directly; multiple names open
    a picker; zero names disables that designation.
12. Selected visit-member IDs are verified against the selected Committee and stored with snapshots.
13. Attendance Total is server-controlled Male + Female; New Members Count is non-negative.
14. Specials require an assigned Specials plan and scope is exactly Under GP or Under VDC.
15. Field images are revalidated/re-encoded to WebP server-side and GPS is range-validated.
16. Offline replay uses unique `client_submission_id` and does not duplicate accepted submissions.
17. Reports list remains concise with View as the detail action; detail shows evidence, GPS/map and
    Committee Member Names; Excel export includes member name/designation.
18. Role-scoped Village Map supports mobile Map/List presentation.
19. Admin master-data transfer previews New/Changed/Moved/Unchanged/Error and omission never deletes.
20. All master/admin mutations are audited; soft-delete/restore and ten-day purge remain operational.
21. Mobile touch controls are at least 44 px and DA/PC/PM navigation is usable at phone widths.
22. Manifest/service worker/offline shell are present for PWA installation.
23. Python source compiles, templates parse, JavaScript syntax checks pass, and both Alembic migrations
    upgrade a temporary SQLite database successfully before release packaging.
