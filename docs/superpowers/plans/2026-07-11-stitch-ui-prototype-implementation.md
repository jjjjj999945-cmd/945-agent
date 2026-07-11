# Stitch UI Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React frontend in `D:\Codex\945` that closely recreates the provided Stitch screens for the 945 fitness and diet agent workspace.

**Architecture:** Use a self-contained Vite React app. Convert each Stitch screen into a route-backed React page using shared tokens for the Refined Glacier Light visual system, reusable shell/navigation, and screen-specific modules where layouts differ.

**Tech Stack:** Vite, React, TypeScript, CSS modules/global CSS, static mock data, local image/html references from the Stitch export.

## Global Constraints

- The Stitch screenshots and `screen.html` files are the visual source of truth.
- The PRD is the product and interaction source of truth.
- Do not iframe Stitch HTML as the app implementation.
- Preserve page-specific module differences instead of forcing one generic template.
- Provide `zh-CN` and `en-US` i18n structure; Chinese can be primary.
- Implement realistic local demo interactions only; no backend, login, payments, medical claims, image recognition, wearables, or community features.
- Verify with a running dev server and browser screenshots.

---

### Task 1: Scaffold App And Reference Assets

**Files:**
- Create: `package.json`, `index.html`, `src/`, `public/stitch-reference/`
- Modify: none

**Deliverable:** Vite React app builds and can access Stitch reference screenshots locally.

### Task 2: Shared Visual System

**Files:**
- Create: `src/styles.css`, `src/data/i18n.ts`, `src/data/mockData.ts`, `src/components/AppShell.tsx`, `src/components/ui.tsx`

**Deliverable:** Glacier light tokens, navigation, buttons, cards, progress bars, chart primitives, and form controls match Stitch proportions and palette.

### Task 3: Screen Routes

**Files:**
- Create: `src/pages/*.tsx`, `src/App.tsx`, `src/main.tsx`

**Deliverable:** All 11 Stitch screens have corresponding routes and visible page-specific module structure.

### Task 4: Interactions

**Files:**
- Modify: `src/pages/*.tsx`, `src/App.tsx`

**Deliverable:** Navigation, tabs, toggles, checkboxes, meal/workout confirmation, onboarding fields, language switch, and chat input have visible feedback using demo state.

### Task 5: Verification And Visual QA

**Files:**
- Create: `design-qa.md`

**Deliverable:** Dev server runs, app builds, screenshots are captured against Stitch references, and P0/P1/P2 visual/runtime issues found during QA are fixed.
