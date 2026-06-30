"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type ConnectorResponse = {
  connectors: Array<{
    name: string;
    route: string;
    formats?: string[];
    options?: Record<string, unknown>;
  }>;
};

type DocumentItem = {
  id: string;
  name: string;
  status: string;
  source_uri: string;
};

export default function KnowledgePage() {
  const [connectors, setConnectors] = useState<ConnectorResponse["connectors"]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = getStoredToken();
        const [connectorData, documentData] = await Promise.all([
          apiRequest<ConnectorResponse>({ path: "/rag/connectors", token }),
          apiRequest<DocumentItem[]>({ path: "/rag/documents", token }),
        ]);
        setConnectors(connectorData.connectors);
        setDocuments(documentData);
      } catch (err) {
        setError((err as Error).message);
      }
    };
    void load();
  }, []);

  return (
    <PageFrame title="Knowledge Base" description="Connector catalog and indexed source documents for retrieval.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="font-semibold">Available Connectors</p>
          <div className="mt-3 space-y-2">
            {connectors.map((connector) => (
              <div key={connector.name} className="rounded border border-border px-3 py-2">
                <p className="font-medium">{connector.name}</p>
                <p className="text-xs text-foreground/70">{connector.route}</p>
              </div>
            ))}
            {!connectors.length ? <p className="text-foreground/70">No connectors available.</p> : null}
          </div>
        </article>

        <article className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="font-semibold">Indexed Documents</p>
          <div className="mt-3 space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="rounded border border-border px-3 py-2">
                <p className="font-medium">{doc.name}</p>
                <p className="text-xs text-foreground/70">{doc.status} · {doc.source_uri}</p>
              </div>
            ))}
            {!documents.length ? <p className="text-foreground/70">No indexed documents.</p> : null}
          </div>
        </article>
      </section>
    </PageFrame>
  );
}
