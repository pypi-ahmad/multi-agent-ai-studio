"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type TemplateItem = {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  config: Record<string, unknown>;
  updated_at: string;
};

export default function MarketplacePage() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<TemplateItem[]>({ path: "/marketplace/templates", token });
      setTemplates(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const importTemplate = async (templateId: string, name: string) => {
    try {
      const token = getStoredToken();
      await apiRequest({
        path: `/marketplace/templates/${templateId}/import`,
        method: "POST",
        token,
        body: { name: `${name} Copy` },
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Agent Marketplace" description="Template catalog for reusable agent blueprints.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Published Templates</p>
        <div className="mt-3 space-y-2">
          {templates.map((template) => (
            <div key={template.id} className="rounded border border-border px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{template.name}</p>
                  <p className="text-xs text-foreground/70">{template.description || "No description"}</p>
                  <p className="text-xs text-foreground/60">{new Date(template.updated_at).toLocaleString()}</p>
                </div>
                <button
                  type="button"
                  onClick={() => importTemplate(template.id, template.name)}
                  className="rounded bg-accent px-3 py-2 text-xs text-white"
                >
                  Import
                </button>
              </div>
            </div>
          ))}
          {!templates.length ? <p className="text-foreground/70">No templates published yet.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
