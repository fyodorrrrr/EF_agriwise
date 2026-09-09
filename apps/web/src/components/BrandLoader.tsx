/** Full-section loading state — the AgriWise leaf, breathing, centred in its container. */
export function BrandLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="brand-loader" role="status" aria-live="polite">
      {/* eslint-disable-next-line @next/next/no-img-element -- tiny static brand mark; next/image adds no value */}
      <img src="/brand/agriwise-mark.png" alt="" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
