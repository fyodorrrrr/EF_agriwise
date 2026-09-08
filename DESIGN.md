---
name: AgriWise
description: Province-resolution agricultural forecasting analytics for CALABARZON, dressed as a calm field ledger.
colors:
  ground: "#f4f3f2"
  surface: "#ffffff"
  sunken: "#ecebe9"
  ink: "#171615"
  body: "#201f1d"
  muted: "#6f6c68"
  line: "#e6e4e1"
  divider: "#eae8e5"
  neutral-100: "#f7f6f5"
  neutral-200: "#eceae8"
  neutral-300: "#dbd8d5"
  neutral-500: "#97938e"
  neutral-700: "#5b5854"
  neutral-800: "#3d3a37"
  accent-100: "#eef3ee"
  accent-200: "#d5e2d6"
  accent-400: "#7fa385"
  accent-500: "#4b7552"
  accent-600: "#3d6144"
  accent-700: "#2f4c35"
  accent-800: "#223727"
  on-accent: "#ffffff"
  leaf-100: "#f4f7ea"
  leaf-500: "#86a13c"
  leaf-800: "#3d4c1c"
  warn-100: "#fbf1e2"
  warn-500: "#b8811f"
  warn-700: "#855b12"
  info-100: "#eaf0f5"
  info-500: "#416d8f"
  info-700: "#2f5069"
  danger-100: "#fbeeec"
  danger-500: "#b23b2e"
  danger-700: "#7f2820"
  viz-track: "#eceae8"
  viz-from: "#eef3ee"
  viz-to: "#2f4c35"
typography:
  display:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(30px, 4vw, 44px)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(24px, 2.9vw, 32px)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(20px, 2.1vw, 24px)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Plus Jakarta Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.08em"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "8px"
  md: "12px"
  lg: "20px"
  xl: "28px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "#2f2c29"
    textColor: "#ffffff"
  button-accent:
    backgroundColor: "{colors.accent-500}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
  button-accent-hover:
    backgroundColor: "{colors.accent-600}"
    textColor: "#ffffff"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.pill}"
    padding: "7px 16px"
  chip-selected:
    backgroundColor: "{colors.accent-500}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "7px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    height: "42px"
  badge-accent:
    backgroundColor: "{colors.accent-100}"
    textColor: "{colors.accent-800}"
    rounded: "{rounded.pill}"
    padding: "4px 11px"
  sidenav-item:
    backgroundColor: "transparent"
    textColor: "{colors.neutral-700}"
    rounded: "{rounded.pill}"
    padding: "9px 12px"
  sidenav-item-active:
    backgroundColor: "{colors.accent-500}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    padding: "9px 12px"
---

# Design System: AgriWise

## Overview

**Creative North Star: "The Extension Officer's Desk"**

AgriWise looks like the workspace of a good agricultural extension officer: plain-spoken,
field-ready, and built to be trusted. One farmer opens it on a slow phone to decide what to
plant; one LGU planner opens it to read the evidence behind that same number. The interface
has to serve both without changing its voice — so it stays warm and reassuring on the
surface, with the rigor kept one tap away rather than in your face.

The world is light-theme only, set on warm paper-grey (`#f4f3f2`) rather than clinical white,
with near-black warm ink for text. Green is the only chromatic voice: a muted **Field Forest
Green** for everything interactive and authoritative, a warmer **Ripe Leaf Green** for
"this passed." The three status hues (amber, blue, red) are the sole non-greens and they
only ever carry meaning. Type is a single humanist sans (Plus Jakarta Sans) doing all the
work, with JetBrains Mono reserved for figures and identifiers. Corners are generous,
controls are fully rounded pills, and shadows are so faint they read as a lift of the paper,
not a drop. Nothing is loud; the brand lives in the precision of the details — the dashed
forecast segment of a sparkline, the uppercase kicker on a card, the one green that means
"go."

Confirmed anti-reference: this is not a "data platform" dashboard. No dark chrome, no neon
accents on black, no dense gridlined tables trying to look like a trading terminal, no
decorative gradients. Restraint is the point.

**Key Characteristics:**
- Warm paper-grey ground, never pure-white page
- A single green voice for action; status colors carry meaning only
- One humanist sans for everything; mono only for numbers and IDs
- Fully-pill buttons and chips; generously rounded cards (20px)
- Depth from tonal surfaces first, faint shadow second
- Every state — loading, empty, error, insufficient-data — is a designed component
- Mobile: the side rail becomes a fixed bottom tab bar; touch targets grow to 44px

## Colors

An almost-monochrome warm-neutral field with one green that does nearly all the chromatic
work and three meaning-only status hues.

