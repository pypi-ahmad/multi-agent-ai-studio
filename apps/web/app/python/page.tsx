"use client";

import { useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type PythonResponse = {
  stdout: string;
  stderr: string;
  returncode: number;
};

export default function PythonPage() {
  const [code, setCode] = useState("import sys\nprint(sys.version)");
  const [result, setResult] = useState<PythonResponse | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<PythonResponse>({
        path: "/tools/python/exec",
        method: "POST",
        token,
        headers: { "X-Confirm-Token": "CONFIRM-DEVELOPMENT" },
        body: { code, timeout_seconds: 120 },
      });
      setResult(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Python Workspace" description="Sandboxed Python execution with bounded runtime and audit trail.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <textarea
          className="w-full min-h-52 rounded border border-border bg-background p-3 font-mono text-xs"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
        <button type="button" onClick={run} className="rounded bg-accent px-4 py-2 text-white">Run Python</button>
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
