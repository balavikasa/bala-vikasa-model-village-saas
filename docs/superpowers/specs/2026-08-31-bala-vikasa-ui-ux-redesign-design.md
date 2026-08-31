# Bala Vikasa Model Village — UI/UX Redesign Design Spec

Date: 2026-08-31
Status: Approved design direction, pending repository commit
Primary direction: Concept 1 — Mobile Field App for DA
Companion direction: same visual language with denser desktop workspaces for Admin / PM / PC

## Goals

Redesign the application so it feels modern, calm, bright, polished, and purposeful while preserving existing Flask routes, permissions, APIs, offline queue, submission behavior, and role-scoped data rules.

The redesign must:
- make DA work task-first and mobile-first;
- keep Admin / PM / PC efficient on desktop;
- improve visual hierarchy, navigation clarity, spacing, readability, and touch ergonomics;
- avoid the muted beige / “old government portal” appearance;
- preserve functional stability through staged rollout and regression testing;
- use restrained motion to create interest without distracting field users.

## Role UX Model

### DA

Primary job: execute assigned field work.

Default landing page:
- `/action-plans`

Primary navigation:
- Entry
- Plans
- Reports
- More

Entry contains Attendance and Specials.
More contains My Villages, Map, Sync/offline queue, Install app, Profile/account, and Logout.

DA pages should avoid admin-style tables and dense management controls.

### PC

Primary jobs:
- assign monthly work;
- monitor DA workload;
- resolve overdue work;
- inspect reports and field evidence.

### PM

Primary jobs:
- monitor program delivery;
- compare areas/clusters;
- inspect reports and analytics.

### Admin

Primary jobs:
- program-wide oversight;
- master data;
- imports/exports;
- recovery;
- monitoring;
- reports;
- analytics;
- system operations.

## Visual Direction

Use a bright, calm civic-tech visual language.

Base palette:
- Primary teal: `#0C7C86`
- Secondary teal: `#13A0A8`
- Page background: `#F4FAFA`
- Surface: `#FFFFFF`
- Primary text: `#163036`
- Secondary text: `#6B7F83`
- Success: `#3A9B70`
- Attention/due: `#F0A53A`
- Danger/overdue/error: `#D95E4F`

Rules:
- teal is for brand and primary actions;
- green is reserved for success;
- amber is for due-soon / attention;
- red is only for overdue / error;
- avoid excessive grey-on-grey;
- use whitespace instead of borders wherever possible.

## Typography

Use Inter for operational UI. Display serif may remain only for major page titles if desired, but not routine controls, tabs, forms, metrics, or navigation.

Prioritize outdoor readability, strong contrast, compact labels, and readable secondary metadata.

## Shared Design Tokens

- Minimum touch target: 44px
- Control radius: 12–16px
- Surface radius: 16–20px
- Spacing: 4 / 8 / 12 / 16 / 20 / 24 / 32px scale
- Shadows: soft, low contrast
- Borders: only when needed
- Focus states: clearly visible

## Motion System

Allowed:
- content rise/fade on initial render;
- 180–220ms transitions;
- sliding active tab indicator;
- active nav movement;
- counters animate once;
- one gentle attention pulse on the main GO button;
- brief success check after submission.

Not allowed:
- continuous glow;
- endless bouncing;
- persistent shimmer;
- distracting looping animation.

Respect `prefers-reduced-motion`.

## DA Navigation

### Mobile

Floating bottom nav with:
- Entry
- Plans
- Reports
- More

Top bar:
- BV brand / Model Village on left;
- sync/online state and menu on right.

### Desktop

No heavy admin sidebar. Use a centered narrow task workspace with compact top/dock navigation.

## DA Action Plans

This is the DA home/work queue.

Top context:
- date;
- number of tasks needing attention;
- overdue count when present.

Primary tabs:
- Today
- Pending

Behavior:
- tap and horizontal swipe;
- obvious active state;
- if Today is empty and Pending exists, Pending may open automatically.

Today:
- due today;
- show GO.

Pending:
- overdue, incomplete assignments including prior months;
- show GO;
- show overdue age.

Upcoming:
- quieter preview below;
- no GO until actionable.

Task card:
- village;
- committee;
- type;
- due/overdue state;
- optional note;
- strong GO action.

## DA Attendance / Specials

Deep links:
- `/field/attendance?plan=<id>`
- `/field/specials?plan=<id>`

Auto-fill:
- Village
- Committee
- Action Plan

Show assignment context near the top.

Attendance:
- live male/female/total summary;
- touch-friendly member selection;
- clear GPS/photo state.

Specials:
- same interaction language;
- only task-specific fields differ.

Submission:
- one obvious primary action;
- inline validation;
- clear success feedback.

## DA Reports

Use a mobile timeline/list, not a management table.

Each row:
- village + committee;
- Attendance/Specials;
- date;
- evidence state;
- status.

Top metrics:
- completed this month;
- on-time rate;
- pending evidence or similar useful metric.

## DA My Villages / Map / More

My Villages:
- searchable vertical list;
- compact village summaries;
- drill into committees and recent work.

Map:
- secondary destination under More.

More:
- My Villages
- Map
- Sync
- Install app
- Account/profile
- Logout

## Admin / PM / PC Navigation

