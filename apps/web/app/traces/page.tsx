"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type TraceItem = {
  id: string;
  run_id: string;
  run_status: string;
  trace_id: string;
  span_count: number;
  created_at: string;
};

type TraceDetail = {
  id: string;
  trace_id: string;
  run_id: string;
  run_status: string;
  span_count: number;
  metadata: {
    timeline?: Array<{ stage: string; latency_ms: number; model?: string }>;
    prompt_preview?: string;
    response_preview?: string;
  };
  run: {
    input_payload: Record<string, unknown>;
    output_payload: Record<string, unknown>;
    model_usage: Record<string, unknown>;
    error_message: string;
  };
};

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const data = await apiRequest<TraceItem[]>({ path: "/traces", token });
        setTraces(data);
        if (!selected && data.length) {
          setSelected(data[0].id);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    };

    void load();
    const interval = setInterval(() => void load(), 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!selected) return;
    const loadDetail = async () => {
      try {
        const token = getStoredToken();
        const data = await apiRequest<TraceDetail>({ path: `/traces/${selected}`, token });
        setDetail(data);
      } catch (err) {
        setError((err as Error).message);
      }
    };
    void loadDetail();
  }, [selected]);

  return (
    <PageFrame title="Traces" description="Trace list and span-level drill-down for orchestration runs.">
      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      <div className="grid gap-4 lg:grid-cols-[320px,1fr]">
        <aside className="rounded-xl border border-border bg-card p-3 text-sm space-y-2 max-h-[700px] overflow-auto">
          {traces.map((trace) => (
            <button
              key={trace.id}
              type="button"
              className={`w-full rounded border px-3 py-2 text-left ${selected === trace.id ? "border-accent bg-accent/10" : "border-border"}`}
              onClick={() => setSelected(trace.id)}
            >
              <p className="font-mono text-xs">{trace.id.slice(0, 8)} · {trace.run_status}</p>
              <p className="text-xs text-foreground/70">spans {trace.span_count} · {new Date(trace.created_at).toLocaleTimeString()}</p>
            </button>
          ))}
          {!traces.length ? <p className="text-foreground/70">No traces yet.</p> : null}
        </aside>

        <section className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
          {detail ? (
            <>
              <p className="font-semibold">Trace {detail.id}</p>
              <p className="text-xs text-foreground/70">run {detail.run_id} · status {detail.run_status} · spans {detail.span_count}</p>

              <article className="rounded border border-border p-3">
                <p className="font-medium">Timeline</p>
                <div className="mt-2 space-y-2">
                  {(detail.metadata.timeline ?? []).map((item, index) => (
                    <div key={`${item.stage}-${index}`} className="flex items-center justify-between rounded border border-border px-3 py-2">
                      <span>{index + 1}. {item.stage}</span>
                      <span className="font-mono text-xs">{item.model ?? ""} · {item.latency_ms} ms</span>
                    </div>
                  ))}
                  {!detail.metadata.timeline?.length ? <p className="text-foreground/70">No timeline data.</p> : null}
                </div>
              </article>

              <article className="rounded border border-border p-3 space-y-2">
                <p className="font-medium">Prompt Preview</p>
                <p className="whitespace-pre-wrap text-xs text-foreground/80">{detail.metadata.prompt_preview ?? ""}</p>
              </article>

              <article className="rounded border border-border p-3 space-y-2">
                <p className="font-medium">Response Preview</p>
                <p className="whitespace-pre-wrap text-xs text-foreground/80">{detail.metadata.response_preview ?? ""}</p>
              </article>
            </>
          ) : (
            <p className="text-foreground/70">Select a trace to inspect details.</p>
          )}
        </section>
      </div>
    </PageFrame>
  );
}