### Primary
- **Field Forest Green** (`#4b7552`, `accent-500`): the single interactive and authoritative
  voice. Accent buttons, selected chips, active nav item, links, focus outlines, the
  sparkline stroke, meter fill, "Why this result?" disclosure triggers. Darker steps
  `accent-600`/`accent-700` are hover/active; `accent-100`/`accent-200` are tint backgrounds
  for badges, notices, selection wash, and `::selection`.

### Secondary
- **Ripe Leaf Green** (`#86a13c`, `leaf-500`): the affirmative signal, warmer and yellower
  than the primary. Reserved for `PASS` verdicts (`badge-leaf`) and healthy/positive states.
  `leaf-100` background with `leaf-800` text. Not an action color — never on a button.

### Tertiary — Status (meaning only)
- **Caution Amber** (`#b8811f` / text `#855b12`, `warn`): `CAUTION` and `INDICATIVE_PROXY`
  verdicts, cautionary notices.
- **Proxy Blue** (`#416d8f` / text `#2f5069`, `info`): `USABLE_PROXY` verdict, informational
  notices, neutral map/context callouts.
- **Insufficient Red** (`#b23b2e` / text `#7f2820`, `danger`): errors, invalid inputs, and
  hard-stop failure states. `INSUFFICIENT_DATA` itself is deliberately **neutral grey**, not
  red — missing data is a fact, not an alarm.

### Neutral
- **Warm Ink** (`#171615`, `ink`) / **Body** (`#201f1d`): headings and primary text; `ink`
  also fills the primary (non-accent) button.
- **Muted** (`#6f6c68`) / **Neutral 500** (`#97938e`): secondary text, labels, meta rows,
  placeholders.
- **Paper Grey** (`#f4f3f2`, `ground`): the page. **Surface** (`#ffffff`): cards, sidebar,
  inputs, raised elements. **Sunken** (`#ecebe9`): recessed wells.
- **Line** (`#e6e4e1`) / **Divider** (`#eae8e5`): input borders, card feet, table rules,
  section separators.

### Data visualisation
- Sparkline / meter stroke: Field Forest Green (`#4b7552`). Track: `#eceae8`.
- Choropleth / value ramp: `viz-from` `#eef3ee` → `viz-to` `#2f4c35` (light forest tint to
  deep forest). Absent/no-data cells use `neutral` grey, never a ramp step.

### Named Rules
**The One Green Rule.** There is exactly one action color. If a control does something, it is
Field Forest Green or it is ink; it is never Ripe Leaf Green. Leaf green only ever means
"passed."

**The Meaning-Never-Decoration Rule.** Amber, blue, and red appear only to carry a verdict,
notice, or error state. They are never used for emphasis, theming, or visual interest.

**The Grey Gap Rule.** `INSUFFICIENT_DATA` renders in neutral grey (`badge-neutral`),
never in red or amber. The product is honest about missing data without dramatizing it.

## Typography

**Display / Body / Label Font:** Plus Jakarta Sans (with `ui-sans-serif, system-ui,
sans-serif`)
**Mono Font:** JetBrains Mono (with `ui-monospace, Menlo, monospace`)

**Character:** One friendly humanist sans carries the entire interface — approachable enough
for a farmer, clean enough for a report. Headings tighten (`-0.025em`) and go heavy (700–800)
to feel decisive; body sits at a comfortable 15px / 1.55 for reading on a phone. Mono is a
deliberate, narrow exception: figures, prices, quarters, model IDs, and anything that should
line up in a column.

### Hierarchy
- **Display** (800, `clamp(30–44px)`, 1.15): page `<h1>` on top-level views only.
- **Headline** (700, `clamp(24–32px)`, 1.15): `<h2>` section headers.
- **Title** (700, `clamp(20–24px)`, 1.15): `<h3>`, and the `.page-head h1` (which is
  intentionally set at title size, not display, so working pages stay calm).
- **Body** (400, 15px, 1.55): default text. Descriptive paragraphs cap at ~72ch.
- **Card title** (700, 17px, 1.25): the heading inside a `.card`.
- **Label / Kicker** (600, 11px, `0.08em`, UPPERCASE): card kickers, disclosure sub-heads,
  spec labels. The uppercase micro-label is a signature.
- **UI text** (500–600, 13–14px): buttons, chips, nav, inputs, table cells.

### Named Rules
**The Fixed-Dense Rule.** Display sizes are fluid (`clamp`); UI and data sizes (`xs`–`md`,
12–17px) are fixed pixels. A data table must not shrink on a small screen — it scrolls
instead.

**The Mono-For-Numbers Rule.** JetBrains Mono is for values and identifiers only —
₱-prices, MT figures, index numbers, quarter labels, model names. Never set prose or labels
in mono.

## Layout

