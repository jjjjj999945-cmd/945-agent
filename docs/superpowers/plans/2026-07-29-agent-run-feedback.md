# Agent Run Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the latest Agent run result and allow explicit retry from the existing Agent page.

**Architecture:** Extend the HTTP adapter with safe Agent-run read and retry methods. The existing Agent status card consumes this data after chat submission and displays concise user-facing status; failures expose an explicit retry action only.

**Tech Stack:** React 19, TypeScript, Vite, FastAPI Agent APIs, Playwright.

## Global Constraints

- Keep the existing 945 visual system unchanged: colors, fonts, icons, navigation, glass effect, and component styles.
- Do not surface token or aggregate operational metrics to end users.
- Retry must remain explicit and must not confirm or write a RecordDraft.

---

### Task 1: Add Agent run HTTP adapter contracts

**Files:**
- Modify: `src/types/domain.ts`
- Modify: `src/services/httpApi.ts`
- Test: `tests/http-integration.spec.ts`

- [x] Add `AgentRun` matching `GET /api/agent/runs` without retry input.
- [x] Add `getAgentRuns` and `retryAgentRun` methods to `httpApi`.
- [x] Add a failing HTTP test that exercises an Agent failure and explicit retry.
- [x] Implement the minimum adapter methods and verify the test passes.

### Task 2: Render latest Agent run feedback

**Files:**
- Modify: `src/pages/AgentPage.tsx`
- Test: `tests/http-integration.spec.ts`

- [x] Load the most recent run when the Agent page opens and after message submission.
- [x] Reuse the existing Agent status card to show processing, completed, or failed state.
- [x] Render an explicit retry button only for a failed run and refresh messages, today context, and run state after retry.
- [x] Verify the retry test and TypeScript build pass.

### Task 3: Verify and commit

**Files:**
- Modify: `docs/superpowers/plans/2026-07-29-agent-run-feedback.md`

- [x] Run the focused Playwright HTTP test.
- [x] Run `npm run build` and `git diff --check`.
- [ ] Commit only files owned by this feature. Deferred because this worktree contains unrelated uncommitted changes.
