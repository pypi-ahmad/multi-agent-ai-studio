"use client";

import { useEffect, useMemo, useState } from "react";

import { apiRequest, getStoredToken } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type StageEvent = {
  stage: string;
  status: string;
  latency_ms?: number;
  model?: string;
};

export function ChatPanel() {
  const [chatId, setChatId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [stageEvents, setStageEvents] = useState<StageEvent[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const init = async () => {
      try {
        const token = getStoredToken();
        const chat = await apiRequest<{ id: string }>({ path: "/chat", method: "POST", body: { title: "Studio Chat" }, token });
        setChatId(chat.id);
      } catch {
        setChatId("");
      }
    };
    void init();
  }, []);

  const canSend = useMemo(() => Boolean(chatId && prompt.trim()), [chatId, prompt]);

  const send = async () => {
    if (!canSend) return;

    const token = getStoredToken();
    const userText = prompt.trim();
    setMessages((prev) => [...prev, { role: "user", content: userText }, { role: "assistant", content: "" }]);
    setPrompt("");
    setStageEvents([]);
    setError("");
    setStreaming(true);

    const url = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/chat/${chatId}/stream?prompt=${encodeURIComponent(userText)}`;
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      setStreaming(false);
      setError(`Stream failed: ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) {
      setStreaming(false);
      return;
    }

    let done = false;
    let buffer = "";
    while (!done) {
      const result = await reader.read();
      done = result.done;
      buffer += decoder.decode(result.value || new Uint8Array(), { stream: !done });

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        if (!frame.trim()) continue;
        const lines = frame.split("\n");
        let eventType = "message";
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventType = line.replace("event:", "").trim();
          }
          if (line.startsWith("data:")) {
            dataLines.push(line.replace("data:", ""));
          }
        }

        const rawData = dataLines.join("\n");
        if (!rawData) continue;

        if (eventType === "stage") {
          try {
            const parsed = JSON.parse(rawData) as StageEvent;
            setStageEvents((prev) => {
              const next = [...prev, parsed];
              return next.slice(-8);
            });
          } catch {
            // Ignore malformed stage event
          }
          continue;
        }

        if (eventType === "error") {
          try {
            const parsed = JSON.parse(rawData) as { error?: string };
            setError(parsed.error ?? "Unknown stream error");
          } catch {
            setError(rawData);
          }
          continue;
        }

        if (eventType === "end" && rawData === "done") {
          continue;
        }

        if (eventType === "meta") {
          continue;
        }

        const text = rawData.replace(/\\n/g, "\n");
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant") {
            last.content += text;
          }
          return copy;
        });
      }
    }

    setStreaming(false);
  };

  return (
    <section className="grid lg:grid-cols-[1fr,320px] gap-4">
      <article className="rounded-xl border border-border bg-card p-4 space-y-3 min-h-[560px]">
        {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p> : null}
        <div className="space-y-3 max-h-[460px] overflow-auto">
          {messages.map((message, idx) => (
            <div key={`${message.role}-${idx}`} className={`rounded-lg p-3 ${message.role === "user" ? "bg-accent text-white" : "bg-foreground/10"}`}>
              <p className="text-xs uppercase opacity-70">{message.role}</p>
              <p className="text-sm whitespace-pre-wrap">{message.content || (streaming ? "Streaming..." : "")}</p>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            className="min-h-24 flex-1 rounded-lg border border-border bg-background p-3 text-sm"
            placeholder="Ask supervisor to orchestrate agents..."
          />
          <button
            type="button"
            onClick={send}
            disabled={!canSend || streaming}
            className="h-fit rounded-lg bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </article>

      <aside className="rounded-xl border border-border bg-card p-4 space-y-2">
        <p className="text-sm font-semibold">Live Run Timeline</p>
        <ul className="space-y-2 text-xs text-foreground/80">
          {stageEvents.map((event, index) => (
            <li key={`${event.stage}-${index}`}>
              {index + 1}. {event.stage} · {event.status}
              {event.model ? ` · ${event.model}` : ""}
              {event.latency_ms ? ` · ${event.latency_ms} ms` : ""}
            </li>
          ))}
          {!stageEvents.length ? <li>Waiting for orchestration events...</li> : null}
        </ul>
      </aside>
    </section>
  );
}
