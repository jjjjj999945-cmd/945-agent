# 945 PRD-Driven Frontend Migration Design

## Context

The current frontend is a Vite + React wrapper around exported Stitch HTML. It preserves the high-fidelity prototype well, but it is not a maintainable product implementation because navigation and behavior are inferred from static HTML, button text, and Material icon names.

`PRD.md` and `docs/FRONTEND_REQUIREMENTS.md` define a broader product surface than the 11 exported Stitch screens. The migration needs to keep Stitch as the visual reference while moving the primary app to PRD-owned routes, state, data, and components.

## Goal

Build the first real frontend foundation for 945 without losing the Stitch visual direction.

This phase does not implement every PRD workflow end to end. It creates the correct application shell, route map, data contracts, mock data, and page skeletons so future work can replace Stitch HTML one page at a time.

## Scope

### In Scope

- Replace the main product entry with a real React App Shell.
- Define PRD-owned primary routes:
  - `/` for Today
  - `/onboarding`
  - `/plan`
  - `/workout`
  - `/diet`
  - `/body`
  - `/advice`
  - `/agent`
  - `/settings`
- Move the Stitch wrapper behind a prototype/reference route namespace:
  - `/prototype`
  - `/prototype/workout`
  - `/prototype/settings`
  - `/prototype/weekly-summary`
  - `/prototype/agent-v3`
  - `/prototype/diet`
  - `/prototype/workout-alt`
  - `/prototype/agent`
  - `/prototype/onboarding`
  - `/prototype/ai-adjustment`
  - `/prototype/diet-alt`
- Create typed demo data for the PRD's core domains:
  - demo user
  - today status
  - workout plan and workout log draft
  - meal plan and meal log draft
  - body metrics
  - daily check-in
  - advice and weekly summary
  - Agent messages
- Create a simple mock API service with async functions and local in-memory mutation.
- Create `zh-CN` and `en-US` i18n dictionaries, with Chinese as the default UI language.
- Add real page skeletons for all primary routes, each showing the PRD-required core modules at information-architecture level.
- Keep the existing Stitch exports, assets, and QA screenshots unchanged as visual references.

### Out of Scope

- Backend integration.
- Auth, account management, or cloud persistence.
- Full charting library integration.
- Food image recognition, barcode scan, external delivery platform integration, or automatic meal recognition.
- Full visual pixel conversion of every Stitch page into React components.
- Full Agent intelligence; Agent responses remain deterministic mock behavior.

## Architecture

### App Shell

`src/App.tsx` becomes a router shell instead of the Stitch renderer. It determines the current route from `window.location.pathname`, renders `AppShell`, and selects the matching page component.

The shell owns:

- desktop side navigation
- mobile bottom navigation
- top page header
- language switch
- prototype reference link
- current-route active states

Navigation is defined from a typed route config, not inferred from static HTML.

### Prototype Reference

The existing Stitch renderer is moved into focused files:

- `src/prototype/StitchPrototype.tsx`
- `src/prototype/screens.ts`
- `src/prototype/stitchDom.ts`

It remains available for visual comparison and QA through `/prototype/*`, but it no longer controls the main product routes.

### Domain Data

Typed domain models live in `src/types/domain.ts`. Demo data lives in `src/data/demoData.ts`. The mock API in `src/services/mockApi.ts` exposes async functions that mimic future backend boundaries:

- `getToday()`
- `getWorkout()`
- `saveWorkoutLog(input)`
- `getDiet()`
- `confirmMeal(mealId)`
- `saveManualMeal(input)`
- `getBodyMetrics()`
- `saveDailyCheckIn(input)`
- `getAdvice()`
- `sendAgentMessage(message)`
- `getSettings()`
- `saveSettings(input)`

Mock mutations update in-memory state during the current browser session. Reload resets data to the default demo seed.

### Pages

Each primary page is a real React component under `src/pages/`:

