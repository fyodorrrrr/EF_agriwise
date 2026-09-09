import type { ReactNode } from "react";

/**
 * Primary navigation. `group` decides the mobile bottom bar:
 * "primary" items are always-visible tabs; "more" items live behind
 * the "More" tab's sheet. On desktop every item shows in the rail.
 *
 * Icons are authored inline (Lucide geometry, 24px grid, 2px stroke,
 * currentColor) so a truncated label on a narrow phone still reads.
 */
export type NavGroup = "primary" | "more";

export interface NavItem {
  href: string;
  label: string;
  /** Shorter label for the mobile tab bar. */
  short: string;
  group: NavGroup;
  icon: ReactNode;
}

const svg = (children: ReactNode) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

export const NAV_ITEMS: readonly NavItem[] = [
  {
    href: "/",
    label: "Dashboard",
    short: "Home",
    group: "primary",
    icon: svg(
      <>
        <rect width="7" height="7" x="3" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="14" rx="1" />
        <rect width="7" height="7" x="3" y="14" rx="1" />
      </>,
    ),
  },
  {
    href: "/forecasting",
    label: "Forecasting",
    short: "Forecast",
    group: "primary",
    icon: svg(
      <>
        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
        <polyline points="16 7 22 7 22 13" />
      </>,
    ),
  },
  {
    href: "/mapping",
    label: "Mapping",
    short: "Map",
    group: "primary",
    icon: svg(
      <>
        <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
        <line x1="9" x2="9" y1="3" y2="18" />
        <line x1="15" x2="15" y1="6" y2="21" />
      </>,
    ),
  },
  {
    href: "/markets",
    label: "Markets",
    short: "Markets",
    group: "primary",
    icon: svg(
      <>
        <path d="M2 7h20l-1.5-3.2A2 2 0 0 0 18.7 2.6H5.3a2 2 0 0 0-1.8 1.2z" />
        <path d="M4 7v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7" />
        <path d="M9 21v-5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v5" />
      </>,
    ),
  },
  {
    href: "/model-evidence",
    label: "Model Evidence",
    short: "Evidence",
    group: "more",
    icon: svg(
      <>
        <path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2" />
        <path d="M6.453 15h11.094" />
        <path d="M8.5 2h7" />
      </>,
    ),
  },
] as const;

export const MORE_ICON = svg(
  <>
    <circle cx="12" cy="12" r="1" />
    <circle cx="19" cy="12" r="1" />
    <circle cx="5" cy="12" r="1" />
  </>,
);
