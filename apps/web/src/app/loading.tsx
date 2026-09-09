// Route-level fallback shown during navigation between pages.
export default function Loading() {
  return (
    <div className="brand-loader" role="status" aria-live="polite">
      <img src="/brand/agriwise-mark.png" alt="" aria-hidden="true" />
      <span>Loading…</span>
    </div>
  );
}
