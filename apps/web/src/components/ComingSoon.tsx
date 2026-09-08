export function ComingSoon({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-3 p-8">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-slate-600 dark:text-slate-300">{description}</p>
      <p className="text-sm text-slate-400">Coming soon.</p>
    </div>
  );
}
