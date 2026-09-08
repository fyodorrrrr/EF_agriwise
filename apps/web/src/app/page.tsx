export default function Home() {
  return (
    <main className="mx-auto flex min-h-full max-w-2xl flex-col justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold">AgriWise</h1>
      <p className="text-slate-600 dark:text-slate-300">
        Province-resolution demand, supply, price, and opportunity analytics for CALABARZON
        agriculture. Scaffold is running — feature routes land per the sprint plan.
      </p>
      <a href="/chat" className="text-emerald-700 underline dark:text-emerald-400">
        Ask AgriWise →
      </a>
    </main>
  );
}
