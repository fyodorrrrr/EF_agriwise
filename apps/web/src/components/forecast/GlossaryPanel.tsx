import { METRIC_INFO, NO_SUPPLY_DEMAND_RATIO } from "@/components/forecast/glossary";

const BANDS: { classification: string; label: string; meaning: string }[] = [
  {
    classification: "HIGH_OPPORTUNITY",
    label: "High opportunity",
    meaning:
      "Compared to the other CALABARZON provinces, conditions here look the most favorable right now.",
  },
  {
    classification: "UNDERSUPPLY_LEANING",
    label: "Undersupply leaning",
    meaning: "This crop may be scarcer here than in most other CALABARZON provinces.",
  },
  {
    classification: "BALANCED",
    label: "Balanced",
    meaning: "Signals here are roughly in line with the CALABARZON average.",
  },
  {
    classification: "OVERSUPPLY_LEANING",
    label: "Oversupply leaning",
    meaning: "More of this crop is available here than usual — prices may be softer than normal.",
  },
  {
    classification: "SEVERE_OVERSUPPLY",
    label: "Severe oversupply",
    meaning: "Supply looks well above demand here — expect the softest prices among the five provinces.",
  },
];

export function GlossaryPanel() {
  return (
    <details className="card text-sm">
      <summary className="cursor-pointer card-kicker">What do these numbers mean?</summary>
      <div className="disclosure-body">
        <div>
          <h4>The three metrics</h4>
          <ul>
            {(["demand", "supply", "price"] as const).map((kind) => (
              <li key={kind}>
                <strong>{METRIC_INFO[kind].label}:</strong> {METRIC_INFO[kind].whatItMeans}
                {METRIC_INFO[kind].unitNote ? ` ${METRIC_INFO[kind].unitNote}` : ""}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4>Confidence badges</h4>
          <p>
            Badges like &ldquo;Good Forecast&rdquo;, &ldquo;Planning Estimate&rdquo;, or
            &ldquo;Not Enough Data&rdquo; describe how reliable a number is, not what the
            number itself means.
          </p>
        </div>

        <div>
          <h4>Opportunity score (0–100)</h4>
          <p>
            Not a percentage of anything physical — it&apos;s a ranking of this province
            against the other four CALABARZON provinces on demand, supply, price, and
            forecast reliability, combined into one number. The bands are:
          </p>
          <ul>
            {BANDS.map((b) => (
              <li key={b.classification}>
                <strong>{b.label}:</strong> {b.meaning}
              </li>
            ))}
          </ul>
        </div>

        <p className="disclosure-note">{NO_SUPPLY_DEMAND_RATIO}</p>
      </div>
    </details>
  );
}
