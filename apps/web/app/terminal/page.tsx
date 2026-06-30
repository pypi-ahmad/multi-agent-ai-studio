"use client";

import { useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type CommandResponse = {
  stdout: string;
  stderr: string;
  returncode: number;
};

export default function TerminalPage() {
  const [command, setCommand] = useState("ls -la");
  const [cwd, setCwd] = useState("/home/ahmad/AI/multi-agent-ai-studio");
  const [result, setResult] = useState<CommandResponse | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<CommandResponse>({
        path: "/tools/terminal/exec",
        method: "POST",
        token,
        headers: { "X-Confirm-Token": "CONFIRM-DEVELOPMENT" },
        body: { command, cwd, timeout_seconds: 120 },
      });
      setResult(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Terminal" description="Guarded shell execution with confirmation and audit logging.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <input
          className="w-full rounded border border-border bg-background px-3 py-2 font-mono"
          value={cwd}
          onChange={(event) => setCwd(event.target.value)}
          placeholder="cwd"
        />
        <textarea
          className="w-full min-h-24 rounded border border-border bg-background px-3 py-2 font-mono"
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="command"
        />
        <button type="button" onClick={run} className="rounded bg-accent px-4 py-2 text-white">Run</button>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Result</p>
        <p className="mt-2 text-xs text-foreground/70">returncode: {result?.returncode ?? "--"}</p>
        <p className="mt-2 text-xs font-semibold">stdout</p>
        <pre className="max-h-64 overflow-auto rounded border border-border bg-background p-3 text-xs">{result?.stdout ?? ""}</pre>
        <p className="mt-2 text-xs font-semibold">stderr</p>
        <pre className="max-h-64 overflow-auto rounded border border-border bg-background p-3 text-xs">{result?.stderr ?? ""}</pre>
      </article>
    </PageFrame>
  );
}
