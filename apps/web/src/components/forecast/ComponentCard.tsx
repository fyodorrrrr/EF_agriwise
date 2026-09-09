import type { OutlookComponent } from "@/types/forecast";
import { Sparkline } from "@/components/forecast/Sparkline";
import { formatValue, verdictBadgeClass, verdictLabel } from "@/components/forecast/verdict";
import { METRIC_INFO, confidenceLabel } from "@/components/forecast/glossary";

function latest(component: OutlookComponent): number | null {
  const series = component.forecast?.length
    ? component.forecast
    : component.observed?.length
      ? component.observed
      : null;
  return series ? series[series.length - 1].value : null;
}

export function ComponentCard({
  kind,
  component,
  detailed = false,
}: {
  kind: "demand" | "supply" | "price";
  component: OutlookComponent;
  detailed?: boolean;
}) {
  const insufficient = component.verdict === "INSUFFICIENT_DATA";
  const value = latest(component);
  const info = METRIC_INFO[kind];

  return (
    <div className="card flex flex-col gap-2">
      <div className="card-head">
        <div>
          <span className="card-kicker">{info.label}</span>
          {detailed && component.label && (
            <p className="text-xs text-muted">{component.label}</p>
          )}
        </div>
        <span className={verdictBadgeClass(component.verdict)}>
          {verdictLabel(component.verdict)}
        </span>
      </div>

      {insufficient ? (
        <p className="state">
          No forecast is published for this component — critical inputs are missing.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-x-3 gap-y-2">
            <div className="min-w-0">
              <div className="text-xl font-bold">
                {value === null ? "—" : formatValue(value, component.unit)}
              </div>
              <p className="text-xs text-muted">
                {component.forecast?.length ? "forecast" : "latest observed"}
                {component.frequency ? ` · ${component.frequency}` : ""}
              </p>
            </div>
            <Sparkline observed={component.observed} forecast={component.forecast} />
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted">
            {component.confidence && (
              <>
                <dt>Confidence</dt>
                <dd className="text-right">{confidenceLabel(component.confidence)}</dd>
              </>
            )}
            {component.source && (
              <>
                <dt>Source</dt>
                <dd className="text-right break-all">{component.source}</dd>
              </>
            )}
            {component.data_as_of && (
              <>
                <dt>Data as of</dt>
                <dd className="text-right">{component.data_as_of}</dd>
              </>
            )}
          </dl>

          {detailed && component.limitations.length > 0 && (
            <ul className="card-foot text-xs text-muted list-disc pl-4">
              {component.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
