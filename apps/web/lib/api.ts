const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const ACCESS_TOKEN_KEY = "studio_access_token";
const REFRESH_TOKEN_KEY = "studio_refresh_token";
const USER_KEY = "studio_current_user";

let refreshPromise: Promise<string | null> | null = null;

export type ApiRequest = {
  path: string;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
  headers?: Record<string, string>;
  skipAuthRefresh?: boolean;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getStoredAccessToken(): string {
  if (!isBrowser()) return "";
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
}

export function getStoredRefreshToken(): string {
  if (!isBrowser()) return "";
  return window.localStorage.getItem(REFRESH_TOKEN_KEY) ?? "";
}

export function getStoredUser(): CurrentUser | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

export function storeAuthTokens(tokens: AuthTokens): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function storeCurrentUser(user: CurrentUser): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredAuth(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

async function doFetch(path: string, method: NonNullable<ApiRequest["method"]>, body: unknown, token: string, headers: Record<string, string>) {
  return fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    cache: "no-store",
  });
}

async function refreshAccessToken(): Promise<string | null> {
  if (!isBrowser()) return null;
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
          cache: "no-store",
        });
        if (!response.ok) {
          clearStoredAuth();
          return null;
        }
        const tokens = (await response.json()) as AuthTokens;
        storeAuthTokens(tokens);
        return tokens.access_token;
      } catch {
        clearStoredAuth();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }

  return refreshPromise;
}

export async function apiRequest<T>({
  path,
  method = "GET",
  body,
  token,
  headers = {},
  skipAuthRefresh = false,
}: ApiRequest): Promise<T> {
  const initialToken = token ?? getStoredAccessToken();
  let response = await doFetch(path, method, body, initialToken, headers);

  if (response.status === 401 && !skipAuthRefresh && path !== "/auth/refresh") {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      response = await doFetch(path, method, body, refreshedToken, headers);
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAuth();
    }
    const errorText = await response.text();
    throw new Error(`API ${response.status}: ${errorText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getStoredToken(): string {
  return getStoredAccessToken();
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const user = await apiRequest<CurrentUser>({ path: "/auth/me" });
  storeCurrentUser(user);
  return user;
}

export async function logout(): Promise<void> {
  const refreshToken = getStoredRefreshToken();
  const accessToken = getStoredAccessToken();
  if (refreshToken && accessToken) {
    try {
      await apiRequest({
        path: "/auth/logout",
        method: "POST",
        token: accessToken,
        skipAuthRefresh: true,
        body: { refresh_token: refreshToken },
      });
    } catch {
      // Best effort logout. Local state still cleared.
    }
  }
  clearStoredAuth();
}

export async function ensureSession(): Promise<CurrentUser | null> {
  const accessToken = getStoredAccessToken();
  const refreshToken = getStoredRefreshToken();
  if (!accessToken && !refreshToken) return null;

  try {
    return await getCurrentUser();
  } catch {
    return null;
  }
}
