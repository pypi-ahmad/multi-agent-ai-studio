"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type ExperimentItem = {
  id: string;
  name: string;
  config: Record<string, unknown>;
  results: Record<string, unknown>;
  updated_at: string;
};

export default function ExperimentsPage() {
  const [items, setItems] = useState<ExperimentItem[]>([]);
  const [name, setName] = useState("baseline-eval");
  const [configInput, setConfigInput] = useState('{"dataset":"default","model":"auto"}');
  const [resultsInput, setResultsInput] = useState('{"quality":0.0,"latency_ms":0}');
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<ExperimentItem[]>({ path: "/experiments", token });
      setItems(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const create = async () => {
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/experiments",
        method: "POST",
        token,
        body: {
          name,
          config: JSON.parse(configInput) as Record<string, unknown>,
          results: JSON.parse(resultsInput) as Record<string, unknown>,
        },
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Experiments" description="Track model and agent experiments with configs and results.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <p className="font-semibold">Create Experiment</p>
        <input className="w-full rounded border border-border bg-background px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
        <textarea className="w-full min-h-24 rounded border border-border bg-background px-3 py-2 font-mono text-xs" value={configInput} onChange={(e) => setConfigInput(e.target.value)} />
        <textarea className="w-full min-h-24 rounded border border-border bg-background px-3 py-2 font-mono text-xs" value={resultsInput} onChange={(e) => setResultsInput(e.target.value)} />
        <button type="button" onClick={create} className="rounded bg-accent px-3 py-2 text-white">Create</button>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Experiment History</p>
        <div className="mt-3 space-y-2">
          {items.map((item) => (
            <div key={item.id} className="rounded border border-border px-3 py-2">
              <p className="font-medium">{item.name}</p>
              <p className="text-xs text-foreground/70">{new Date(item.updated_at).toLocaleString()}</p>
              <p className="mt-1 text-xs">config: {JSON.stringify(item.config)}</p>
              <p className="mt-1 text-xs">results: {JSON.stringify(item.results)}</p>
            </div>
          ))}
          {!items.length ? <p className="text-foreground/70">No experiments yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
