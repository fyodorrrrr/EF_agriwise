"use client";

import { useEffect, useState } from "react";

import { BrandLoader } from "@/components/BrandLoader";
import { verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { getEvidence } from "@/lib/forecast";
import { COMMODITIES } from "@/lib/domain";
import type { EvidenceComponent } from "@/types/forecast";

type Status = "loading" | "ready" | "error";

const COMPONENT_ORDER = ["demand", "supply", "price"] as const;

const METRIC_LABELS: Record<string, string> = {
  r2: "R² (fit quality)",
  mae: "MAE (avg error)",
  mse: "MSE (squared error)",
  rmse: "RMSE (typical error)",
  mape: "MAPE (% error)",
  smape: "sMAPE (% error)",
  wape: "WAPE (% error)",
  mase: "MASE (vs. naïve)",
  bias: "Bias",
  normalized_mae_percent: "Normalized MAE (%)",
  aggregate_bias_percent: "Aggregate bias (%)",
};

// Everything except r2 is an error/bias metric where smaller (closer to zero) wins.
const HIGHER_IS_BETTER = new Set(["r2"]);

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key;
}

function num(value: number): string {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(3);
}

function isModelBetter(key: string, modelValue: number, baselineValue: number): boolean {
  if (HIGHER_IS_BETTER.has(key)) return modelValue >= baselineValue;
  return Math.abs(modelValue) <= Math.abs(baselineValue);
}

function barWidth(value: number, other: number): number {
  const max = Math.max(Math.abs(value), Math.abs(other), 1e-9);
  return Math.max(0, Math.min(100, (Math.abs(value) / max) * 100));
}

export function ModelEvidenceClient() {
  const [components, setComponents] = useState<EvidenceComponent[]>([]);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    let cancelled = false;
    getEvidence()
      .then((res) => {
        if (cancelled) return;
        setComponents(res.components);
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, []);

  const byKey = new Map(components.map((c) => [`${c.commodity}|${c.component}`, c]));

  return (
    <div className="page-container-wide flex flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Model Evidence</h1>
          <p>
            How each forecast component was validated. Demand for Tomato and Red Onion is
            the same shared vegetable-expenditure proxy.
          </p>
        </div>
      </div>

      {status === "loading" && <BrandLoader label="Loading evidence…" />}
      {status === "error" && (
        <p className="state state-error">Couldn&apos;t reach the forecast service.</p>
      )}

      {status === "ready" &&
        COMMODITIES.map((commodity) => (
          <div key={commodity} className="card flex flex-col gap-3">
            <div className="card-title">{commodity}</div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {COMPONENT_ORDER.map((component) => {
                const c = byKey.get(`${commodity}|${component}`);
                if (!c) return null;
                return <EvidenceCard key={component} evidence={c} />;
              })}
            </div>
          </div>
        ))}
    </div>
  );
}

function EvidenceCard({ evidence: c }: { evidence: EvidenceComponent }) {
  const unavailable = c.verdict === "INSUFFICIENT_DATA";
  const metrics = Object.entries(c.metrics);
  return (
    <div className="flex flex-col gap-2 border-t border-[var(--color-divider)] pt-2 text-xs">
      <div className="flex items-center justify-between">
        <span className="card-kicker">{c.component}</span>
        <span className={verdictBadgeClass(c.verdict)}>{verdictLabel(c.verdict)}</span>
      </div>

      <dl className="flex flex-col gap-0.5">
        <Row label="Target" value={c.target} />
        <Row label="Model" value={c.model ?? "unavailable"} />
        <Row label="Reason" value={c.reason} />
        <Row label="Frequency" value={c.frequency} />
        <Row label="Province resolution" value={c.province_resolution} />
        <Row label="Source" value={c.source} />
        <Row label="Artifact schema" value={c.schema_version} />
      </dl>

      {unavailable ? (
        <p className="text-muted">Metrics unavailable — no deployable model.</p>
      ) : (
        <>
          {metrics.length > 0 && (
            <div className="flex flex-col gap-2">
              {metrics.map(([k, v]) => {
                const baselineValue = c.baseline[k];
                if (baselineValue === undefined) {
                  return (
                    <div key={k} className="flex justify-between gap-3">
                      <span className="text-muted">{metricLabel(k)}</span>
                      <span>{num(v)}</span>
                    </div>
                  );
                }
                const modelWins = isModelBetter(k, v, baselineValue);
                return (
                  <div key={k}>
                    <div className="meter-row">
                      <span className="font-medium">{metricLabel(k)}</span>
                      <span className={modelWins ? "text-[var(--color-leaf-700)]" : "text-muted"}>
                        {num(v)} vs naïve {num(baselineValue)}
                      </span>
                    </div>
                    <div className="meter">
                      <span
                        style={{
                          width: `${barWidth(v, baselineValue)}%`,
                          background: modelWins
                            ? "var(--color-leaf-500)"
                            : "var(--color-neutral-400)",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {c.province_holdout.length > 0 && (
            <details>
              <summary className="cursor-pointer text-[var(--color-accent-600)]">
                Province hold-out
              </summary>
              <div className="table-wrap mt-1">
                <table className="table">
                  <thead>
                    <tr>
                      {Object.keys(c.province_holdout[0]).map((k) => (
                        <th key={k}>{metricLabel(k)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {c.province_holdout.map((row, i) => (
                      <tr key={i}>
                        {Object.entries(row).map(([k, v]) => (
                          <td key={k} className="text-right">
                            {typeof v === "number" ? num(v) : String(v)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </>
      )}

      {c.limitations.length > 0 && (
        <ul className="list-disc pl-4 text-muted">
          {c.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex justify-between gap-3">
      <dt className="shrink-0 text-muted">{label}</dt>
      <dd className="min-w-0 text-right [overflow-wrap:anywhere]">{value}</dd>
    </div>
  );
}
