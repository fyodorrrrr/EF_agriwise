export function KpiCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string;
  sublabel?: string;
}) {
  return (
    <div className="card flex flex-col gap-1">
      <span className="card-kicker">{label}</span>
      <span className="text-xl font-bold">{value}</span>
      {sublabel && <span className="text-xs text-muted">{sublabel}</span>}
    </div>
  );
}
