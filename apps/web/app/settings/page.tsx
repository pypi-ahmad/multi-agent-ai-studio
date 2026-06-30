"use client";

import { useEffect, useState } from "react";

import { PageFrame } from "@/components/ui/page-frame";
import { apiRequest, getStoredToken } from "@/lib/api";

type SettingItem = {
  id: string;
  key: string;
  value: Record<string, unknown>;
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingItem[]>([]);
  const [keyInput, setKeyInput] = useState("ui.preferences");
  const [valueInput, setValueInput] = useState('{"theme":"dark"}');
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const token = getStoredToken();
      const data = await apiRequest<SettingItem[]>({ path: "/settings", token });
      setSettings(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const upsert = async () => {
    try {
      const parsed = JSON.parse(valueInput) as Record<string, unknown>;
      const token = getStoredToken();
      await apiRequest({ path: `/settings/${encodeURIComponent(keyInput)}`, method: "PUT", token, body: { value: parsed } });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <PageFrame title="Settings" description="Persisted user settings and platform preferences.">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}

      <article className="rounded-xl border border-border bg-card p-4 text-sm space-y-3">
        <p className="font-semibold">Upsert Setting</p>
        <input
          className="w-full rounded border border-border bg-background px-3 py-2"
          value={keyInput}
          onChange={(event) => setKeyInput(event.target.value)}
          placeholder="settings key"
        />
        <textarea
          className="w-full min-h-32 rounded border border-border bg-background px-3 py-2 font-mono text-xs"
          value={valueInput}
          onChange={(event) => setValueInput(event.target.value)}
        />
        <button type="button" onClick={upsert} className="rounded bg-accent px-3 py-2 text-white">Save</button>
      </article>

      <article className="rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-semibold">Current Settings</p>
        <div className="mt-3 space-y-2">
          {settings.map((item) => (
            <div key={item.id} className="rounded border border-border px-3 py-2">
              <p className="font-medium">{item.key}</p>
              <pre className="mt-1 overflow-auto text-xs text-foreground/80">{JSON.stringify(item.value, null, 2)}</pre>
            </div>
          ))}
          {!settings.length ? <p className="text-foreground/70">No settings found.</p> : null}
        </div>
      </article>
    </PageFrame>
  );
}
