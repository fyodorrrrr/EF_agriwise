import type { OpportunityComponent, OutlookComponent } from "@/types/forecast";
import {
  NO_SUPPLY_DEMAND_RATIO,
  OPPORTUNITY_SCORE_EXPLAINER,
  VERDICT_MEANING,
  classificationMeaning,
  confidenceLabel,
} from "@/components/forecast/glossary";
import { verdictLabel } from "@/components/forecast/verdict";

function coverage(component: OutlookComponent): string | null {
  const obs = component.observed ?? [];
  if (!obs.length) return null;
  const start = obs[0].period;
  const end = obs[obs.length - 1].period;
  const horizon = component.forecast?.length ?? 0;
  return `${start} → ${end} observed${horizon ? `, +${horizon} forecast period(s)` : ""}`;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex justify-between gap-4 py-0.5">
      <dt className="shrink-0 text-muted">{label}</dt>
      <dd className="min-w-0 text-right [overflow-wrap:anywhere]">{value}</dd>
    </div>
  );
}

export function WhyThisResult({
  kind,
  component,
  disclaimer,
}: {
  kind: "demand" | "supply" | "price" | "opportunity";
  component: OutlookComponent | OpportunityComponent;
  disclaimer: string;
}) {
  const isOutlook = "unit" in component;

  return (
    <details className="text-xs">
      <summary className="cursor-pointer text-[var(--color-accent-600)]">
        Why this result?
      </summary>
      <dl className="mt-2 flex flex-col gap-0.5 border-l-2 border-[var(--color-divider)] pl-3">
        <Row label="Verdict" value={verdictLabel(component.verdict)} />
        <Row label="What that means" value={VERDICT_MEANING[component.verdict]} />
        {isOutlook && kind === "demand" && (
          <Row
            label="Is this a percentage?"
            value="No — it's an index where about 100 is a typical level, not a percent and not metric tons."
          />
        )}
        {isOutlook && (
          <>
            <Row
              label="How it was produced"
              value={
                (component as OutlookComponent).source?.startsWith("learned_model")
                  ? "learned model that earned the verdict"
                  : (component as OutlookComponent).source === "seasonal_naive"
                    ? "seasonal-naive fallback (no deployable model)"
                    : (component as OutlookComponent).source === "demand_pressure_index"
                      ? "a demand-pressure index built from national household spending and employment survey data, plus seasonal patterns"
                      : (component as OutlookComponent).source
              }
            />
            <Row
              label="Confidence"
              value={confidenceLabel((component as OutlookComponent).confidence)}
            />
            <Row label="Frequency" value={(component as OutlookComponent).frequency} />
            <Row label="Data coverage" value={coverage(component as OutlookComponent)} />
            <Row
              label="Latest input date"
              value={(component as OutlookComponent).data_as_of}
            />
          </>
        )}
        {!isOutlook && (
          <>
            <Row
              label="Method"
              value="peer-relative rank of this province against the other four, weighted per config"
            />
            <Row
              label="Shared quarter"
              value={(component as OpportunityComponent).shared_quarter}
            />
            <Row label="What the score means" value={OPPORTUNITY_SCORE_EXPLAINER} />
            <Row
              label="What this band means"
              value={classificationMeaning((component as OpportunityComponent).classification)}
            />
            <Row label="Why not a supply/demand ratio?" value={NO_SUPPLY_DEMAND_RATIO} />
          </>
        )}
        <Row label="Province resolution" value="province (not municipality)" />
        {isOutlook && (component as OutlookComponent).limitations.length > 0 && (
          <div className="pt-1">
            <dt className="text-muted">Limitations</dt>
            <ul className="list-disc pl-4">
              {(component as OutlookComponent).limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="pt-1 text-muted">{disclaimer}</p>
        <p className="text-muted">
          This is {kind === "opportunity" ? "a decision-support association" : "a proxy estimate"},
          not a causal finding. No confidence interval is published.
        </p>
      </dl>
    </details>
  );
}
