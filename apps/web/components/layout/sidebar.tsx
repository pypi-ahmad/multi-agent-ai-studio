"use client";

import { usePathname } from "next/navigation";

import { routes } from "@/lib/routes";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-72 md:flex-col border-r border-border bg-card/50 backdrop-blur">
      <div className="px-5 py-4 border-b border-border">
        <p className="text-lg font-semibold tracking-tight">Multi-Agent AI Studio</p>
        <p className="text-xs text-foreground/70">Local Agentic Platform</p>
      </div>
      <nav className="overflow-y-auto px-3 py-4 space-y-1">
        {routes.map((route) => {
          const active = pathname === route.path;
          return (
            <a
              key={route.path}
              href={route.path}
              className={`block rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-accent text-white"
                  : "text-foreground/80 hover:bg-foreground/10 hover:text-foreground"
              }`}
            >
              {route.label}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}
