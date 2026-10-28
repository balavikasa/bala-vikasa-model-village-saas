# Reference-led UI Rebuild Implementation Plan

> Execute inline with test-first gates and a separate final self-review.

**Goal:** Rebuild six referenced page compositions with real controls and existing application data.
**Architecture:** One shared reference design system; replace markup for the six main screens; retain role scoping, attendance API and offline queue. Separate local fixtures from production.
**Tech Stack:** Flask/Jinja, CSS, vanilla JavaScript, SVG charts, Playwright visual checks.
**Spec:** The six attached reference images plus the DA-led workflow approved in this conversation.

## Global Constraints
- DA home/login opens Attendance. Automatic entry date, one visit, shared photo/GPS and new-members total remain.
- No production data changes, fake KPIs, extra role privileges, or invented account avatars.
- Use the reference BV mark and decorative village illustrations, not the red supplied logo.
- No font files distributed. Use CSS web fonts with system fallbacks.
- Test 390px mobile and 1448px desktop, plus 320/768/1280px overflow checks.

## Review Focus
1. Long names/tables cannot extend the whole viewport.
2. Disabled/deleted data and role filters stay enforced by backend.
3. Missing photo/location/chart data must have honest empty states.
4. Real actions retain CSRF and event bindings.
5. Reference schedule/late/planned values are historical mockup content, not new workflow rules.

## Tasks
1. Shell/assets: test reference stylesheet and desktop/mobile geometry; implement isolated layout, artwork, SVG icons and navigation.
2. Six templates: test data hooks and read-only date; rebuild Admin, Dashboard, Analytics, Profile, Report and Entry.
3. Data interactions: browser-test filters, member selection, totals, accordions, dialogs, charts and export; connect existing APIs.
4. Render every page; inspect screenshots; correct overflow and broken controls. Compile/check all JS and Python; attempt full suite and record environment failures.
5. Package source, patch and browser previews. Verify patch application, archive integrity and exact modified-file manifest.
