"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type DocumentItem = {
  id: string;
  name: string;
  mime_type: string;
  source_uri: string;
  status: string;
  updated_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const token = getStoredToken();
      const docs = await apiRequest<DocumentItem[]>({ path: "/rag/documents", token });
      setDocuments(docs);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const ingest = async () => {
    if (!files.length) return;
    setBusy(true);
    try {
      const token = getStoredToken();
      for (const file of files) {
        const doc = await apiRequest<DocumentItem>({
          path: "/rag/documents",
          method: "POST",
          token,
          body: {
            name: file.name,
            mime_type: file.type || "application/octet-stream",
            source_uri: `local://${file.name}`,
            metadata: { upload: true },
          },
        });

        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${API_BASE}/rag/documents/${doc.id}/ingest`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
        if (!response.ok) {
          throw new Error(`Ingest failed ${response.status}: ${await response.text()}`);
        }
      }
      setFiles([]);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageFrame title="Documents" description="Upload and ingest files into RAG knowledge base.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <input type="file" multiple onChange={(event) => setFiles(Array.from(event.target.files ?? []))} />
        <button
          type="button"
          onClick={ingest}
          disabled={busy || !files.length}
          className="rounded bg-accent px-3 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Ingesting..." : "Ingest Selected Files"}
        </button>
        <p className="text-xs text-foreground/70">{files.length} file(s) selected</p>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Documents</p>
        <div className="mt-3 space-y-2">
          {documents.map((doc) => (
            <div key={doc.id} className="rounded border border-border px-3 py-2">
              <p className="font-medium">{doc.name}</p>
              <p className="text-xs text-foreground/70">{doc.mime_type} · {doc.status}</p>
              <p className="text-xs text-foreground/70">{new Date(doc.updated_at).toLocaleString()}</p>
            </div>
          ))}
          {!documents.length ? <p className="text-foreground/70">No documents yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
