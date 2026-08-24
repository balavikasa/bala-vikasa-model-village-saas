# Upgrade to 2026.27.3

This release changes the product from legacy ActionPlan templates to immutable monthly ActionPlan
occurrences and adds Visit Designation member snapshots.

## Safest local upgrade path

Keep the old project folder untouched until the new release is verified.

```powershell
# Example locations; adjust to your folders.
$old = "C:\Users\Kalyan Charan\Downloads\bala_vikasa_model_village_2026_27"
$new = "C:\Users\Kalyan Charan\Downloads\bala_vikasa_model_village_saas_2026_27"

# Copy the existing local database into the NEW application's instance folder.
New-Item -ItemType Directory -Force "$new\instance" | Out-Null
Copy-Item "$old\instance\model_village.db" "$new\instance\model_village.db"

# Copy existing evidence uploads if present.
if (Test-Path "$old\uploads") {
    Copy-Item "$old\uploads" "$new\uploads" -Recurse -Force
}
```

Then:

```powershell
Set-Location $new
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env

# Keep another DB backup immediately before migration.
Copy-Item .\instance\model_village.db .\instance\model_village.pre-migration.db

python -m flask --app wsgi db upgrade

# The original master workbook did not carry Village GPS coordinates.
# This explicit command fills missing coordinates from the approved prototype mapping.
python -m flask --app wsgi backfill-village-coordinates

python -m flask --app wsgi run --debug
```

## Migration behavior

Migration `20260822_0002`:

- keeps existing PM/PC/DA/Village/Committee/Member/User rows;
- keeps existing ActionPlan rows as legacy/template rows with `plan_month=NULL`;
- adds monthly plan Type/Month/Prepared-From fields;
- adds Attendance `new_members_count`;
- adds `attendance_visit_members`;
- links new Specials submissions to monthly plans and status/reason.

Legacy ActionPlan rows remain non-executable. This is intentional. PC creates actual monthly schedule
occurrences through Action Plans → Export / Import or single-plan edit.

Legacy rows that happened to contain an old/test `assigned_date` still migrate safely because
`plan_month=NULL`; they are not treated as executable monthly assignments.

## First verification after migration

Sign in with each test role and verify:

1. Admin: Overview/Admin/Data Transfer/Map/Reports load.
2. PM: global Overview/People/Plans/Reports/Map are read-only.
3. PC: Action Plans opens current month and shows only own DAs/committees.
4. PC: export current month, fill at least three rows (future/today/past date within the month where
   meaningful), Validate, Preview and Confirm.
5. DA: assigned plans appear under the correct Village/Committee.
6. DA Attendance: one-name designation selects directly; multi-name designation opens picker.
7. Report list stays concise; View shows member names, image/GPS/map detail.
8. Prepare Next Month creates the next month with Type/Notes copied and Assigned Date blank.

## Rollback

If verification fails before you have accepted new production writes:

```powershell
# Stop Flask first.
Remove-Item .\instance\model_village.db
Copy-Item .\instance\model_village.pre-migration.db .\instance\model_village.db
```

Also revert to the previous application code. Do not restore only the database while continuing to
serve the newer schema-dependent code.
