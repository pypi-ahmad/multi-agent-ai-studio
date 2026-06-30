"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { apiRequest, getCurrentUser, storeAuthTokens } from "@/lib/api";

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export default function LoginPage() {
  const router = useRouter();
  const search = useSearchParams();
  const nextPath = search.get("next") || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const onLogin = async () => {
    setBusy(true);
    setError("");
    try {
      const tokens = await apiRequest<TokenPair>({
        path: "/auth/login",
        method: "POST",
        body: { email, password },
        skipAuthRefresh: true,
      });
      storeAuthTokens(tokens);
      await getCurrentUser();
      router.replace(nextPath);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onGithubOAuth = async () => {
    setError("");
    setBusy(true);
    try {
      const payload = await apiRequest<{ url: string }>({
        path: "/auth/github/authorize",
        skipAuthRefresh: true,
      });
      window.location.href = payload.url;
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <section className="min-h-screen flex items-center justify-center px-4 py-10">
      <article className="w-full max-w-md rounded-2xl border border-border bg-card p-6 space-y-4">
        <header>
          <h1 className="text-xl font-semibold">Sign in</h1>
          <p className="text-sm text-foreground/70">Authenticate to access Multi-Agent AI Studio.</p>
        </header>
        {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}
        <label className="block space-y-1">
          <span className="text-xs text-foreground/70">Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
            placeholder="you@example.com"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-foreground/70">Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
            placeholder="••••••••"
          />
        </label>
        <button
          type="button"
          onClick={onLogin}
          disabled={busy || !email.trim() || !password.trim()}
          className="w-full rounded bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Signing in..." : "Sign in"}
        </button>
        <button
          type="button"
          onClick={onGithubOAuth}
          disabled={busy}
          className="w-full rounded border border-border px-4 py-2 text-sm disabled:opacity-50"
        >
          Continue with GitHub
        </button>
        <p className="text-xs text-foreground/70">
          New user?{" "}
          <Link href="/register" className="text-accent underline underline-offset-2">
            Create account
          </Link>
        </p>
      </article>
    </section>
  );
}
