"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiRequest, getCurrentUser, storeAuthTokens } from "@/lib/api";

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export default function GithubCallbackPage() {
  const router = useRouter();
  const search = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const code = search.get("code");
    if (!code) {
      setError("Missing OAuth code.");
      return;
    }

    const run = async () => {
      try {
        const tokens = await apiRequest<TokenPair>({
          path: `/auth/github/callback?code=${encodeURIComponent(code)}`,
          skipAuthRefresh: true,
        });
        storeAuthTokens(tokens);
        await getCurrentUser();
        if (active) {
          router.replace("/dashboard");
        }
      } catch (err) {
        if (active) {
          setError((err as Error).message);
        }
      }
    };

    void run();
    return () => {
      active = false;
    };
  }, [router, search]);

  return (
    <section className="min-h-screen flex items-center justify-center px-4 py-10">
      <article className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 space-y-3">
        <h1 className="text-lg font-semibold">GitHub authentication</h1>
        {error ? (
          <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>
        ) : (
          <p className="text-sm text-foreground/70">Completing OAuth flow...</p>
        )}
      </article>
    </section>
  );
}
