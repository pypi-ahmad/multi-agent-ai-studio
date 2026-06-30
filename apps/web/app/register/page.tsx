"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiRequest, getCurrentUser, storeAuthTokens } from "@/lib/api";

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const onRegister = async () => {
    setBusy(true);
    setError("");
    try {
      const tokens = await apiRequest<TokenPair>({
        path: "/auth/register",
        method: "POST",
        body: {
          full_name: fullName,
          email,
          password,
        },
        skipAuthRefresh: true,
      });
      storeAuthTokens(tokens);
      await getCurrentUser();
      router.replace("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="min-h-screen flex items-center justify-center px-4 py-10">
      <article className="w-full max-w-md rounded-2xl border border-border bg-card p-6 space-y-4">
        <header>
          <h1 className="text-xl font-semibold">Create account</h1>
          <p className="text-sm text-foreground/70">Register local studio owner/editor account.</p>
        </header>
        {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}
        <label className="block space-y-1">
          <span className="text-xs text-foreground/70">Full name</span>
          <input
            type="text"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
            placeholder="Ahmad"
          />
        </label>
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
            placeholder="At least 8 characters"
          />
        </label>
        <button
          type="button"
          onClick={onRegister}
          disabled={busy || !email.trim() || !password.trim()}
          className="w-full rounded bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Creating account..." : "Create account"}
        </button>
        <p className="text-xs text-foreground/70">
          Already have account?{" "}
          <Link href="/login" className="text-accent underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </article>
    </section>
  );
}
