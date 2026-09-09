# Dashboard Opportunity Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace explanatory tooltips and technical tables with an always-visible, farmer-friendly summary of the Opportunity Score and classification.

**Architecture:** Render the API-provided `opportunity.breakdown` entries in a wrapping Dashboard grid as four plain-language scores “out of 100,” followed by a rounded overall score and farmer-friendly classification. Omit weights and contribution calculations from the summary, expand Dashboard units and period labels, and remove the shared glossary and all `InfoTip` controls without changing forecast data or scoring.

**Tech Stack:** Next.js 16, React 19, TypeScript, Vitest, Testing Library

**Spec:** Approved bounded design in the 2026-09-09 user conversation; no separate design document was required.

## Global Constraints

- Do not change opportunity-score calculation, classifications, API contracts, or forecast data.
- Remove all Dashboard and Forecasting tooltip controls.
- Remove the “What do these numbers mean?” panel from Dashboard and Forecasting.
- Keep the detailed Forecasting page's visible `Why this result?` explanations unchanged.
- Show factor and overall scores in plain language within every scored commodity card.
- Use a wrapping grid with no minimum width or horizontal scrolling.
- Do not abbreviate Dashboard units or common labels.

---

### Task 1: Lock the Dashboard explanation behavior

**Files:**
- Modify: `apps/web/src/app/page.test.tsx`
- Test: `apps/web/src/app/page.test.tsx`

**Interfaces:**
- Consumes: `DashboardClient` rendered through `Home`, mocked `getOutlook` responses with `BALANCED` opportunity data.
- Produces: Regression coverage proving the numeric opportunity breakdown is visible while prose, glossary, and tooltip controls are absent.

- [x] **Step 1: Write the failing test**

Extend the populated-dashboard fixture with all four API breakdown entries, then assert the rendered calculation:

```tsx
const breakdowns = screen.getAllByRole("table", { name: /opportunity breakdown/i });
expect(breakdowns).toHaveLength(4);
expect(within(breakdowns[0]).getByText("Demand pressure")).toBeVisible();
expect(within(breakdowns[0]).getByText("75")).toBeVisible();
expect(within(breakdowns[0]).getByText("39%")).toBeVisible();
expect(within(breakdowns[0]).getByText("29.2")).toBeVisible();
expect(within(breakdowns[0]).getByText("55.4 · balanced")).toBeVisible();
expect(screen.queryByText("What do these numbers mean?")).not.toBeInTheDocument();
expect(screen.queryByLabelText("What does this score mean?")).not.toBeInTheDocument();
expect(screen.queryByLabelText("What is Estimated Demand Proxy?")).not.toBeInTheDocument();
```

- [x] **Step 2: Run the test to verify it fails**

Run: `npm test -- src/app/page.test.tsx`

Expected: FAIL because the breakdown tables do not exist.

- [x] **Step 3: Preserve the failing test for Task 2**

Do not weaken text queries or mock the explanation UI. The test must exercise the real Dashboard component and fail on the missing visible behavior.

---

### Task 2: Render numeric per-commodity breakdowns and remove Dashboard tooltips

**Files:**
- Modify: `apps/web/src/app/DashboardClient.tsx`
- Test: `apps/web/src/app/page.test.tsx`

**Interfaces:**
- Consumes: Each `OutlookResponse.opportunity.breakdown`, overall `score`, and `classification`.
- Produces: Commodity cards with a visible factor calculation and overall result.

- [x] **Step 1: Implement the minimal Dashboard change**

Remove `GlossaryPanel` and `InfoTip` usage from the Dashboard. Keep plain metric labels and the existing classification badge, then add a visible calculation after the three metrics for scored opportunities:

```tsx
<table aria-label={`${commodity} opportunity breakdown`}>
  <thead>
    <tr><th>Factor</th><th>Score (0–100)</th><th>Weight</th><th>Contribution (pts)</th></tr>
  </thead>
  <tbody>
    {Object.entries(opp.breakdown).map(([key, entry]) => (
      <tr key={key}>
        <td>{opportunityFactorLabel(key)}</td>
        <td>{entry.score.toFixed(0)}</td>
        <td>{(entry.weight * 100).toFixed(0)}%</td>
        <td>{(entry.score * entry.weight).toFixed(1)}</td>
      </tr>
    ))}
  </tbody>
</table>
```

