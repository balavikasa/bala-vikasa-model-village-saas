# Reference rebuild - implementation ledger and self-review

Plan: docs/superpowers/plans/2026-10-28-reference-rebuild.md

Completed in an isolated local branch; no shared-branch push, live deployment or production DB operation.

## Task evidence

1. Shared layout/assets: reference-style contracts and geometry were written and observed failing before replacement; geometry passes for six compositions after correction.
2. Six page templates: reference compositions and original attendance data hooks retained; browser renders inspected.
3. Interactions: 15 isolated browser checks pass, including filtering, export, error states, selection, payload and dialogs.
4. Responsive QA: 30 viewport/navigation cases pass; six desktop layout gates pass.
5. Runtime gate: full pytest was attempted and could not import Flask. Ruff unavailable. Those gates remain open and are not reported as passed.

## Decisions and their cost

- Preserve the confirmed DA-led workflow rather than reintroduce the mockups' schedules and On-time/Overdue metrics. Cost: text and data do not exactly duplicate the illustrative images.
- Use existing real roles/routes and initials rather than invent household/document modules and staff portraits. Cost: some navigation labels/avatar appearance differ from the concepts.
- Preserve attendance/date/queue APIs and use an isolated sample renderer for local browser tests because live browser navigation and dependency downloads are blocked. Cost: these tests do not certify the backend or real device/offline operation.
- Use reference-derived decorative PNG assets and external CSS font links, with system fallback. Cost: font rasterization and scale can differ; no numerical pixel-match claim is supported.

## Review findings addressed

- Stale chart/KPI values remained after failed filtering: failing browser test then cleared/error state and disabled export; browser checks pass.
- Low-count axes repeated rounded values: failing Node test then distinct integer ticks; four Node tests pass.
- Small phone controls: failing 44px browser test then corrected field-control height; interaction suite passes.
- A disabled parent visit or another submitter's evidence could appear on an Other-village map: new pure evidence-filter test fails before implementation and passes after; map now uses that filter.
- Outdated tests required the previous sidebar/chooser/logo and contradicted the approved replacement. Replaced those UI assertions with current navigation, CSRF, asset and layout contracts; business/permission checks retained.

## Remaining acceptance work

Independent review, full runtime pytest, Ruff, PostgreSQL migration/queries, actual login and account mutations, deployed fonts/maps, camera permissions, and offline queue synchronization require CI/staging. Do not merge as a verified production release solely on these local UI results.

## Deferred minor polish

No numeric similarity score is certified. Per-device typography and map imagery need deployed comparison. Fixed-header full-height screenshots use a resized viewport; normal viewport captures are included for clarity.
