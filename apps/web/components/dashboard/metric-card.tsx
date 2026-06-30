type MetricCardProps = {
  title: string;
  value: string;
  hint: string;
};

export function MetricCard({ title, value, hint }: MetricCardProps) {
  return (
    <article className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs uppercase tracking-wider text-foreground/60">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-foreground/70">{hint}</p>
    </article>
  );
}
