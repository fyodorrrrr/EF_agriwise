"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CommoditySelect } from "@/components/filters/CommoditySelect";
import { ProvinceSelect } from "@/components/filters/ProvinceSelect";
import { rankMarkets } from "@/lib/markets";
import { usePreferences } from "@/lib/preferences";
import type { MarketRankingResponse, RankedMarket } from "@/types/markets";

type Status = "idle" | "loading" | "ready" | "error";

const CONFIDENCE_BADGE: Record<string, string> = {
  HIGH: "badge badge-leaf",
  MEDIUM: "badge badge-info",
  LOW: "badge badge-warn",
  NEEDS_VERIFICATION: "badge badge-neutral",
};

export function MarketsClient() {
  const { preferences, isHydrated, setCommodity, setProvince } = usePreferences();
  const { commodity, province } = preferences;
  const key = commodity && province ? `${commodity}|${province}` : null;

  const [result, setResult] = useState<{ key: string; data: MarketRankingResponse } | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    if (!key || !commodity || !province) return;
    let cancelled = false;
    rankMarkets(commodity, province)
      .then((data) => !cancelled && setResult({ key, data }))
      .catch(() => !cancelled && setErrorKey(key));
    return () => {
      cancelled = true;
    };
  }, [key, commodity, province]);

  const status: Status = !key
    ? "idle"
    : errorKey === key
      ? "error"
      : result?.key === key
        ? "ready"
        : "loading";
  const data = result?.key === key ? result.data : null;

  if (!isHydrated) return null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Curated Markets</h1>
          <p>
            Public markets ranked for a commodity and province. Straight-line distance is
            not travel time, and market type is not measured buyer demand.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <CommoditySelect value={commodity} onChange={setCommodity} />
          <ProvinceSelect value={province} onChange={setProvince} />
        </div>
      </div>

      {!key && <p className="state">Pick a commodity and province to see ranked markets.</p>}
      {status === "loading" && <p className="state state-loading">Ranking markets…</p>}
      {status === "error" && (
        <p className="state state-error">Couldn&apos;t reach the markets service.</p>
      )}

      {status === "ready" && data && (
        <>
          <p className="text-xs text-muted">
            {data.supported_analytics}/3 analytics components available for {data.commodity} —
            they feed the &ldquo;analytics support&rdquo; factor below.
          </p>

          {data.ranked.length === 0 ? (
            <p className="state state-empty">
              No curated market with verified coordinates in {data.province} yet.
            </p>
          ) : (
            data.ranked.map((r) => <MarketCard key={r.market.market_id} ranked={r} />)
          )}

          <ul className="card text-xs text-muted list-disc pl-5">
            {data.policy.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function MarketCard({ ranked }: { ranked: RankedMarket }) {
  const { market } = ranked;
  return (
    <div className="card flex flex-col gap-2">
      <div className="card-head">
        <div>
          <div className="card-title">{market.market_name}</div>
          <p className="text-xs text-muted">
            {market.municipality}, {market.province}
            {market.market_type ? ` · ${market.market_type}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold">{ranked.score}</span>
          <span className={CONFIDENCE_BADGE[market.coordinate_confidence] ?? "badge badge-neutral"}>
            {market.coordinate_confidence.replaceAll("_", " ").toLowerCase()}
          </span>
        </div>
      </div>

      <p className="text-xs text-muted">
        {ranked.distance_km} km from the province centre · {ranked.why}
      </p>

      <details className="text-xs">
        <summary className="cursor-pointer text-[var(--color-accent-600)]">
          Why recommended?
        </summary>
        <div className="-mx-1 mt-1 overflow-x-auto px-1">
          <table className="w-full min-w-[14rem]">
            <tbody>
              {Object.entries(ranked.breakdown).map(([factor, entry]) => (
                <tr key={factor}>
                  <td className="py-0.5">{factor.replaceAll("_", " ")}</td>
                  <td className="text-right">{(entry.weight * 100).toFixed(0)}%</td>
                  <td className="text-right">{(entry.score * 100).toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <div className="card-foot flex flex-wrap gap-2 text-xs">
        <Link
          href={`/mapping?market=${encodeURIComponent(market.market_id)}`}
          className="btn btn-ghost btn-sm"
        >
          View on map
        </Link>
        <Link
          href={`/chat?about=${encodeURIComponent(market.market_name)}`}
          className="btn btn-ghost btn-sm"
        >
          Ask AgriWise
        </Link>
        {market.source_url && (
          <a
            href={market.source_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost btn-sm"
          >
            Source
          </a>
        )}
      </div>
    </div>
  );
}