A fixed left sidebar (`224px`) holds primary navigation; an optional right aside (`320px`)
carries contextual evidence. The main column scrolls independently at `24px` padding and is
constrained by a container scale — `narrow 448` / `reading 672` / `page 896` / `wide 1024` /
`full 1200` — chosen per view rather than one global max-width.

Spacing follows Tailwind's 4px scale. Cards are `24px` internal padding; grids gap `16px`;
section separators add `24px` top margin plus a `16px` padded rule. The `.page-head` pattern
opens every view: a title, a `≤72ch` description, and optional trailing actions, with `24px`
below it.

**Responsive** (breakpoints are Tailwind's own, so utilities and hand-written rules agree):
- **`≤767px`**: shell stacks; sidebar becomes a fixed bottom tab bar (icon + short label,
  `44px` min height, above the home indicator); content gets bottom padding to clear it;
  aside goes full-width.
- **`≤639px`**: grids collapse to one column; card padding drops to `16px` and radius to
  `12px`; `page-head` stacks; chip rows become a horizontal no-wrap scroller.
- **`(hover: none)`**: every control grows to a `≥44px` touch target; inputs go to `16px`
  font to stop iOS zoom.
- **`prefers-reduced-motion`**: spinners and skeleton pulses freeze.

## Elevation & Depth

Hybrid. Structure comes first from **tonal surfaces** — `ground` (page) vs `surface` (raised)
vs `sunken` (recessed) — and from hairline `line`/`divider` borders. The **shadow scale then
adds a gentle secondary lift**, deliberately low-opacity (all layers ≈ 5–9% warm black) so a
card reads as paper resting on paper, never as a floating panel.

### Shadow Vocabulary
- **`shadow-sm`** (`0 1px 2px rgba(23,22,21,0.05)`): resting state for cards, chips,
  secondary buttons, inputs, table wraps.
- **`shadow-md`** (`0 2px 6px / 0 8px 20px, both 0.05`): hover response, and the resting
  state for the chat `input-shell`.
- **`shadow-lg`** (`0 8px 16px / 0 24px 56px, 0.06–0.09`): overlays, popovers, the highest
  elevation. Used sparingly.

### Named Rules
**The Paper-Lift Rule.** Shadows never exceed the `lg` scale and never darken past ~9%.
Depth is a whisper. If something needs to feel separated, change its surface tone or add a
border before you reach for a bigger shadow.

**The Hover-Deepens Rule.** Interactive surfaces rest at `shadow-sm` and move to `shadow-md`
+ a `-2px` translate on hover. Selection is shown with an inset `2px accent-400` ring
(`card-selected`), not a heavier shadow.

## Shapes

Soft and rounded throughout. Four radius steps — `sm 8` / `md 12` / `lg 20` / `xl 28` —
plus a full `999px` pill. Cards and table wraps use `lg` (`20px`, tightening to `md` on
small screens); inputs and notices use `md`; small chrome uses `sm`. **Buttons, chips,
badges, nav items, and the chat bar are all fully-pill** — the rounded silhouette is the
most recognizable formal signature of the system. Borders are hairline (`1px`, occasionally
`1.5px` on the checkbox) in `line`/`neutral-300`. No sharp corners anywhere in the UI.

## Components

### Buttons
- **Shape:** fully rounded pill (`999px`), `10px 18px` padding, `14px`/600 label, `7px`
  icon gap. `btn-sm` is `6px 12px` / `13px`. `btn-icon` is `40px` square.
- **Primary:** warm ink fill (`#171615`), white text → hover `#2f2c29`. The default
  high-emphasis action.
- **Accent:** Field Forest Green fill (`accent-500`), white text → hover `accent-600` →
  active `accent-700`. Used for the affirmative primary action in a flow.
- **Secondary:** white surface, `shadow-sm` → hover `neutral-100` + `shadow-md`.
- **Ghost:** transparent, muted text → hover `neutral-200` wash + body text.
- **Disabled:** `opacity 0.45`, no shadow, `not-allowed`.
- **Touch:** `≥44px` min-height under `(hover: none)`.

### Chips (selectable filters)
- **Style:** pill, white surface + `shadow-sm`, `14px`/600, `7px 16px`. One row per filter
  axis (`chip-group`); on mobile the row becomes a hidden-scrollbar horizontal scroller.
- **State:** `aria-pressed="true"` → Field Forest Green fill, white text, shadow removed;
  hover `accent-600`. The `chip-ink` variant selects to ink instead of green.
- **Disabled:** `opacity 0.45`, no shadow.

### Cards / Containers
- **Corner:** `lg` (`20px`), → `md` (`12px`) at `≤639px`.
- **Background:** white `surface` on the paper `ground`.
- **Shadow:** `shadow-sm` at rest; `card-hover` lifts to `shadow-md` + `translateY(-2px)`;
  `card-selected` adds an inset `2px accent-400` ring.
- **Anatomy:** optional `card-kicker` (uppercase 11px accent label), `card-title` (17px/700),
  `card-body` (14px muted), `card-foot` (top border, `12px` padding). Internal padding
  `24px` → `16px` on small screens.

### Inputs / Fields
- **Style:** white surface, `1px line` border, `md` radius (`12px`), `shadow-sm`, `≥42px`
  height, `14px` text, accent caret.
- **Hover:** border → `neutral-300`.
- **Focus:** border → `accent-500` plus a `3px accent-200` outline (soft double-ring).
- **Invalid:** `aria-invalid="true"` → `danger-500` border.
- **Field wrapper:** stacked `label` (14px/500 muted) + control + optional `hint` (12px).
- **`input-shell`:** a pill containing a borderless input plus a trailing icon button —
  the "Ask AgriWise" chat bar. Rests at `shadow-md`; `focus-within` adds a `3px accent-200`
  ring.

### Badges & Notices
- **Badge:** pill, `12px`/600, `4px 11px`. Tint-background + dark-text pairs: `accent`,
  `leaf` (=PASS), `neutral` (=INSUFFICIENT_DATA), `warn`, `info`, `danger`, plus a
  bordered `outline` variant.
- **Notice:** `md` radius, `10px 14px`, `14px` text, same one-color-per-meaning tint pairs.

### Navigation
- **Sidebar:** sticky, `224px`, white, right hairline border. Brand wordmark at top in
  `accent-700`, 800 weight, `-0.03em`.
- **Item:** pill, `13px`/500, `12px` icon gap, `neutral-700` text with `neutral-600` icon →
  hover `accent-100` wash + `accent-700` → active (`aria-current="page"`) solid
  `accent-500` fill, white text and icon.
- **Mobile:** fixed bottom tab bar — items go vertical (icon over `11px` short label),
  active state softens to `accent-100` wash (not the solid fill) to stay quiet at the
  bottom of the screen.

### Data components (signature)
- **Sparkline:** observed segment solid Field Forest Green `1.5px`; forecast segment
  **dashed** and joined at the last observed point; boundary point marked. Renders nothing
  below two points.
- **Meter:** `6px` pill track (`viz-track`), Field Forest Green fill, with a label row above
  (`12px`, space-between).
- **Spec list:** two-column `<dl>`, `12px`, muted label left / body value right
  (`spec-wide` flips to `150px 1fr`, left-aligned).
- **Disclosure ("Why this result?"):** top border, `12px`/600 accent summary (no marker),
  body in `neutral-700` with uppercase `11px` sub-heads. This is how planner-grade evidence
  is kept one tap from the farmer's plain read.
- **States:** `state-loading` (inline spinner), `state-empty` (centered, `48px` padding,
  muted), `state-error` (`danger-700`), `skeleton` (`neutral-200`, pulse). Every page uses
  the real components — states are never ad-hoc.

## Do's and Don'ts

### Do:
- **Do** set pages on `ground` (`#f4f3f2`) and raise content onto white `surface` cards.
- **Do** use Field Forest Green (`accent-500`) as the only action/selection color; use ink
  (`#171615`) for the neutral high-emphasis button.
- **Do** reserve Ripe Leaf Green strictly for `PASS`, and render `INSUFFICIENT_DATA` in
  neutral grey.
- **Do** keep buttons, chips, badges, and nav items fully pill-shaped (`999px`).
- **Do** set every price, tonnage, index value, quarter, and model ID in JetBrains Mono.
- **Do** give loading, empty, error, and insufficient-data their designed components on
  every view.
- **Do** show forecast series as a dashed continuation of a solid observed line.
- **Do** grow controls to `≥44px` and inputs to `16px` under `(hover: none)`.
- **Do** keep the `:focus-visible` accent outline (`2px accent-500`, `2px` offset) intact.

### Don't:
- **Don't** introduce a dark theme, dark chrome, or a pure-white (`#fff`) page background.
- **Don't** use amber, blue, or red for anything but a verdict, notice, or error — never for
  emphasis or decoration.
- **Don't** put Ripe Leaf Green on a button or use it as a general "good" accent.
- **Don't** add gradients (except the defined choropleth value ramp), glows, or shadows
  heavier than `shadow-lg` / ~9% opacity.
- **Don't** set prose or labels in mono, or shrink data tables below their fixed sizes —
  scroll them.
- **Don't** add a second accent hue or theme color; the palette is one green plus warm
  neutrals plus meaning-only status.
- **Don't** present a municipality-level or physical-MT figure as if the design implies a
  precision the data lacks — the honest-labeling conventions are product, not decoration.
