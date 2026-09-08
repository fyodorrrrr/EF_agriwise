"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { COMMODITIES, PROVINCES } from "@/lib/domain";
import { getOutlook } from "@/lib/forecast";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, OutlookResponse, Province } from "@/types/forecast";
import { formatQuarter, formatValue, verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";

type Row = { commodity: Commodity; outlook: OutlookResponse };
type Status = "idle" | "loading" | "ready" | "error";

function componentSummary(outlook: OutlookResponse, kind: "demand" | "supply" | "price") {
  const c = outlook[kind];
  if (c.verdict === "INSUFFICIENT_DATA") return "—";
  const series = c.forecast?.length ? c.forecast : c.observed ?? [];
  const value = series.length ? series[series.length - 1].value : null;
  return value === null ? "—" : formatValue(value, c.unit);
}

export function DashboardClient() {
  const { preferences, isHydrated, setProvince } = usePreferences();
  const province = preferences.province;

  const [result, setResult] = useState<{ province: string; rows: Row[] } | null>(null);
  const [errorProvince, setErrorProvince] = useState<string | null>(null);

  useEffect(() => {
    if (!province) return;
    let cancelled = false;
    Promise.all(COMMODITIES.map((commodity) => getOutlook(commodity, province)))
      .then((outlooks) => {
        if (cancelled) return;
        setResult({
          province,
          rows: COMMODITIES.map((commodity, i) => ({ commodity, outlook: outlooks[i] })),
        });
      })
      .catch(() => !cancelled && setErrorProvince(province));
    return () => {
      cancelled = true;
    };
  }, [province]);

  // Derived — a previous province's rows never leak through.
  const status: Status = !province
    ? "idle"
    : errorProvince === province
      ? "error"
      : result?.province === province
        ? "ready"
        : "loading";
  const rows = result?.province === province ? result.rows : [];

  if (!isHydrated) return null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>CALABARZON Outlook</h1>
          <p>
            Province-resolution demand, supply, price, and opportunity for all four
            commodities. This is not a municipality-level forecast.
          </p>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Province</span>
          <select
            aria-label="Province"
            className="input-bare border rounded-md px-2 py-1"
            value={province ?? ""}
            onChange={(e) => setProvince((e.target.value || null) as Province | null)}
          >
            <option value="">Select a province…</option>
            {PROVINCES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!province && (
        <p className="state">
          Choose a province to see its outlook, or head to{" "}
          <Link href="/setup" className="underline">
            Setup
          </Link>
          .
        </p>
      )}

      {status === "loading" && <p className="state state-loading">Loading outlook…</p>}

      {status === "error" && (
        <p className="state state-error">
          Couldn&apos;t reach the forecast service. Try again in a moment.
        </p>
      )}

      {status === "ready" &&
        rows.map(({ commodity, outlook }) => {
          const opp = outlook.opportunity;
          return (
            <div key={commodity} className="card flex flex-col gap-3">
              <div className="card-head">
                <div className="card-title">{commodity}</div>
                {opp.verdict === "INSUFFICIENT_DATA" ? (
                  <span className="badge badge-neutral">Opportunity: n/a</span>
                ) : (
                  <span className="badge badge-accent">
                    {opp.classification?.replaceAll("_", " ").toLowerCase()} · {opp.score}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm">
                {(["demand", "supply", "price"] as const).map((kind) => (
                  <div key={kind} className="flex flex-col gap-1">
                    <span className="card-kicker">
                      {kind === "demand" ? "Demand proxy" : kind}
                    </span>
                    <span className="text-md font-semibold">
                      {componentSummary(outlook, kind)}
                    </span>
                    <span className={verdictBadgeClass(outlook[kind].verdict)}>
                      {verdictLabel(outlook[kind].verdict)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="card-foot flex items-center justify-between text-xs text-muted">
                <span>
                  {opp.shared_quarter
                    ? `Opportunity quarter: ${formatQuarter(opp.shared_quarter)}`
                    : "Opportunity unavailable"}
                </span>
                <Link
                  href={`/forecasting?commodity=${encodeURIComponent(commodity)}`}
                  className="btn btn-ghost btn-sm"
                >
                  Details →
                </Link>
              </div>
            </div>
          );
        })}
    </div>
  );
}