- `TodayPage.tsx`
- `OnboardingPage.tsx`
- `PlanPage.tsx`
- `WorkoutPage.tsx`
- `DietPage.tsx`
- `BodyPage.tsx`
- `AdvicePage.tsx`
- `AgentPage.tsx`
- `SettingsPage.tsx`

Pages use shared lightweight components under `src/components/`:

- `AppShell.tsx`
- `MetricCard.tsx`
- `ProgressBar.tsx`
- `SectionPanel.tsx`
- `StatusPill.tsx`
- `ActionButton.tsx`
- `EmptyState.tsx`
- `ConfirmModal.tsx`

Components should be simple and local. No new UI library is added in this phase.

## Product Behavior

### Today

Today shows:

- status summary
- today workout card
- today meal card
- body quick entry
- daily check-in
- Agent advice
- weekly progress

Core actions show visible state changes through mock API updates:

- save daily check-in
- mark workout completed
- confirm planned meal
- create manual meal draft
- open advice route

### Workout

Workout shows:

- weekly workout plan
- selected day's workout
- exercise list
- set-level completion controls
- workout history summary
- completion-rate and volume summary

### Diet

Diet shows:

- today meal plan
- nutrition progress
- meal list
- planned meal confirmation
- manual meal entry
- diet history summary

### Body

Body shows:

- current weight
- BMI
- recent trend summaries for 7, 30, and 90 days
- optional body-fat and waist rows shown as explicit empty states when no demo value exists
- goal-specific interpretation

### Advice

Advice replaces the overloaded `Analytics/Schedule` ambiguity. It shows:

- today's advice
- weekly summary
- plan adjustment recommendations
- advice source explanation
- accept, dismiss, and defer feedback actions

### Agent

Agent remains a deterministic mock chat, but it follows PRD constraints:

- it can explain plans
- it can prepare record drafts
- it does not silently save critical data
- draft-saving actions require explicit user confirmation

### Settings

Settings shows:

- demo profile
- goal and preference summaries
- unit setting
- language setting
- safety disclaimer
- data export entry shown as a disabled future capability

## Navigation Rules

- `Schedule` is not a primary route in the PRD information architecture and should not route to Weekly Summary.
- Weekly Summary belongs under Advice in this phase.
- `Body data` gets its own `/body` route.
- `Analytics` is not used as a primary navigation label in the new app shell. Trend and summary content is distributed across Body and Advice.
- Prototype-only routes are visibly marked as references so users do not confuse them with product routes.

## Styling Strategy

Use local CSS in `src/styles.css` for the new product shell. The style should borrow Stitch's "Refined Glacier Light" cues:

- light blue-white surface
- restrained glass panels
- compact dashboard cards
- primary blue accent
- green success state
- clear borders and subtle shadows

Avoid copying the Stitch HTML wholesale into business components. Use the Stitch screenshots and local exports as visual reference only.

## Testing And Verification

This phase is accepted when:

- `npm run build` passes.
- All primary routes render without console errors.
- Main navigation routes correctly:
  - Today -> `/`
  - Workout -> `/workout`
  - Diet -> `/diet`
  - Body -> `/body`
  - Advice -> `/advice`
  - Agent -> `/agent`
  - Settings -> `/settings`
- Prototype routes remain accessible under `/prototype`.
- Today, Workout, Diet, Advice, Agent, and Settings have at least one visible mock interaction each.
- `Schedule` no longer appears as a misleading top-level route in the main product shell.
- `design-qa.md` or a new QA note records that this is a functional foundation pass, not a full Stitch pixel migration.

## Risks

- The first real components will look less pixel-perfect than the Stitch HTML until each page is migrated visually.
- Keeping prototype and product routes side by side can confuse users if labels are not explicit.
- In-memory mock API state is useful for demos but must not be mistaken for persistence.

## Decisions

- Use incremental migration instead of rewriting all pages at once.
- Keep the existing Stitch implementation available under `/prototype`.
- Make PRD route structure the source of truth for product navigation.
- Do not add new dependencies for routing, state management, UI components, or charts in this phase.
