# Bala Vikasa UI Refresh — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the approved bright civic-tech design foundation and DA Mobile Field App shell without changing routes, permissions, APIs, offline behavior, or field-submission semantics.

**Architecture:** Preserve the existing Flask/Jinja structure. Add new `--mv-*` CSS tokens and motion primitives incrementally in `app/static/css/app.css`. Update only the DA branch of `app/templates/base.html` to use a compact top bar and floating `Entry / Plans / Reports / More` bottom navigation. Keep Admin/PM/PC navigation functionally unchanged.

**Tech Stack:** Flask, Jinja2, vanilla JS, CSS, pytest, Ruff, PWA/service worker

**Spec:** `docs/superpowers/specs/2026-08-31-bala-vikasa-ui-ux-redesign-design.md`

## Global constraints

- Primary `#0C7C86`; secondary `#13A0A8`
- Page `#F4FAFA`; surface `#FFFFFF`
- Text `#163036`; muted `#6B7F83`
- Success `#3A9B70`; warning `#F0A53A`; danger `#D95E4F`
- Minimum touch target 44px
- Motion 180–220ms and respect `prefers-reduced-motion`
- Do not replace `app.css` wholesale
- Preserve authorization, CSRF, offline queue, service worker, PWA, idempotency, audit and import/export behavior

---

## Safety precondition

The current branch still has the DA work-hub implementation uncommitted. Commit it before starting the redesign so rollback remains clean.

```powershell
python -m ruff check app tests scripts --output-format concise
python -m pytest -q
git diff --check
git status --short

git add `
  app/pages.py `
  app/planning.py `
  app/services/monthly_plans.py `
  app/static/css/app.css `
  app/static/js/action-plans.js `
  app/static/js/field.js `
  app/templates/action_plans.html `
  tests/test_da_work_hub.py `
  tests/test_da_work_queue.py

git diff --cached --check
git commit -m "Add DA action plan work hub"
git status
```

Expected: clean working tree after the commit.

---

### Task 1 — Design-token and DA-shell contract tests

**Modify:** `tests/test_mobile_ui_contract.py`, `tests/test_da_work_hub.py`

Add a failing test asserting these CSS tokens exist:

```python
expected_tokens = {
    "--mv-primary: #0C7C86",
    "--mv-primary-2: #13A0A8",
    "--mv-page: #F4FAFA",
    "--mv-surface: #FFFFFF",
    "--mv-text: #163036",
    "--mv-muted: #6B7F83",
    "--mv-success: #3A9B70",
    "--mv-warning: #F0A53A",
    "--mv-danger: #D95E4F",
}
```

Also assert `.mv-enter`, `.mv-primary-action`, and `@media (prefers-reduced-motion: reduce)`.

Add a DA shell test asserting `base.html` contains:
- `class="da-field-appbar"`
- `class="da-field-bottom-nav"`
- `data-da-entry-menu`
- `data-da-more-menu`
- labels `Entry`, `Plans`, `Reports`, `More`

Run the focused tests and confirm RED, then commit tests.

---

### Task 2 — Shared visual foundation

**Modify:** `app/static/css/app.css`

Add to the existing `:root` block:

```css
--mv-primary: #0C7C86;
--mv-primary-2: #13A0A8;
--mv-page: #F4FAFA;
--mv-surface: #FFFFFF;
--mv-text: #163036;
--mv-muted: #6B7F83;
--mv-success: #3A9B70;
--mv-warning: #F0A53A;
--mv-danger: #D95E4F;
--mv-radius-control: 14px;
--mv-radius-surface: 18px;
--mv-shadow-soft: 0 12px 32px rgba(18,64,70,.08);
--mv-shadow-float: 0 18px 48px rgba(18,64,70,.16);
--mv-motion-fast: 180ms;
--mv-motion-base: 210ms;
```

Add `.mv-enter`, `.mv-primary-action`, `@keyframes mv-enter`, and reduced-motion overrides. Switch only page-level authenticated background/text aliases to `var(--mv-page)` and `var(--mv-text)`; do not mass-replace legacy colors.

Run UI/shell tests, then commit:

```powershell
git commit -am "style: add modern Bala Vikasa design tokens"
```

---

### Task 3 — DA mobile field shell

**Modify:** `app/templates/base.html`

For DA only, render:
- compact brand bar with BV + Model Village
- existing sync queue button/hook
- menu button/hook
- floating four-item bottom nav:
  - Entry (button)
  - Plans (link)
  - Reports (link)
  - More (button)

Reuse existing routes and hooks. Keep PC/PM/Admin shell unchanged.

Run:
```powershell
python -m pytest tests/test_da_work_hub.py tests/test_mobile_ui_contract.py tests/test_routes_and_headers.py tests/test_pwa_contract.py -q
```

Commit:
```powershell
git add app/templates/base.html tests/test_da_work_hub.py
git commit -m "feat: add DA mobile field navigation shell"
```

---

### Task 4 — DA shell styling

**Modify:** `app/static/css/app.css`

Add mobile styles for:
- `.da-field-appbar`
- `.da-field-brand`
- `.da-sync-button`
- `.da-field-menu-button`
- `.da-field-bottom-nav`
- `.da-field-bottom-nav .is-active`

Requirements:
- floating white/blurred bottom nav
- safe-area aware
- 44px minimum targets
- teal active state
- DA `app-main` gets bottom padding for floating nav
- existing `.mobile-appbar` / `.bottom-nav` hidden only for DA at phone widths

Run mobile/PWA tests and commit.

---

### Task 5 — One-time GO attention effect

**Modify:** `app/static/js/action-plans.js`, `app/static/css/app.css`, `tests/test_da_work_hub.py`

Add a contract for:
- `is-attention-pulse`
- `animationend`
- `@keyframes mv-attention-pulse`

After Today/Pending cards render, select the first `.da-work-go`. If reduced motion is not requested, add `is-attention-pulse` once and remove it on `animationend`.

CSS pulse:

```css
.is-attention-pulse {
  animation: mv-attention-pulse 620ms ease-out 1;
}

