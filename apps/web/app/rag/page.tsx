"use client";

import { useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type RetrievalHit = {
  document_id: string;
  chunk_id: string;
  score: number;
  text: string;
  highlights: string[];
  metadata: Record<string, unknown>;
};

type RetrievalResponse = {
  query: string;
  mode: string;
  hits: RetrievalHit[];
};

export default function RagPage() {
  const [query, setQuery] = useState("summarize current architecture");
  const [mode, setMode] = useState("hybrid");
  const [hits, setHits] = useState<RetrievalHit[]>([]);
  const [error, setError] = useState("");

  const retrieve = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<RetrievalResponse>({
        path: "/rag/retrieve",
        method: "POST",
        token,
        body: {
          query,
          top_k: 8,
          mode,
          rerank: true,
          candidate_pool: 40,
          filters: {},
        },
      });
      setHits(data.hits);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="RAG" description="Hybrid retrieval with reranking, filters, and citation-ready chunks.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border border-border bg-background px-3 py-2"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Query"
          />
          <select className="rounded border border-border bg-background px-3 py-2" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="hybrid">hybrid</option>
            <option value="semantic">semantic</option>
            <option value="keyword">keyword</option>
          </select>
          <button type="button" onClick={retrieve} className="rounded bg-accent px-4 py-2 text-white">Retrieve</button>
        </div>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Results</p>
        <div className="mt-3 space-y-2">
          {hits.map((hit) => (
            <div key={hit.chunk_id} className="rounded border border-border px-3 py-2">
              <p className="text-xs text-foreground/70">score {hit.score.toFixed(4)} · doc {hit.document_id}</p>
              <p className="mt-1 whitespace-pre-wrap text-sm">{hit.text}</p>
            </div>
          ))}
          {!hits.length ? <p className="text-foreground/70">No retrieval results yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
