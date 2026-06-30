"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ensureSession } from "@/lib/api";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

const PUBLIC_ROUTES = new Set(["/login", "/register", "/auth/callback/github"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  const isPublicRoute = useMemo(() => {
    if (!pathname) return false;
    if (PUBLIC_ROUTES.has(pathname)) return true;
    return pathname.startsWith("/auth/callback/");
  }, [pathname]);

  useEffect(() => {
    let active = true;

    const verify = async () => {
      if (isPublicRoute) {
        if (active) setReady(true);
        return;
      }

      const user = await ensureSession();
      if (!active) return;
      if (!user) {
        const next = pathname ? `?next=${encodeURIComponent(pathname)}` : "";
        router.replace(`/login${next}`);
        return;
      }
      setReady(true);
    };

    setReady(false);
    void verify();
    return () => {
      active = false;
    };
  }, [isPublicRoute, pathname, router]);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-sm text-foreground/70">Loading session...</p>
      </div>
    );
  }

  if (isPublicRoute) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
