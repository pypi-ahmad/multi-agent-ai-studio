"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CurrentUser, getCurrentUser, getStoredUser, logout } from "@/lib/api";

export function Topbar() {
  const router = useRouter();
  const [dark, setDark] = useState(true);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const saved = window.localStorage.getItem("studio_theme");
    if (saved === "light") {
      root.classList.remove("dark");
      setDark(false);
    } else {
      root.classList.add("dark");
      setDark(true);
    }

    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    const cached = getStoredUser();
    if (cached) {
      setUser(cached);
    }
    const load = async () => {
      try {
        const current = await getCurrentUser();
        setUser(current);
      } catch {
        setUser(cached);
      }
    };
    void load();
  }, []);

  const toggleTheme = () => {
    const root = document.documentElement;
    if (dark) {
      root.classList.remove("dark");
      window.localStorage.setItem("studio_theme", "light");
      setDark(false);
    } else {
      root.classList.add("dark");
      window.localStorage.setItem("studio_theme", "dark");
      setDark(true);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <header className="h-16 border-b border-border bg-card/60 backdrop-blur px-6 flex items-center justify-between">
      <div>
        <p className="text-sm text-foreground/70">Privacy-first local orchestration</p>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden md:block text-right">
          <p className="text-xs font-medium">{user?.full_name || user?.email || "Unknown User"}</p>
          <p className="text-[11px] text-foreground/60 uppercase">{user?.role || "viewer"}</p>
        </div>
        <button
          type="button"
          onClick={() => setPaletteOpen((value) => !value)}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          ⌘/Ctrl + K
        </button>
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          {dark ? "Light" : "Dark"}
        </button>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          Logout
        </button>
      </div>
      {paletteOpen ? (
        <div className="absolute right-6 top-16 mt-2 w-80 rounded-lg border border-border bg-card p-4 shadow-xl">
          <p className="text-sm font-medium">Command Palette</p>
          <p className="text-xs text-foreground/70 mt-2">
            Use sidebar routes for navigation. This shortcut toggles quick command panel.
          </p>
        </div>
      ) : null}
    </header>
  );
}
