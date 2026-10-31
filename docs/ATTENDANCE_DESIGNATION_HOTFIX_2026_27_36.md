# Bala Vikasa Model Village — DA attendance designation compatibility fix

Release: **2026.27.36** (applies to version 2026.27.35). This is a **server-side compatibility fix**, not a database import or schema migration.

## Verified cause

The screenshot reports: `D.Mounika has an unsupported designation in master data.`

The uploaded `MMU File-2026-27-Oct -Vasantha.xlsx`, sheet `07-Comm-list-2026-27`, row **1631**, contains **D.Mounika** in **Nayakuni Thanda / Youth & Technical** with designation **`S\M`**. Other source designations include `Secretory`, `Wise President`, `Mem`, and lower-case `member`. The backend `_selected_members` previously rejected any value outside `President`, `Vice President`, `Secretary`, `Member`, even though the UI displayed such records and allowed selection.

## Fix

- A member remains selectable if they are active, not deleted, and belong to the exact submitted committee.
- **Designation is descriptive, not a rule for attendance eligibility.** Any existing designation spelling (including NULL) is accepted.
- The original designation is kept unchanged in master data and copied into the submitted member snapshot. No assumption is made that `S\M` means `Member` or `Secretary`.
- Gender is still validated as Male/Female for exact counts. GPS/photo/one-village/all-committees requirements remain in force.
- No existing user, village, committee, attendance record, data or password is changed by installing this code.

## Deployment

1. Verify the running application is **2026.27.35** (`/healthz`), or reconcile the patch against your deployed commit.
2. Back up the deployment as usual. Run GitHub CI (including full pytest + Ruff) before deploying.
3. Apply the supplied Git patch to the current repository, or deploy the complete updated ZIP via your existing Coolify workflow.
4. Redeploy the Flask service. No `flask db upgrade` is required for this fix.
5. Verify `/healthz` reports `2026.27.36`.
6. In a **non-production test environment**, log in as a DA and select a committee member with designation `S\M`. Submit attendance for all committees using one photo and valid GPS; verify report names, attendance counts and designation snapshot.
7. Only after successful staging checks, deploy to production and try again using **a fresh evidence photo and GPS** if the prior mobile form has been reloaded.

## Temporary Admin workaround without deploying code

Under **Master Data → Committee Members**, find D.Mounika in **Nayakuni Thanda → Youth & Technical**. If the field team confirms which of the standard roles applies, Admin may correct the designation. Do **not** arbitrarily change `S\M` to `Member`; that would corrupt role information. Similar source spellings may cause further blocks until the server fix is deployed.

## Local validation

- Regression: `python -m pytest --noconftest -q tests/test_member_designation_compatibility.py` — **8 passed**, including a regression test that failed before the fix.
- Python/JS/Jinja and static contracts: `python scripts/validate_release.py` — passed except runtime skipped; Flask dependencies are unavailable here.
- Full Flask/PostgreSQL tests and real mobile submission: **not tested in this environment**.

## Optional PostgreSQL read-only audit

```sql
SELECT cm.id, cm.full_name, cm.designation, c.name AS committee, v.name AS village
FROM committee_members AS cm
JOIN committees AS c ON c.id = cm.committee_id
JOIN villages AS v ON v.id = c.village_id
WHERE cm.is_deleted = false AND cm.is_enabled = true
  AND lower(btrim(coalesce(cm.designation, ''))) NOT IN
      ('president', 'vice president', 'secretary', 'member')
ORDER BY v.name, c.name, cm.full_name;
```

Treat the result as **data to review**, not records to mass-update blindly.
