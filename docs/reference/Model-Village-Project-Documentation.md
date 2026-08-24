# Model Village — Project Documentation

> **Purpose of this document:** a complete, self-contained brief on the Model Village project — background, requirements, data model, architecture decisions, and current build status — written so a new person (human or LLM) can be handed this file with zero other context and understand the whole project. Written from project start onward, in chronological/logical order.

---

## 1. What This Project Is

**Organization:** Bala Vikasa, an NGO operating in Telangana, India.
**Program:** Model Village Program, 2026–27 cycle.
**Donor:** Sopar.
**Scope:** 42 villages, organized into 2 Clusters — **CSRB** and **PDTC**.

Each village runs a set of community-governance committees (VDC, Water, Health, Farmer, Education, etc.). Bala Vikasa field staff (**DAs**) are assigned to specific villages, and are supposed to visit committees on a schedule (**Action Plans**) and log two kinds of field activity:

1. **Attendance** — did the committee meet, who showed up, how many members
2. **Specials** — one-off special activities/events run under a committee

The project is to digitize this: a system where field staff log visits from a phone, coordinators monitor progress, and a program manager and admin oversee the whole thing — replacing what is currently tracked in a single large, messy Excel workbook.

---

## 2. Origin — The Source Data

The project started from one file: **`MV-Comittees-26-27.xlsx`** — a single sheet, 2,885 rows × 43 columns, containing:

- A **summary block** (42 rows, one per village): DA name, District, Mandal, Village, Cluster, committee counts, Male/Female totals, plus blank monthly tracker columns (Jun 2026 → Mar 2027).
- A **detailed list block**: for each village, a repeated set of committees (VDC, Environment, Education, Technical & Youth, Water, Health, Farmer, Problem Solving, Gender, and — for 5 villages only — a 10th committee, Anti-Liquor & Alcohol Prohibition), each listing member Name, Male/Female flag, Designation (President/Vice President/Secretary/Member), and Mobile Number.

### Data quality issues found in the source (and fixed downstream)

- Inconsistent spellings: Siddipeta/Siddipet → **Siddipet**; Janagon/Janagoan/Janagam → **Jangaon**; Jagadevpur/Jagadhevpur → **Jagdevpur**; Govindaraopet/Govindaraopeta → **Govindaraopet**; "T Ramesh"/"T.Ramesh" and "R Vinay"/"R.Vinay" merged.
- 24 raw spelling variants of Designation, normalized to 4: **President, Vice President, Secretary, Member** (raw text preserved in a `Designation_Raw` field for audit).
- The source file's **own committee subtotal rows were wrong** — they undercounted vs. the actual listed members (1,243 Male/1,142 Female vs. the real 1,278/1,154). All downstream totals are computed fresh from the actual member list, never from the source subtotals.
- 130 mobile numbers malformed (wrong digit count, letters like `o`, zeros), 149 blank — **~11.5% of the 2,433 members have no usable mobile number**.
- 1 member (N. Isthari, Farmer committee, Palugugadda) has neither Male nor Female flagged — marked `Unknown`, needs manual resolution.
- Committee count per village genuinely ranges **6 to 10**, not a fixed 9 — real field variation, not a data error.

### Fields the client (Kalyan) specified as required, at project start

