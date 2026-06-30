"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type ModelProfile = {
  model_name: string;
  capabilities: string[];
  context_length: number;
  score: number;
};

type Snapshot = {
  count: number;
  models: ModelProfile[];
  last_refresh: string | null;
  custom_rules?: Record<string, string>;
};

const tasks = ["reasoning", "coding", "ocr", "embedding", "translation", "summarization", "vision", "chat"];

export default function ModelsPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [selectedTask, setSelectedTask] = useState("chat");
  const [selectedModel, setSelectedModel] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<Snapshot>({ path: "/models/snapshot", token });
      setSnapshot(data);
      if (!selectedModel && data.models.length) {
        setSelectedModel(data.models[0].model_name);
      }
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const refresh = async () => {
    try {
      const token = getStoredToken();
      await apiRequest({ path: "/models/refresh", method: "POST", token, body: {} });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const setRule = async () => {
    if (!selectedTask || !selectedModel) return;
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/models/routing-rules",
        method: "POST",
        token,
        body: { task: selectedTask, model_name: selectedModel },
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const clearRule = async () => {
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/models/routing-rules",
        method: "DELETE",
        token,
        body: { task: selectedTask },
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Model Manager" description="Dynamic model discovery, routing rules, and capability snapshots.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <p className="font-semibold">Router Controls</p>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={refresh} className="rounded bg-accent px-3 py-2 text-white">Refresh Models</button>
          <select className="rounded border border-border bg-background px-3 py-2" value={selectedTask} onChange={(e) => setSelectedTask(e.target.value)}>
            {tasks.map((task) => (
              <option key={task} value={task}>{task}</option>
            ))}
          </select>
          <select className="rounded border border-border bg-background px-3 py-2" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
            {(snapshot?.models ?? []).map((model) => (
              <option key={model.model_name} value={model.model_name}>{model.model_name}</option>
            ))}
          </select>
          <button type="button" onClick={setRule} className="rounded border border-border px-3 py-2">Set Rule</button>
          <button type="button" onClick={clearRule} className="rounded border border-border px-3 py-2">Clear Rule</button>
        </div>
        <p className="text-xs text-foreground/70">Discovered models: {snapshot?.count ?? 0} · Last refresh: {snapshot?.last_refresh ?? "n/a"}</p>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Custom Rules</p>
        <pre className="mt-2 overflow-auto rounded border border-border bg-background p-3 text-xs">{JSON.stringify(snapshot?.custom_rules ?? {}, null, 2)}</pre>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Models</p>
        <div className="mt-3 space-y-2">
          {(snapshot?.models ?? []).map((model) => (
            <div key={model.model_name} className="rounded border border-border px-3 py-2">
              <p className="font-medium">{model.model_name}</p>
              <p className="text-xs text-foreground/70">Capabilities: {model.capabilities.join(", ")}</p>
              <p className="text-xs text-foreground/70">Context: {model.context_length} · Score: {model.score.toFixed(3)}</p>
            </div>
          ))}
          {!snapshot?.models.length ? <p className="text-foreground/70">No models discovered yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
