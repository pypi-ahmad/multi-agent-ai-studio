"use client";

import { useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type ChatResponse = { content: string };

export default function BrowserPage() {
  const [prompt, setPrompt] = useState("Plan browser automation steps to extract pricing tables from target site.");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");

  const run = async () => {
    try {
      const token = getStoredToken();
      const chat = await apiRequest<{ id: string }>({ path: "/chat", method: "POST", token, body: { title: "Browser Workspace" } });
      const response = await apiRequest<ChatResponse>({
        path: `/chat/${chat.id}/messages`,
        method: "POST",
        token,
        body: { content: `Browser Agent Task: ${prompt}`, context: { workspace: "browser" } },
      });
      setAnswer(response.content);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Browser Automation" description="Browser automation planning and extraction workflows.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}
      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <textarea className="w-full min-h-28 rounded border border-border bg-background p-3" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button type="button" onClick={run} className="rounded bg-accent px-4 py-2 text-white">Run Browser Agent</button>
      </article>
      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Output</p>
        <p className="mt-2 whitespace-pre-wrap text-foreground/80">{answer || "No output yet."}</p>
      </article>
    </PageFrame>
  );
}