Use plain labels for demand, supply, and price so no Dashboard tooltip control remains.

- [x] **Step 2: Run the focused test to verify it passes**

Run: `npm test -- src/app/page.test.tsx`

Expected: PASS.

---

### Task 3: Remove the shared glossary and all Forecasting tooltips

**Files:**
- Modify: `apps/web/src/app/forecasting/ForecastingClient.tsx`
- Modify: `apps/web/src/components/forecast/ComponentCard.tsx`
- Modify: `apps/web/src/components/forecast/glossary.ts`
- Modify: `apps/web/src/app/globals.css`
- Delete: `apps/web/src/components/forecast/GlossaryPanel.tsx`
- Delete: `apps/web/src/components/ui/InfoTip.tsx`
- Modify: `apps/web/src/app/forecasting/page.test.tsx`

**Interfaces:**
- Consumes: Existing Forecasting page render behavior.
- Produces: Forecasting without the glossary or any tooltip controls, while retaining visible detailed explanations.

- [x] **Step 1: Add a failing Forecasting assertion**

Add to the ready-state Forecasting test:

```tsx
expect(screen.queryByText("What do these numbers mean?")).not.toBeInTheDocument();
expect(container.querySelector(".info-tip")).toBeNull();
```

- [x] **Step 2: Run the focused test to verify it fails**

Run: `npm test -- src/app/forecasting/page.test.tsx`

Expected: FAIL because Forecasting still renders `GlossaryPanel` and `InfoTip` controls.

- [x] **Step 3: Remove the shared glossary**

Remove the `GlossaryPanel` and `InfoTip` imports and renders from Forecasting components. Delete both unused components and remove the orphaned tooltip styles after confirming no runtime imports remain.

- [x] **Step 4: Run both focused tests**

Run: `npm test -- src/app/page.test.tsx src/app/forecasting/page.test.tsx`

Expected: PASS.

---

### Task 4: Verify the web application

**Files:**
- Verify only; do not introduce unrelated changes.

**Interfaces:**
- Consumes: Completed UI and test changes.
- Produces: Evidence that tests, types, linting, and production compilation remain healthy.

- [x] **Step 1: Run the complete web test suite**

Run: `npm test`

Expected: All tests PASS.

- [x] **Step 2: Run static checks**

Run: `npm run typecheck`

Expected: TypeScript exits successfully.

Run: `npm run lint`

Expected: ESLint exits successfully with no new errors.

- [x] **Step 3: Run the production build**

Run: `npm run build`

Expected: Next.js production build succeeds.

- [x] **Step 4: Review the final diff**

Run: `git diff --check`

Expected: No whitespace errors. Confirm every changed line traces to the requested UI change. Leave the work uncommitted unless the user explicitly requests a commit.

---

### Task 5: Apply the farmer-facing readability refinement

**Files:**
- Modify: `apps/web/src/app/DashboardClient.tsx`
- Modify: `apps/web/src/app/page.test.tsx`

**Interfaces:**
- Consumes: The same API-provided breakdown scores and classifications from Task 2.
- Produces: A non-scrolling summary with plain-language labels and fully written Dashboard units.

- [x] **Step 1: Replace the technical table expectations with failing summary expectations**

Require four accessible opportunity-summary regions containing “Demand,” “Limited supply,” “Price,” and “Forecast reliability,” with values stated as “out of 100.” Require the technical table to be absent.

- [x] **Step 2: Verify the revised Dashboard test fails**

Run: `npm test -- src/app/page.test.tsx`

Observed: FAIL because the old table and technical classification labels were still rendered.

- [x] **Step 3: Implement the wrapping summary and expanded labels**

Render the four factors with `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` and `min-w-0`, followed by a wrapping overall-result row. Expand `idx`, `MT`, `PHP/kg`, `Avg`, and quarter notation to “demand index,” “metric tons,” “pesos per kilogram,” “Average,” and “Quarter.”

- [x] **Step 4: Verify the revised Dashboard test passes**

Run: `npm test -- src/app/page.test.tsx`

Observed: PASS, 3 tests.