@keyframes mv-attention-pulse {
  0% { box-shadow: 0 0 0 0 rgba(12,124,134,.30); }
  55% { box-shadow: 0 0 0 9px rgba(12,124,134,0); }
  100% { box-shadow: 0 0 0 0 rgba(12,124,134,0); }
}

@media (prefers-reduced-motion: reduce) {
  .is-attention-pulse { animation: none; }
}
```

Run DA hub tests and commit.

---

### Task 6 — Phase-1 verification

Run:

```powershell
python -m ruff check app tests scripts --output-format concise
python -m pytest tests/test_da_work_hub.py tests/test_da_work_queue.py tests/test_mobile_ui_contract.py tests/test_routes_and_headers.py tests/test_pwa_contract.py tests/test_shared_shell_encoding.py -q
python -m pytest -q
git diff --check
git status --short
```

Manual browser checks:
- DA at 390×844, 768×1024, 1440×900
- top bar compact and bright
- bottom nav exactly Entry / Plans / Reports / More
- no horizontal overflow
- GO still opens prefilled Attendance/Specials
- sync and More hooks still work
- one-time pulse runs once
- reduced-motion suppresses it
- one PC/Admin login still has functional management navigation

## Exit criteria

Phase 1 is complete when:
- DA work hub is committed separately
- new tokens exist without deleting legacy tokens
- DA mobile nav is task-first
- management nav remains intact
- GO pulse is subtle and one-time
- Ruff and full pytest pass
- no whitespace errors
- phone/tablet/desktop manual checks pass

## Follow-on plans

1. Phase 2 — DA Action Plans visual redesign
2. Phase 3 — DA Attendance / Specials
3. Phase 4 — DA Reports / My Villages / More
4. Phase 5 — Admin / PM / PC shell and Overview
5. Phase 6 — Planning workspace and Reports
6. Phase 7 — Monitoring / Analytics
7. Phase 8 — Directory / Master Data / Transfers
8. Phase 9 — final accessibility/responsive/visual regression audit
