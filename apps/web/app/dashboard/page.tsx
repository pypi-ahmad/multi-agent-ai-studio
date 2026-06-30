"use client";

import { useEffect, useMemo, useState } from "react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type RunItem = {
  id: string;
  status: string;
};

type EvalSummary = {
  count: number;
  avg_score: number;
  metrics: Record<string, number>;
};

type TraceItem = {
  id: string;
  run_id: string;
  span_count: number;
  metadata?: {
    timeline?: Array<{ stage: string; latency_ms: number }>;
  };
};

type MetricPoint = {
  recorded_at: string;
  gpu_used_mb: number;
  gpu_total_mb: number;
  gpu_utilization_percent: number;
};

type TimeseriesResponse = {
  count: number;
  series: MetricPoint[];
};

function Sparkline({ values, colorClass }: { values: number[]; colorClass: string }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-20 items-end gap-1">
      {values.map((value, index) => (
        <div
          key={`${value}-${index}`}
          className={`${colorClass} min-w-1 flex-1 rounded-sm opacity-80`}
          style={{ height: `${Math.max((value / max) * 100, 4)}%` }}
        />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [summary, setSummary] = useState<EvalSummary | null>(null);
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [timeseries, setTimeseries] = useState<TimeseriesResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const [runsData, evalData, traceData, metricData] = await Promise.all([
          apiRequest<RunItem[]>({ path: "/runs", token }),
          apiRequest<EvalSummary>({ path: "/evaluation/summary", token }),
          apiRequest<TraceItem[]>({ path: "/traces", token }),
          apiRequest<TimeseriesResponse>({ path: "/system/metrics/timeseries?minutes=60", token }),
        ]);
        setRuns(runsData);
        setSummary(evalData);
        setTraces(traceData);
        setTimeseries(metricData);
      } catch (err) {
        setError((err as Error).message);
      }
    };

    void load();
    const interval = setInterval(() => void load(), 10000);
    return () => clearInterval(interval);
  }, []);

  const activeRuns = useMemo(
    () => runs.filter((run) => run.status === "running" || run.status === "queued").length,
    [runs],
  );

  const avgLatencyMs = useMemo(() => {
    const latencies = traces.flatMap((trace) => (trace.metadata?.timeline ?? []).map((item) => Number(item.latency_ms || 0)));
    if (!latencies.length) return 0;
    return latencies.reduce((sum, value) => sum + value, 0) / latencies.length;
  }, [traces]);

  const latestPoint = timeseries?.series.at(-1);
  const gpuSeries = (timeseries?.series ?? []).slice(-40).map((point) => point.gpu_utilization_percent);
  const vramSeries = (timeseries?.series ?? []).slice(-40).map((point) => point.gpu_used_mb);

  return (
    <PageFrame title="Dashboard" description="System-wide execution status, model telemetry, and quality signals.">
      {error ? <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Active Runs" value={String(activeRuns)} hint="Queued and running orchestration jobs" />
        <MetricCard title="Avg Latency" value={avgLatencyMs ? `${avgLatencyMs.toFixed(1)} ms` : "--"} hint="Stage-level trace latency" />
        <MetricCard
          title="GPU VRAM"
          value={latestPoint ? `${latestPoint.gpu_used_mb} / ${latestPoint.gpu_total_mb} MB` : "--"}
          hint="Live sampled from system telemetry"
        />
        <MetricCard title="Eval Score" value={summary ? summary.avg_score.toFixed(3) : "--"} hint="Average score across evaluation history" />
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-4">
          <p className="text-sm font-semibold">GPU Utilization (60m)</p>
          {gpuSeries.length ? <Sparkline values={gpuSeries} colorClass="bg-emerald-400" /> : <p className="text-sm text-foreground/70">No samples yet.</p>}
        </article>
        <article className="rounded-xl border border-border bg-card p-4">
          <p className="text-sm font-semibold">VRAM Usage MB (60m)</p>
          {vramSeries.length ? <Sparkline values={vramSeries} colorClass="bg-sky-400" /> : <p className="text-sm text-foreground/70">No samples yet.</p>}
        </article>
      </section>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Recent Traces</p>
        <div className="mt-3 space-y-2">
          {traces.slice(0, 6).map((trace) => (
            <div key={trace.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
              <p className="font-mono text-xs">{trace.id.slice(0, 8)} · run {trace.run_id.slice(0, 8)}</p>
              <p className="text-xs text-foreground/70">spans: {trace.span_count}</p>
            </div>
          ))}
          {!traces.length ? <p className="text-foreground/70">No traces recorded yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
