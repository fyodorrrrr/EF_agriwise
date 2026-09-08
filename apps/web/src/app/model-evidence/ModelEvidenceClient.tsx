"use client";

import { useEffect, useState } from "react";

import { verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { getEvidence } from "@/lib/forecast";
import { COMMODITIES } from "@/lib/domain";
import type { EvidenceComponent } from "@/types/forecast";

type Status = "loading" | "ready" | "error";

const COMPONENT_ORDER = ["demand", "supply", "price"] as const;

function num(value: number): string {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(3);
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
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Model Evidence</h1>
          <p>
            How each forecast component was validated. Demand for Tomato and Red Onion is
            the same shared vegetable-expenditure proxy.
          </p>
        </div>
      </div>

      {status === "loading" && <p className="state state-loading">Loading evidence…</p>}
      {status === "error" && (
        <p className="state state-error">Couldn&apos;t reach the forecast service.</p>
      )}

      {status === "ready" &&
        COMMODITIES.map((commodity) => (
          <div key={commodity} className="card flex flex-col gap-3">
            <div className="card-title">{commodity}</div>
            <div className="grid gap-3 md:grid-cols-3">
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
            <table className="w-full">
              <tbody>
                {metrics.map(([k, v]) => (
                  <tr key={k}>
                    <td className="text-muted">{k}</td>
                    <td className="text-right">{num(v)}</td>
                    {c.baseline[k] !== undefined && (
                      <td className="text-right text-muted">naïve {num(c.baseline[k])}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {c.province_holdout.length > 0 && (
            <details>
              <summary className="cursor-pointer text-[var(--color-accent-600)]">
                Province hold-out
              </summary>
              <table className="mt-1 block w-full overflow-x-auto">
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
      <dt className="text-muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
