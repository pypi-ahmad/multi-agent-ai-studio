"use client";

import { useEffect, useMemo, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type SystemSnapshot = {
  status: string;
  timestamp: string;
  services: Record<string, string>;
  metrics: {
    cpu_percent: number;
    memory_total_mb: number;
    memory_used_mb: number;
    memory_percent: number;
    gpu: {
      available: boolean;
      name: string;
      total_mb: number;
      used_mb: number;
      free_mb: number;
      utilization_percent: number;
      memory_utilization_percent: number;
    };
  };
};

type TimeseriesPoint = {
  recorded_at: string;
  cpu_percent: number;
  gpu_utilization_percent: number;
  gpu_used_mb: number;
  gpu_total_mb: number;
};

type Timeseries = {
  count: number;
  series: TimeseriesPoint[];
};

export default function SystemPage() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null);
  const [series, setSeries] = useState<Timeseries | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const [health, history] = await Promise.all([
          apiRequest<SystemSnapshot>({ path: "/system/health", token }),
          apiRequest<Timeseries>({ path: "/system/metrics/timeseries?minutes=60", token }),
        ]);
        setSnapshot(health);
        setSeries(history);
      } catch (err) {
        setError((err as Error).message);
      }
    };

    void load();
    const interval = setInterval(() => void load(), 5000);
    return () => clearInterval(interval);
  }, []);

  const utilizationAvg = useMemo(() => {
    const values = (series?.series ?? []).map((point) => point.gpu_utilization_percent);
    if (!values.length) return 0;
    return values.reduce((sum, item) => sum + item, 0) / values.length;
  }, [series]);

  return (
    <PageFrame title="System Monitoring" description="Live host telemetry for CPU, memory, GPU, and core services.">
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <div className="grid gap-4 md:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-1">
          <p>Health: {snapshot?.status ?? "--"}</p>
          <p>CPU: {snapshot?.metrics.cpu_percent ?? "--"}%</p>
          <p>
            RAM: {snapshot?.metrics.memory_used_mb ?? "--"} / {snapshot?.metrics.memory_total_mb ?? "--"} MB
          </p>
          <p>RAM Usage: {snapshot?.metrics.memory_percent ?? "--"}%</p>
        </article>
        <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-1">
          <p>GPU Available: {String(snapshot?.metrics.gpu.available ?? false)}</p>
          <p>GPU: {snapshot?.metrics.gpu.name ?? "n/a"}</p>
          <p>
            VRAM Used: {snapshot?.metrics.gpu.used_mb ?? "--"} / {snapshot?.metrics.gpu.total_mb ?? "--"} MB
          </p>
          <p>GPU Utilization: {snapshot?.metrics.gpu.utilization_percent ?? "--"}%</p>
          <p>GPU Memory Utilization: {snapshot?.metrics.gpu.memory_utilization_percent ?? "--"}%</p>
        </article>
      </div>

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-2">
        <p className="font-semibold">Time-Series (last 60m)</p>
        <p>Samples: {series?.count ?? 0}</p>
        <p>Avg GPU Utilization: {utilizationAvg.toFixed(1)}%</p>
        <div className="grid gap-2">
          {(series?.series ?? []).slice(-8).map((point) => (
            <div key={point.recorded_at} className="grid grid-cols-4 gap-2 rounded border border-border px-2 py-1 text-xs">
              <span>{new Date(point.recorded_at).toLocaleTimeString()}</span>
              <span>CPU {point.cpu_percent.toFixed(1)}%</span>
              <span>GPU {point.gpu_utilization_percent.toFixed(1)}%</span>
              <span>
                VRAM {point.gpu_used_mb}/{point.gpu_total_mb} MB
              </span>
            </div>
          ))}
          {!series?.count ? <p className="text-foreground/70">No telemetry points yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
