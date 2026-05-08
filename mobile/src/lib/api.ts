import { API_BASE_URL } from "./config";
import { getAccessToken, setAccessToken, getRefreshToken, setRefreshToken, clearTokens } from "./auth";

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE" | "PUT";

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  authenticated?: boolean;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return false;

  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${refreshToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    await clearTokens();
    return false;
  }

  const data = await res.json();
  setAccessToken(data.access_token);
  await setRefreshToken(data.refresh_token);
  return true;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, authenticated = true } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authenticated) {
    const accessToken = getAccessToken();
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }
  }

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Auto-refresh on 401 and retry once
  if (res.status === 401 && authenticated) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getAccessToken()}`;
      res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    }
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, error.detail ?? "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth endpoints ─────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    user_id: string;
    email: string;
    display_name: string;
    maturity_stage: string;
  };
}

export const authApi = {
  register: (email: string, password: string, display_name: string) =>
    apiRequest<AuthResponse>("/auth/register", {
      method: "POST",
      body: { email, password, display_name },
      authenticated: false,
    }),

  login: (email: string, password: string) =>
    apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      authenticated: false,
    }),

  logout: async () => {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return;
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${refreshToken}` },
    }).catch(() => {});
    await clearTokens();
  },
};
