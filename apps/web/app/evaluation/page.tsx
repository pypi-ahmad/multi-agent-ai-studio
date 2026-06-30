"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type EvalItem = {
  id: string;
  name: string;
  dataset_ref: string;
  metric_scores: Record<string, number>;
  created_at: string;
};

type EvalSummary = {
  count: number;
  avg_score: number;
  best_score: number;
  metrics: Record<string, number>;
  timeline: Array<{
    id: string;
    name: string;
    created_at: string;
    metric_scores: Record<string, number>;
  }>;
};

export default function EvaluationPage() {
  const [evaluations, setEvaluations] = useState<EvalItem[]>([]);
  const [summary, setSummary] = useState<EvalSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const [list, stats] = await Promise.all([
          apiRequest<EvalItem[]>({ path: "/evaluation", token }),
          apiRequest<EvalSummary>({ path: "/evaluation/summary", token }),
        ]);
        setEvaluations(list);
        setSummary(stats);
      } catch (err) {
        setError((err as Error).message);
      }
    };

    void load();
    const interval = setInterval(() => void load(), 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <PageFrame title="Evaluation" description="Quality metrics, groundedness trends, and benchmark history.">
      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="text-foreground/70">Total Evaluations</p>
          <p className="text-2xl font-semibold">{summary?.count ?? 0}</p>
        </article>
        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="text-foreground/70">Average Score</p>
          <p className="text-2xl font-semibold">{summary ? summary.avg_score.toFixed(3) : "--"}</p>
        </article>
        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="text-foreground/70">Best Score</p>
          <p className="text-2xl font-semibold">{summary ? summary.best_score.toFixed(3) : "--"}</p>
        </article>
      </div>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Metric Averages</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {Object.entries(summary?.metrics ?? {}).map(([metric, value]) => (
            <div key={metric} className="flex items-center justify-between rounded border border-border px-3 py-2">
              <span>{metric}</span>
              <span className="font-mono">{value.toFixed(3)}</span>
            </div>
          ))}
          {!Object.keys(summary?.metrics ?? {}).length ? <p className="text-foreground/70">No metric aggregates yet.</p> : null}
        </div>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Evaluation History</p>
        <div className="mt-3 space-y-2">
          {evaluations.map((item) => (
            <div key={item.id} className="rounded border border-border px-3 py-2">
              <p className="font-medium">{item.name}</p>
              <p className="text-xs text-foreground/70">{new Date(item.created_at).toLocaleString()} · {item.dataset_ref}</p>
              <p className="mt-1 text-xs font-mono">{JSON.stringify(item.metric_scores)}</p>
            </div>
          ))}
          {!evaluations.length ? <p className="text-foreground/70">No evaluations yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
