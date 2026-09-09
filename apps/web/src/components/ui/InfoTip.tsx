export function InfoTip({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <details className="info-tip">
      <summary aria-label={label} />
      <div className="info-tip-panel">{children}</div>
    </details>
  );
}