Use the same visual identity with a denser smart side rail on desktop.

Rail:
- compact icon + label;
- quiet inactive state;
- soft teal active pill;
- account/sync at bottom.

Tablet/mobile:
- compact top bar and role-specific bottom navigation.

## Admin / PM / PC Overview

Replace large hero-heavy composition with:
1. compact greeting/period strip;
2. 4–5 useful KPIs;
3. Needs Attention;
4. Recent Activity / Delivery Pulse.

Role emphasis:
- PC: cluster / DA workload and overdue work;
- PM: program monitoring;
- Admin: program-wide summary.

Reuse existing data sources and permissions.

## Admin / PC Action Plans

Desktop structure:
- compact month command bar;
- horizontal KPI strip;
- grouped search/status/import/export/next-month actions;
- monthly ledger.

Editing:
- right-side drawer on desktop;
- bottom sheet on mobile.

Do not change role permissions.

## Reports Workspace

Desktop:
- sticky filter bar;
- month;
- report type;
- status;
- search;
- export where permitted.

Use smaller KPI chips.
Rows prioritize village/committee, then type/date/evidence/status, with one obvious View action.

Mobile:
- compact report rows/cards.

## Monitoring

Make the map the visual center.

Desktop:
- compact KPI strip;
- large evidence/risk map;
- narrow risk/attention panel alongside.

Mobile:
- map first;
- risk list below.

Use warning colors sparingly.

## Analytics

Use:
- unified filters;
- larger chart canvas;
- fewer decorative panels;
- consistent chart surfaces;
- clear responsive behavior.

## Directory / Team / Master Data

Directory/Team:
- searchable workspace;
- compact rows;
- strong drill-down.

Master Data:
- sticky toolbar;
- clear tabs;
- compact tables;
- side-panel editing;
- explicit destructive states;
- strong success/error feedback.

## Responsive Strategy

Phone:
- DA single-column task flow;
- floating bottom nav;
- compact top bar;
- no desktop sidebar;
- management data converted to rows/cards where appropriate.

Tablet:
- compact navigation;
- selective two-column layouts.

Desktop:
- dense role-appropriate workspace;
- smart rail for Admin / PM / PC;
- centered task workspace for DA.

Do not merely shrink desktop layouts.

## Accessibility

Required:
- 44px minimum touch target;
- visible keyboard focus;
- semantic tabs/navigation;
- sufficient contrast;
- labels not replaced by color;
- clear status text;
- reduced motion support;
- meaningful empty/loading/success/error states.

## Technical Constraints

Preserve:
- Flask routes;
- existing role checks;
- authorization boundaries;
- CSRF behavior;
- offline queue;
- service worker;
- PWA install flow;
- field submission semantics;
- idempotency;
- current APIs unless an additive endpoint is explicitly required;
- audit behavior;
- import/export workflows.

Avoid broad functional rewrites during visual rollout.

## CSS / Component Strategy

Do not replace `app/static/css/app.css` wholesale.

Introduce incrementally:
1. new design tokens;
2. shared primitives;
3. navigation layer;
4. page-level components;
5. responsive variants.

Retire legacy rules only after each related screen is verified.

Reusable component families:
- app bar;
- floating bottom nav;
- smart side rail;
- segmented tabs;
- task card;
- status badge;
- KPI chip;
- filter bar;
- report row;
- empty state;
- field context strip;
- drawer/bottom sheet;
- toast/inline feedback.

## Rollout Plan

1. shared tokens, typography, buttons, forms, motion primitives;
2. DA shell and navigation;
3. DA Action Plans;
4. Attendance / Specials;
5. DA Reports / My Villages / More;
6. Admin / PM / PC shell and Overview;
7. planning workspace and Reports;
8. Monitoring / Analytics;
9. Directory / Master Data / transfers;
10. responsive, accessibility, and visual regression audit.

Each stage must pass regression tests before proceeding.

## Testing Strategy

At minimum:
- Ruff clean;
- full pytest suite green;
- route/permission contract tests green;
- DA work hub tests green;
- deep-link auto-fill tests green;
- mobile UI contract tests updated where intentional;
- no session stability regression;
- no PWA/service-worker regression;
- manual browser verification at phone, tablet, and desktop widths.

Critical journeys:
- DA login → Action Plans;
- Today GO → Attendance auto-fill;
- Pending GO → Attendance/Specials auto-fill;
- submit field entry;
- report visible;
- PC assigns work;
- Admin/PM/PC browse reports;
- monitoring loads;
- offline queue still functions.

## Rollback

Each visual phase must be independently reversible.

Do not combine broad UI changes with database migrations or unrelated functional refactors.

If a stage fails:
- revert only that stage;
- keep prior stabilized stages;
- preserve data and APIs.

## Acceptance Criteria

Complete when:
- DA mobile flow is task-first and requires minimal navigation;
- Today/Pending/Upcoming are immediately understandable;
- GO leads to the correct prefilled field form;
- mobile navigation is compact and one-hand friendly;
- Admin/PM/PC retain efficient dense desktop workflows;
- all major pages share one visual language;
- dull beige legacy portal appearance is removed;
- phone/tablet/desktop layouts are intentional;
- motion is subtle and accessible;
- regression suite remains green;
- no role-permission or offline behavior regression is introduced.
