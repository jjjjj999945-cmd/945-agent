# Task 2 Report: Normalize HTTP Errors and Expose Initial Load Failures

## Scope

Implemented Task 2 in the assigned worktree. The mock/default API path remains unchanged; the changes apply to `httpApi` protocol validation and to initial-load error rendering.

## RED Evidence

Command:

```powershell
npm run qa:http -- --grep "errors|non-JSON|aborted"
```

Output:

```text
Running 3 tests using 1 worker

  x  1 [chrome-desktop-http] › tests\http-integration.spec.ts:23:3 › 945 real HTTP integration › shows normalized validation errors (12.5s)
  -  2 [chrome-desktop-http] › tests\http-integration.spec.ts:35:3 › 945 real HTTP integration › shows protocol errors for non-JSON responses
  -  3 [chrome-desktop-http] › tests\http-integration.spec.ts:43:3 › 945 real HTTP integration › shows network errors when the API request is aborted

Error: expect(locator).toContainText(expected) failed
Locator: getByRole('status')
Expected substring: "Request validation failed."
Timeout: 10000ms
Error: element(s) not found

1 failed
2 did not run
```

The first test failed for the expected reason: the empty-data guard only rendered Loading and had no visible status role or normalized error message. The serial suite therefore did not execute the remaining two cases.

## GREEN Evidence

Command:

```powershell
npm run qa:http -- --grep "errors|non-JSON|aborted"
```

Output:

```text
Running 3 tests using 1 worker

  ok 1 [chrome-desktop-http] › tests\http-integration.spec.ts:27:3 › 945 real HTTP integration › shows normalized validation errors (5.5s)
  ok 2 [chrome-desktop-http] › tests\http-integration.spec.ts:39:3 › 945 real HTTP integration › shows protocol errors for non-JSON responses (1.8s)
  ok 3 [chrome-desktop-http] › tests\http-integration.spec.ts:47:3 › 945 real HTTP integration › shows network errors when the API request is aborted (2.2s)

3 passed (14.8s)
```

## Regression and Build Evidence

Command:

```powershell
npm run qa:app
```

Output:

```text
Running 9 tests using 3 workers

4 skipped
5 passed (29.2s)
```

The four HTTP-only tests are skipped under the default `chrome-desktop` project. The mock suite remains at five passing tests. The test file now explicitly requires the `chrome-desktop-http` project, which starts FastAPI; this prevents `qa:app` from attempting an HTTP health check against a backend it intentionally does not start.

Command:

```powershell
npm run build
```

Output:

```text
> 945-stitch-frontend@0.1.0 build
> tsc && vite build

vite v7.3.6 building client environment for production...
56 modules transformed.
dist/index.html                 5.27 kB | gzip: 1.57 kB
dist/assets/index-BV9lmjVa.css 67.95 kB | gzip: 13.52 kB
dist/assets/index-xqbkTnI5.js 289.33 kB | gzip: 88.48 kB
built in 914ms
```

`git diff --check` completed with exit code 0.

## Files Changed

- `src/components/business/PageLoadState.tsx` (new shared initial-load status component)
- `src/services/httpApi.ts`
- `src/pages/TodayPage.tsx`
- `src/pages/WorkoutPage.tsx`
- `src/pages/DietPage.tsx`
- `src/pages/BodyPage.tsx`
- `src/pages/AdvicePage.tsx`
- `src/pages/SettingsPage.tsx`
- `tests/http-integration.spec.ts`

## Self-Review

- Valid unified `{ data, error }` success and error envelopes return unchanged only when their shape is valid.
- FastAPI 422 envelopes retain their `detail` in `VALIDATION_ERROR.details`.
- Invalid JSON and JSON that is not a valid unified envelope return `HTTP_ERROR` with status and path.
- Fetch failures continue to return `NETWORK_ERROR` with the existing diagnostics.
- Every specified initial-load guard now renders `PageLoadState` with `notice || t("status.loading")`.
- The HTTP suite is excluded from mock QA through an HTTP-project guard in the allowed test file; no mock/default client code changed.

## Concerns

- The HTTP-project guard relies on the Task 1 project name `chrome-desktop-http`. Renaming that project requires updating the guard.
- The three new browser tests exercise Today page loading; the other five page integrations are covered structurally by their shared component use and by the existing mock regression suite, rather than by separate HTTP-failure browser cases.
