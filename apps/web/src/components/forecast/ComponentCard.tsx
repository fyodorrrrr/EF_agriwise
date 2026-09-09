import type { OutlookComponent } from "@/types/forecast";
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

/**
 * A compact fact strip above the metric's chart — verdict, one plain-
 * language value, and the confidence/source/data-as-of detail. It no
 * longer carries its own trend line: the big chart directly below shows
 * the same series at real size, so a second mini-chart here would be
 * redundant chrome.
 */
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
    <div className="flex flex-col gap-2">
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
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-xl font-bold">
              {value === null ? "—" : formatValue(value, component.unit)}
            </span>
            <span className="text-xs text-muted">
              {component.forecast?.length ? "forecast" : "latest observed"}
              {component.frequency ? ` · ${component.frequency}` : ""}
            </span>
          </div>

          <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            {component.confidence && (
              <div className="flex gap-1">
                <dt>Confidence:</dt>
                <dd>{confidenceLabel(component.confidence)}</dd>
              </div>
            )}
            {component.source && (
              <div className="flex gap-1">
                <dt>Source:</dt>
                <dd className="break-all">{component.source}</dd>
              </div>
            )}
            {component.data_as_of && (
              <div className="flex gap-1">
                <dt>Data as of:</dt>
                <dd>{component.data_as_of}</dd>
              </div>
            )}
          </dl>

          {detailed && component.limitations.length > 0 && (
            <ul className="text-xs text-muted list-disc pl-4">
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
