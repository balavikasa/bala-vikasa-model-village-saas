# DA-led village attendance — October 28, 2026

## Active operating model

- PC-created Action Plans are no longer prerequisites to DA attendance.
- DA chooses a date implicitly by performing a visit. The server stamps the visit with its current India-local date; the date is displayed read-only and never accepted from user input. Offline entries are dated when synchronization reaches the server, **not** when they were queued.
- DA sees assigned villages first. `Other village` permits explicit cross-assignment selection from active master villages. Submission records the actual DA and `outside_assignment`; no village ownership is changed.
- One visit per village per calendar month while active. This rule covers all committees. Admin soft deletion permits resubmission; a duplicate or concurrent submission is rejected. Existing earlier attendance history is preserved.
- Each committee still retains selected member-name details, automatic male/female/total counts, one shared photo and GPS, and one village-wide new-members count on the parent visit. Committee child rows store zero new members to prevent double-counting.
- Dashboard and Monitoring show villages done / not done, people attended, and new members based on real recorded visits, not planning deadlines. Legacy Action Plans are available only for historical workflows.

## Database migration

Backup PostgreSQL and uploads, then apply `python -m flask --app wsgi db upgrade` to revision `20261028_0004`. It makes `attendance_entries.action_plan_id` nullable, adds village-level counts, cross-assignment flag, visit month, and an active-month unique index. The downgrade intentionally refuses to delete DA-led records.

## Known constraints

- One village visit per month, including visits from DAs outside that village's primary assignment.
- DAs can view their own cross-assignment attendance reports. PC/Admin visibility remains based on master village ownership.
- Legacy action-plan reports remain readable, but should no longer be interpreted as DA completion KPIs.
- Live PostgreSQL migration, offline sync, and production auth require staging tests before deployment.
