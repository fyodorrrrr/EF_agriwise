export interface RankBarRow {
  key: string;
  label: string;
  value: number;
  detail?: string;
}

/**
 * A horizontal ranked bar list. Reused for the Dashboard's opportunity
 * ranking strip and Forecasting's opportunity-factor breakdown, so both
 * pages show "how do these compare" as a bar instead of a raw number table.
 */
export function OpportunityRankBar({ rows }: { rows: RankBarRow[] }) {
  return (
    <div className="flex flex-col gap-3">
      {rows.map((row) => (
        <div key={row.key}>
          <div className="meter-row">
            <span className="font-medium">{row.label}</span>
            {row.detail && <span className="text-muted">{row.detail}</span>}
          </div>
          <div className="meter">
            <span style={{ width: `${Math.max(0, Math.min(100, row.value))}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