DA-Name · Village · Mandal · District · Cluster (PDTC/CSRB) · Committee Name · Committee Member Designations (Name + Designation) · Male · Female · Mobile Number · Committee Meeting Action Plans · **Specials** (individual action plans under GP/VDC — this did not exist in the source file at all; it's new structure).

---

## 3. Role Hierarchy

Finalized hierarchy, confirmed with the client mid-project (an earlier assumption — 1 PM per Cluster — was corrected: PMs are **not** cluster-scoped):

```
Admin (1 person)  →  PM (2 people)  →  PC (2+ people)  →  DA (9 people)
```

| Role | Count | Cluster-scoped? | Sees | Can do |
|---|---|---|---|---|
| **Admin** | 1 (IT & Head of Org) | No — sees everything | Everything, including disabled records | Full CRUD: Add, Edit, Move, Enable/Disable, Delete (soft, to a Bin), Restore. Only role that can do any of this. |
| **PM** (Programme Manager) | 2 | No — deliberately not tied to a Cluster | Every PC's data and every DA's individual profile, across both Clusters | Read-only monitoring |
| **PC** (Project Coordinator) | 2 today, one per Cluster (PC01="CSRB", PC02="PDTC") — structure supports more than one PC per Cluster later | Yes | Only their own DAs' data | Creates/assigns Action Plans to their DAs; monitors DA submissions (read-only) |
| **DA** (Development Agent) | 9 | Inherited from their PC | Only their own assigned villages | Executes Action Plans: submits Attendance and Specials entries |

**Cluster inheritance chain:** `PC.Cluster` (the only place Cluster is actually stored) → `DA.Cluster` (derived from their PC) → `Village.Cluster` (derived from their DA). Nothing independently stores Cluster below PC level — this was a deliberate correction so Cluster can never drift out of sync between a DA and their PC.

Login is by **email or mobile number + password** for every role.

---

## 4. Data Model (Master Data Schema)

Built first as a normalized Excel workbook (**`MV-Master-Data-26-27.xlsx`**, 10 sheets, 4,000+ live formulas, zero hardcoded totals), then translated into a real SQLAlchemy/Flask schema. Entities:

| Entity | Key fields | Notes |
|---|---|---|
| **PM** | pm_code, name, email, mobile | No Cluster field |
| **PC** | pc_code, name, **cluster**, email, mobile | Cluster lives here, nowhere else independently |
| **DA** | da_code, name, **pc_id** (FK), email, mobile | Cluster is a derived property (`pc.cluster`), not a column |
| **Village** | village_code, name, mandal, district, **da_id** (FK) | Cluster is a derived property (`da.cluster`) |
| **Committee** | committee_code, **village_id** (FK), name | Name is one of the 10 normalized committee types |
| **CommitteeMember** | member_code, **committee_id** (FK), name, gender, designation, designation_raw, mobile | 2,433 rows from the source data |
| **ActionPlan** | plan_code, village_id, committee_id, da_id, **type** (Attendance/Specials), **frequency** (Recurring-Monthly/One-off — genuinely mixed per committee, not a global rule), assigned_date, notes | One row per village-committee pre-populated (351 total); Type/Frequency/Assigned_Date left for the client to fill in |
| **AttendanceEntry** | entry_code, plan_id, da_id, entry_date, status, reason, image_url, male_count_live, female_count_live, new_members_count, visit_designations, gps_lat, gps_long | Male/Female "Total from Master" are computed live via lookup, never duplicated |
| **SpecialsEntry** | entry_code, plan_id, da_id, special, entry_date, status, reason, image_url, participants_count, scope (Under GP/Under VDC), gps_lat, gps_long | `special` currently = the Committee name (no separate specials catalog yet — deferred, see §10) |
| **User** (auth) | email, mobile, password_hash, role, pm_id/pc_id/da_id (exactly one set, or none for Admin) | Deliberately separate from the profile tables — one place to authenticate regardless of role |
| **AuditLog** | user_id, table_name, record_id, action (create/edit/move/enable/disable/delete/restore), field_name, old_value, new_value, timestamp | Every Admin mutation gets a row here |

Every master-data entity (PM/PC/DA/Village/Committee/CommitteeMember/ActionPlan) plus the two Entry tables carries:

- **`is_enabled`** (bool) — the Enable/Disable toggle
- **`is_deleted`** + **`deleted_at`** — the "Bin": soft-deleted, restorable, meant to be hard-purged by a scheduled job after **10 days**

---

## 5. Application Requirements

### 5.1 Attendance module (DA-facing)

1. Login with Email/Mobile + password
2. Select assigned Village (dropdown, scoped to that DA only)
3. Based on Village, select Committee (dropdown — this is "their assigned action plan")
4. Upload image → **converted to WebP** regardless of source format
5. Show **Male: live count / total from master data** (e.g. "4 / 12") and same for Female
6. Auto-computed **Total = Male + Female** (never manually entered)
7. **New Members Count** field
8. **Visit Designations** — multi-select tick list (President / Vice President / Secretary / Member), options driven by master data
9. **Reason** card — shown **only** if the submission is Early or Postponed; hidden if on-time
10. **Live GPS location** — permission requested, captured with the entry

**Status logic:** submitted before the Action Plan's assigned date → **Early**; on the date → **On-time**; after the date → **Postponed**; nothing submitted once the date has passed → **Failure**.

### 5.2 Specials module (DA-facing)

Same login/Village/Committee selection flow, then:

1. **Specials** dropdown — scoped to the selected committee (currently just shows the Committee name; a real catalog of specific activity types is a future addition, structurally a one-table add-on, nothing else changes)
2. Upload image → WebP
3. **Number of participants**
4. **Scope**: Under GP or Under VDC (single select, required — not both)
5. Live GPS location

### 5.3 Admin capabilities (the current build focus)

Full CRUD across every entity: **Add, Edit, Move** (reassign a foreign key — e.g. a DA to a different PC — logged distinctly from a plain Edit), **Enable/Disable** (reversible, hides from active pickers), **Delete** (→ the Bin, restorable), **Restore**, plus user/login management (create a login for a PM/PC/DA, reset password, enable/disable/delete a login). All of it Admin-only, all of it audit-logged.

### 5.4 Cross-cutting

- Everything needs a **dashboard** per role.
- **Export** option (mentioned early, not yet built).
- **Import** option for Action Plans — decided shape: same structure as the master workbook, plus Assigned_Date/Type/Frequency columns.

---

## 6. Technical Architecture

### 6.1 Stack decisions (with reasoning, as discussed)

| Layer | Decision | Why |
|---|---|---|
| Backend | **Flask + MySQL** (SQLite fallback for local dev) | Matches the client's existing stack across prior Bala Vikasa projects (CSRB Feedback, IT Helpdesk, WPPMS) |
| DA frontend | **Mobile-first PWA**, vanilla JS | Matches the client's established pattern; Dash isn't built for form-heavy mobile entry with camera/GPS |
| PC/PM/Admin frontend | **One shared Plotly Dash app**, role-gated, mounted on the Flask app | Python-only, no separate JS build; Dash's callback model is a direct match for the drill-down/cross-filter dashboards the client already built once before (WPPMS, Power BI-style) |
| Rejected: Bokeh + Panel | Dropped | Solves the same problem as Dash for zero added benefit here — the one legitimate reason to reach for it (Bokeh's streaming-plot performance for live DA GPS tracking) hasn't come up as a real requirement |
| Three.js | **Scoped to exactly one hero visual** on the Admin dashboard (e.g. an interactive 3D map of the program districts/villages, colored by status) | It's a component, not an architectural tier — everywhere else Dash's own charts are faster to build and better suited |

### 6.2 Admin permission model, implemented

- **Enable/Disable** = `is_enabled` toggle. Reversible. Hides the record from every non-Admin role's queries (Admin still sees disabled records, since someone has to be able to re-enable them).
- **Delete** = `is_deleted=True` + `deleted_at` stamped. This is the "Bin" — still queryable/restorable.
- **Restore** = clears `is_deleted`/`deleted_at`.
- **Auto-purge** = a `purge_expired()` classmethod, meant to run as a daily scheduled job (cron/Celery beat), hard-deletes anything in the Bin past the 10-day retention window.
- **Move** = editing a foreign key column (e.g. `DA.pc_id`) — no separate mechanism, just an Edit that happens to target a relationship field; logged to `AuditLog` with action=`move` instead of `edit` when it's specifically an FK field.
- **Add/Edit** = normal insert/update, always audit-logged.

### 6.3 Visibility scoping (query-layer enforcement)

A single module (`app/scoping.py`) is the only place "who sees what" is decided:

- DA → own records only, enabled only
- PC → own DAs' records only, enabled only
- PM → everything, enabled only, read-only
- Admin → everything, including disabled, excluding the Bin

---

## 7. Build Status

### 7.1 Completed and tested end-to-end

- Master data workbook (`MV-Master-Data-26-27.xlsx`) — 10 sheets, all totals formula-driven, zero hardcoded numbers, zero formula errors.
- Full Flask schema (11 tables) via SQLAlchemy, with Alembic migrations.
- Seed pipeline: imports the master workbook straight into the database (`app/seed/import_master_data.py`) — confirmed importing all 2,433 members / 351 committees / 42 villages / 9 DAs / 2 PCs / 2 PMs with zero errors.
- Auth: login by email-or-mobile + password (Flask-Login), role-based route gating.
- Visibility scoping: confirmed a PC only ever sees their own DAs; PM/Admin see everyone; cross-role access to another role's routes returns 403.
- A temporary plain-HTML (Jinja) frontend: login page + one dashboard per role, showing real, correctly-scoped data — explicitly a stand-in for local testing, not the final DA-PWA/PC-PM-Admin-Dash architecture.
- 14 local test logins (1 Admin, 2 PM, 2 PC, 9 DA), all generated by a repeatable script.

### 7.2 In progress (as of this document)

- **Admin full CRUD + user management** — a generic, registry-driven system (one config per entity, not 8 hand-built CRUD screens) covering Add/Edit/Move/Enable/Disable/Delete/Restore for every entity, plus login/password management, with every mutation audit-logged and CSRF-protected.

### 7.3 Not started

- DA-facing Attendance/Specials entry forms (the actual field app)
- Image upload + WebP conversion pipeline
- GPS capture endpoint
- PC/PM/Admin Dash dashboards (charts, drill-down)
- Three.js hero visual
- Action Plan bulk import route
- Export functionality
- Specials catalog (currently just = Committee name)
- Production deployment (MySQL, hosting, HTTPS, backups, rate limiting)

---

## 8. Known Issues Found and Fixed During Build

1. **Silent login failure.** `SoftDeleteMixin`'s enable/disable column was named `is_active`, which collided with Flask-Login's own reserved `UserMixin.is_active` property on the `User` model — the column never actually got mapped, so every login failed with a generic "invalid credentials" even with the correct password. Fixed by renaming the column to `is_enabled` everywhere and giving `User` its own explicit `is_active` property (`is_enabled and not is_deleted`) satisfying Flask-Login's real interface.
2. **Enable/Disable did nothing.** `scoping.py` filtered every query by `is_deleted` but never checked `is_enabled` — a disabled DA or PC would still show up in every dashboard. Fixed: non-Admin roles now filter on both flags.
3. **Local setup failure.** `.env.example` shipped with `DATABASE_URL=` (nothing after the `=`). Because `python-dotenv` auto-loads `.env` for the Flask CLI, this set the environment variable to an *empty string* rather than leaving it unset — and `os.environ.get(key, default)` only falls back to `default` when the key is *missing*, not when it's present-but-empty. Fixed by switching to `os.environ.get(key) or default`.
4. **Source data integrity issue** (not a code bug, a finding): the original Excel file's own per-committee subtotal rows didn't match the actual listed members. All downstream totals are computed from the real member list, never from those subtotal cells.

---

## 9. Deliverables Produced So Far

1. **`MV-Master-Data-26-27.xlsx`** — the normalized master data workbook
2. **`model_village_flask.zip`** — the Flask backend + temporary frontend, runnable locally (SQLite) or pointed at MySQL
3. **`test_credentials.txt`** — 14 local test logins (regeneratable via `app/seed/create_test_logins.py`)

---

## 10. Open Decisions / Still Needed From the Client

- Real names for the 2 PM placeholders (currently `S.Prasad`, `A.Lakshmi` — invented, flagged, need replacing)
- Real emails/mobiles for every PM/PC/DA (currently blank in the master data — no real logins can be issued until these are filled in)
- Confirmation: is it permanently 1 PC per Cluster, or will CSRB/PDTC eventually split across multiple PCs? (Schema already supports either.)
- The real Specials catalog, whenever the client is ready to move past "Specials = Committee name"
- MySQL hosting details for production deployment

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **DA** | Development Agent/Associate — field staff who visit villages and submit entries |
| **PC** | Project Coordinator — manages a set of DAs within one Cluster |
| **PM** | Programme/Project Manager — oversees all PCs and DAs, no Cluster restriction |
| **Cluster** | CSRB or PDTC — the top-level program division; owned by PC, inherited downward |
| **VDC** | Village Development Committee — one of the 10 standard committee types |
| **GP** | Gram Panchayat — one of the two "Scope" options for a Specials entry |
| **Action Plan** | A specific Village+Committee+Type(Attendance/Specials) assignment a DA is expected to fulfill by a given date |
| **Bin** | The soft-delete holding area — deleted-but-restorable records, auto-purged after 10 days |
| **CSRB / PDTC** | The two Clusters the 42-village program is split across |
