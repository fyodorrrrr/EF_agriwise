"use client";

import { useEffect, useState } from "react";

import { ProvinceSelect } from "@/components/filters/ProvinceSelect";
import { classificationLabel } from "@/components/forecast/glossary";
import { formatValue, verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { getAdvisories } from "@/lib/advisory";
import { usePreferences } from "@/lib/preferences";
import type { AdvisoryRecord, AdvisoryResponse } from "@/types/advisory";

const TYPE_LABEL: Record<string, string> = {
  OPPORTUNITY: "Potential opportunity",
  MARKET_WATCH: "Market watch",
  RISK: "Risk watch",
  PRICE_UPDATE: "Price update",
  MARKET_ACCESS: "Market access",
};

function percent(value: number | null) {
  return value === null ? "Not available" : `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function SignalLine({ advisory }: { advisory: AdvisoryRecord }) {
  const signals = advisory.signals;
  const items = [
    signals.demand_growth_pct !== null && `Demand ${percent(signals.demand_growth_pct)}`,
    signals.supply_growth_pct !== null && `Supply ${percent(signals.supply_growth_pct)}`,
    signals.price_growth_pct !== null && `Price ${percent(signals.price_growth_pct)}`,
  ].filter(Boolean);
  return <p className="text-xs text-muted">{items.length ? items.join(" · ") : "Trend data unavailable for this period."}</p>;
}

function AdvisoryCard({ advisory, compact = false }: { advisory: AdvisoryRecord; compact?: boolean }) {
  return (
    <article className="card flex flex-col gap-3">
      <div className="card-head gap-3">
        <div>
          <span className="card-kicker">{TYPE_LABEL[advisory.advisory_type]}</span>
          <h2 className={compact ? "text-base font-semibold" : "text-lg font-semibold"}>{advisory.headline}</h2>
        </div>
        <span className="badge badge-accent">{advisory.opportunity.score === null ? "Score unavailable" : `${Math.round(advisory.opportunity.score)} / 100`}</span>
      </div>
      <p className="text-sm text-muted">{advisory.summary}</p>
      <SignalLine advisory={advisory} />
      {!compact && (
        <>
          <p className="text-sm"><span className="font-medium">Consideration: </span>{advisory.farmer_consideration}</p>
          <div className="flex flex-wrap gap-2 text-xs text-muted">
            <span>{advisory.commodity} · {advisory.province}</span>
            {advisory.period && <span>{advisory.period}</span>}
            {advisory.opportunity.classification && <span>{classificationLabel(advisory.opportunity.classification)}</span>}
            <span className={verdictBadgeClass(advisory.demand.verdict)}>{verdictLabel(advisory.demand.verdict)} confidence: {advisory.confidence.toLowerCase()}</span>
          </div>
          <details className="rounded border border-line p-3 text-sm">
            <summary className="cursor-pointer font-medium">View supporting data</summary>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {(["demand", "supply", "price"] as const).map((kind) => {
                const component = advisory[kind];
                return <div key={kind}><span className="card-kicker">{kind}</span><div>{component.value === null ? "Unavailable" : formatValue(component.value, component.unit)}</div><span className="text-xs text-muted">{component.frequency} · {component.source ?? "source unavailable"}</span></div>;
              })}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <span>Demand growth: {percent(advisory.signals.demand_growth_pct)}</span>
              <span>Supply growth: {percent(advisory.signals.supply_growth_pct)}</span>
              <span>Price growth: {percent(advisory.signals.price_growth_pct)}</span>
              {advisory.signals.physical_gap !== null && <span>Physical demand–supply gap: {formatValue(advisory.signals.physical_gap, "MT")}</span>}
            </div>
            {advisory.limitations.length > 0 && <ul className="mt-3 list-disc pl-5 text-xs text-muted">{advisory.limitations.map((item) => <li key={item}>{item}</li>)}</ul>}
          </details>
        </>
      )}
    </article>
  );
}

function AdvisorySkeleton() {
  return (
    <div className="flex flex-col gap-4" role="status" aria-live="polite">
      <span className="sr-only">Preparing market brief…</span>
      <div
        className="card gap-3 bg-[var(--color-accent-50)]"
        data-advisory-skeleton-card
        aria-hidden="true"
      >
        <div className="skeleton h-3 w-40" />
        <div className="skeleton h-6 w-full max-w-3xl" />
        <div className="skeleton h-3 w-2/3 max-w-xl" />
      </div>
      <section className="flex flex-col gap-3" aria-hidden="true">
        <div className="skeleton h-5 w-44" />
        <div className="grid gap-3 md:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="card gap-3" data-advisory-skeleton-card>
              <div className="skeleton h-3 w-28" />
              <div className="skeleton h-5 w-full" />
              <div className="skeleton h-3 w-4/5" />
              <div className="skeleton h-3 w-3/5" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function AdvisoryClient() {
  const { preferences, isHydrated, setProvince } = usePreferences();
  const province = preferences.province;
  const [result, setResult] = useState<{ province: string; data: AdvisoryResponse } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    if (!province) return;
    let cancelled = false;
    getAdvisories(province).then((data) => !cancelled && setResult({ province, data })).catch(() => !cancelled && setFailed(province));
    return () => { cancelled = true; };
  }, [province]);

  if (!isHydrated) return null;
  const data = result?.province === province ? result.data : null;
  const top = data?.advisories.slice(0, 3) ?? [];
  return (
    <div className="page-container-full flex flex-col gap-4">
      <div className="page-head">
        <div><h1>Market Advisory</h1><p>Market intelligence based on AgriWise demand, supply, price, opportunity, and market-location data.</p></div>
        <ProvinceSelect value={province} onChange={setProvince} />
      </div>
      {!province && <p className="state">Select a province to view market advisories.</p>}
      {province && !data && failed !== province && <AdvisorySkeleton />}
      {failed === province && <p className="state state-error">Couldn&apos;t load the market advisory.</p>}
      {data && <>
        <section className="card bg-[var(--color-accent-50)] flex flex-col gap-2">
          <span className="card-kicker">Market brief · {data.period ?? "latest available period"}</span>
          <h2 className="text-xl font-semibold">{data.market_brief.OPPORTUNITY} potential opportunities, {data.market_brief.RISK} risk watches, and {data.market_brief.MARKET_WATCH} market watches in {data.province}</h2>
          <p className="text-sm text-muted">Signals are decision support, not guarantees of demand, price, or profit.</p>
        </section>
        <section className="flex flex-col gap-3"><h2 className="text-lg font-semibold">Top market signals</h2><div className="grid gap-3 md:grid-cols-3">{top.map((item) => <AdvisoryCard key={item.commodity} advisory={item} compact />)}</div></section>
        <section className="flex flex-col gap-3"><h2 className="text-lg font-semibold">Latest market advisories</h2>{data.advisories.map((item) => <AdvisoryCard key={item.commodity} advisory={item} />)}</section>
        {data.advisories.some((item) => item.markets.length) && <section className="card"><h2 className="text-lg font-semibold">Relevant markets</h2><p className="text-sm text-muted">Potential market access points ranked from the province centre; distances are straight-line estimates, not buyer demand or travel time.</p><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{data.advisories.flatMap((item) => item.markets.slice(0, 1).map((market) => <div key={`${item.commodity}-${market.market_id}`} className="rounded border border-line p-3"><span className="card-kicker">{item.commodity}</span><div className="font-medium">{market.market_name}</div><div className="text-sm text-muted">{market.municipality} · {market.distance_km} km from province centre</div></div>))}</div></section>}
      </>}
    </div>
  );
}
