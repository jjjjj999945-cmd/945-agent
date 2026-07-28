# Task 3 Report: Shared Active Plan Context

## Status

Completed.

## Implementation

- Added `appToday` as the frontend runtime-date source, honoring `VITE_945_REFERENCE_DATE`.
- Added `CurrentPlanData`, `PlanCoverageStatus`, and `PlanContextValue` to the frontend domain contract.
- Added `PlanProvider` and `usePlanContext()`. The provider fetches profile and current-plan state concurrently after a user ID is available, exposes a refresh function, and keeps the profile, current plan, coverage state, loading state, error, and runtime date together.
- Wrapped business pages in `PlanProvider`. The Today route now renders a stable renewal state for `expired` and `none` coverage, with the primary action navigating to `/onboarding`.
- Updated HTTP and mock API adapters so `getCurrentPlan()` returns `{ plan, coverage_status }`.
- Updated plan consumers and write paths to handle a nullable active plan. Workout logs, planned-meal confirmations, record-draft writes, workout/diet data assembly, and plan-page reads now use the API-returned plan or stop with `PLAN_UNAVAILABLE`; none falls back to `demoPlan.plan_id` for writes.
- Updated the existing HTTP integration assertions to use the Task 1 lifecycle wrapper.

## Test Evidence

1. RED: `npx playwright test tests/plan-lifecycle.spec.ts --config=playwright.plan-lifecycle.config.ts --project=http`
   - Before the shared context UI existed, the required renewal heading was absent.
2. Focused lifecycle test:
   - `npx playwright test tests/plan-lifecycle.spec.ts --config=playwright.plan-lifecycle.config.ts --project=http`
   - Result: `1 passed`.
3. Production build:
   - `npm run build`
   - Result: passed (`tsc` and Vite build completed).
4. Full HTTP regression:
   - `npm run qa:http`
   - Result: `16 passed`.
5. Final focused lifecycle verification:
   - `npx playwright test tests/plan-lifecycle.spec.ts --config=playwright.plan-lifecycle.config.ts --project=http`
   - Result: `1 passed`.

## Test Fixture Note

The preserved dirty backend seed work derives demo-plan dates from `945_REFERENCE_DATE`. A single backend reference date therefore makes the seeded plan active for that same date, rather than expired. The focused frontend lifecycle test uses the real HTTP profile request and a narrow Playwright route fixture only for `/api/plans/current`, returning the Task 1 expired contract `{ plan: null, coverage_status: "expired" }`. The dedicated lifecycle config supplies the `http` project name requested by the task; the existing HTTP config filters this new spec out.

## Dirty Worktree Handling

Pre-existing backend, deployment, UI, authentication, date-data, and broad HTTP-test changes were retained. Only Task 3 contract, context, lifecycle-test, current-plan caller, and required HTTP assertion changes are staged for the Task 3 commit.

## Fix Round 1

- Onboarding, plan acceptance, and settings-plan acceptance now refresh `PlanContext` before the application can rely on the active-plan state. The onboarding lifecycle waits for the refresh before routing to Today.
- Plan, Today, Workout, Diet, and record-draft writes now consume the shared active plan instead of independently loading a current plan.
- `appToday` is the only frontend runtime-date source. Demo data, HTTP/mock adapters, and page writes use it consistently.
- Mock workout and diet adapters now reject uncovered plans with `PLAN_UNAVAILABLE`, matching the HTTP adapter.
- The lifecycle fixture now keeps every initial current-plan request expired until the test explicitly starts onboarding. This accounts for React Strict Mode's duplicate provider mount and verifies the complete renewal, acceptance, refresh, and Today transition.

### Fix Round 1 Test Evidence

1. `npx playwright test tests/plan-lifecycle.spec.ts --config=playwright.plan-lifecycle.config.ts --project=http --reporter=line`
   - Result: 4 passed.
2. `npm run build`
   - Result: passed.
3. `npm run qa:http`
   - Result: passed, 16 tests.
