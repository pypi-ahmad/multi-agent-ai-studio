"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type AgentItem = {
  id: string;
  name: string;
  description: string;
  is_template: boolean;
  updated_at: string;
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<AgentItem[]>({ path: "/agents", token });
      setAgents(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createAgent = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/agents",
        method: "POST",
        token,
        body: {
          name: name.trim(),
          description: description.trim(),
          config: {
            tools: ["filesystem.read", "rag.retrieve", "chat.stream"],
            memory: { enabled: true, scope: "project" },
          },
          is_template: false,
        },
      });
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const deleteAgent = async (id: string) => {
    setBusy(true);
    try {
      const token = getStoredToken();
      await apiRequest({ path: `/agents/${id}`, method: "DELETE", token });
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const publishTemplate = async (id: string) => {
    setBusy(true);
    try {
      const token = getStoredToken();
      await apiRequest({
        path: "/marketplace/templates/publish",
        method: "POST",
        token,
        body: { agent_id: id },
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageFrame title="Agent Builder" description="Create specialized agents with prompts, tools, memory, and model policies.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 space-y-3">
        <p className="text-sm font-semibold">Create Agent</p>
        <input
          className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
          placeholder="Agent name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <textarea
          className="w-full rounded border border-border bg-background px-3 py-2 text-sm min-h-24"
          placeholder="Role and behavior"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <button
          type="button"
          onClick={createAgent}
          disabled={busy || !name.trim()}
          className="rounded bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Create
        </button>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Agents</p>
        <div className="mt-3 space-y-2">
          {agents.map((agent) => (
            <div key={agent.id} className="rounded border border-border px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{agent.name}</p>
                  <p className="text-xs text-foreground/70">{agent.description || "No description"}</p>
                  <p className="text-xs text-foreground/60">{new Date(agent.updated_at).toLocaleString()}</p>
                </div>
                <div className="flex gap-2">
                  {!agent.is_template ? (
                    <button
                      type="button"
                      onClick={() => publishTemplate(agent.id)}
                      className="rounded border border-border px-2 py-1 text-xs"
                    >
                      Publish
                    </button>
                  ) : (
                    <span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">Template</span>
                  )}
                  <button
                    type="button"
                    onClick={() => deleteAgent(agent.id)}
                    className="rounded border border-red-500/40 px-2 py-1 text-xs text-red-300"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {!agents.length ? <p className="text-foreground/70">No agents yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
