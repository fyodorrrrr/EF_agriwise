"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProvinceSelect } from "@/components/filters/ProvinceSelect";
import { COMMODITIES } from "@/lib/domain";
import { getOutlook } from "@/lib/forecast";
import { usePreferences } from "@/lib/preferences";
import type { Commodity, OutlookResponse } from "@/types/forecast";
import { formatQuarter, formatValue, verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { Sparkline } from "@/components/forecast/Sparkline";

type Row = { commodity: Commodity; outlook: OutlookResponse };
type Status = "idle" | "loading" | "ready" | "error";

function componentSummary(outlook: OutlookResponse, kind: "demand" | "supply" | "price") {
  const c = outlook[kind];
  if (c.verdict === "INSUFFICIENT_DATA") return "—";
  const series = c.forecast?.length ? c.forecast : c.observed ?? [];
  const value = series.length ? series[series.length - 1].value : null;
  return value === null ? "—" : formatValue(value, c.unit);
}

function computeKpis(rows: Row[]) {
  const covered = rows.filter(
    ({ outlook }) =>
      outlook.demand.verdict !== "INSUFFICIENT_DATA" &&
      outlook.supply.verdict !== "INSUFFICIENT_DATA" &&
      outlook.price.verdict !== "INSUFFICIENT_DATA" &&
      outlook.opportunity.verdict !== "INSUFFICIENT_DATA",
  );
  const scored = rows.filter(({ outlook }) => outlook.opportunity.score !== null);
  const best = scored.reduce<Row | null>(
    (top, row) =>
      !top || (row.outlook.opportunity.score ?? -Infinity) > (top.outlook.opportunity.score ?? -Infinity)
        ? row
        : top,
    null,
  );
  const avgScore = scored.length
    ? scored.reduce((sum, { outlook }) => sum + (outlook.opportunity.score ?? 0), 0) / scored.length
    : null;

  return { covered, best, avgScore };
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
        <ProvinceSelect value={province} onChange={setProvince} />
      </div>

      {!province && <p className="state">Choose a province above to see its outlook.</p>}

      {status === "loading" && <p className="state state-loading">Loading outlook…</p>}

      {status === "error" && (
        <p className="state state-error">
          Couldn&apos;t reach the forecast service. Try again in a moment.
        </p>
      )}

      {status === "ready" && rows.length > 0 && (() => {
        const { covered, best, avgScore } = computeKpis(rows);
        return (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <KpiCard label="Commodities tracked" value={String(COMMODITIES.length)} />
            <KpiCard
              label="Data coverage"
              value={`${covered.length}/${rows.length}`}
              sublabel="fully populated"
            />
            <KpiCard
              label="Best opportunity"
              value={best ? best.commodity : "—"}
              sublabel={
                best?.outlook.opportunity.classification
                  ? best.outlook.opportunity.classification.replaceAll("_", " ").toLowerCase()
                  : undefined
              }
            />
            <KpiCard
              label="Avg opportunity score"
              value={avgScore === null ? "—" : avgScore.toFixed(0)}
            />
          </div>
        );
      })()}

      {status === "ready" &&
        rows.map(({ commodity, outlook }) => {
          const opp = outlook.opportunity;
          return (
            <div key={commodity} className="card flex flex-col gap-3">
              <div className="card-head">
                <div className="card-title">{commodity}</div>
                <div className="flex items-center gap-3">
                  <Sparkline observed={outlook.demand.observed} forecast={outlook.demand.forecast} />
                  {opp.verdict === "INSUFFICIENT_DATA" ? (
                    <span className={verdictBadgeClass("INSUFFICIENT_DATA")}>
                      Opportunity: {verdictLabel("INSUFFICIENT_DATA")}
                    </span>
                  ) : (
                    <span className="badge badge-accent">
                      {opp.classification?.replaceAll("_", " ").toLowerCase()} · {opp.score}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-2 text-sm sm:grid sm:grid-cols-3 sm:gap-3">
                {(["demand", "supply", "price"] as const).map((kind) => (
                  <div
                    key={kind}
                    className="flex items-center justify-between gap-3 sm:flex-col sm:items-start sm:gap-1"
                  >
                    <span className="card-kicker">
                      {kind === "demand" ? "Demand proxy" : kind}
                    </span>
                    <span className="flex items-center gap-2 sm:mt-1 sm:flex-col sm:items-start sm:gap-1">
                      <span className="text-md font-semibold">
                        {componentSummary(outlook, kind)}
                      </span>
                      <span className={verdictBadgeClass(outlook[kind].verdict)}>
                        {verdictLabel(outlook[kind].verdict)}
                      </span>
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
