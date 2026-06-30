"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type MemoryItem = {
  id: string;
  memory_type: string;
  scope: string;
  content: string;
  salience: number;
  ttl_days: number;
  updated_at: string;
};

const memoryTypes = ["short_term", "long_term", "semantic", "episodic", "conversation", "project", "agent"];

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [content, setContent] = useState("");
  const [scope, setScope] = useState("project");
  const [memoryType, setMemoryType] = useState("project");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<MemoryItem[]>({ path: "/memory?limit=100", token });
      setItems(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createMemory = async () => {
    if (!content.trim()) return;
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/memory",
        method: "POST",
        token,
        body: {
          memory_type: memoryType,
          scope,
          content: content.trim(),
          salience: 0.6,
          ttl_days: 90,
          metadata: {},
        },
      });
      setContent("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const summarize = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<{ summary: string }>({
        path: "/memory/summary",
        method: "POST",
        token,
        body: { scope, memory_type: memoryType, limit: 40 },
      });
      setSummary(data.summary);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const forget = async () => {
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/memory/forget",
        method: "POST",
        token,
        body: { scope, memory_type: memoryType, min_salience: 0.4 },
      });
      await load();
      setSummary("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const remove = async (id: string) => {
    try {
      const token = getStoredToken();
      await apiRequest({ path: `/memory/${id}`, method: "DELETE", token });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Memory Explorer" description="Inspect, summarize, edit lifecycle, and forget agent memory.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 space-y-3 text-sm">
        <p className="font-semibold">New Memory</p>
        <div className="grid gap-2 md:grid-cols-2">
          <input
            className="rounded border border-border bg-background px-3 py-2"
            value={scope}
            onChange={(event) => setScope(event.target.value)}
            placeholder="scope"
          />
          <select
            className="rounded border border-border bg-background px-3 py-2"
            value={memoryType}
            onChange={(event) => setMemoryType(event.target.value)}
          >
            {memoryTypes.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
        <textarea
          className="w-full min-h-24 rounded border border-border bg-background px-3 py-2"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Memory content"
        />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={createMemory} className="rounded bg-accent px-3 py-2 text-white">Save</button>
          <button type="button" onClick={summarize} className="rounded border border-border px-3 py-2">Summarize</button>
          <button type="button" onClick={forget} className="rounded border border-red-500/40 px-3 py-2 text-red-300">Forget low-salience</button>
        </div>
      </article>

      {summary ? (
        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="font-semibold">Summary</p>
          <p className="mt-2 whitespace-pre-wrap text-foreground/80">{summary}</p>
        </article>
      ) : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Memory Records</p>
        <div className="mt-3 space-y-2">
          {items.map((item) => (
            <div key={item.id} className="rounded border border-border px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs text-foreground/70">{item.memory_type} · {item.scope} · salience {item.salience.toFixed(2)} · ttl {item.ttl_days}d</p>
                  <p className="mt-1 whitespace-pre-wrap">{item.content}</p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(item.id)}
                  className="rounded border border-red-500/40 px-2 py-1 text-xs text-red-300"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {!items.length ? <p className="text-foreground/70">No memory records.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
