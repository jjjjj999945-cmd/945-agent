import type { User } from "../types/domain";
import type { ApiResponse } from "./apiTypes";

const API_BASE_URL = import.meta.env.VITE_945_API_BASE_URL ?? "http://127.0.0.1:8000";
const TOKEN_KEY = "945.auth.token";
const USER_KEY = "945.auth.user_id";
let accessToken: string | null = null;
let currentUserId: string | null = null;
let refreshRequest: Promise<ApiResponse<AuthSession>> | null = null;

export type AuthSession = { access_token: string; session_id: string; token_type: "bearer"; user: User };

export function getAccessToken() { return accessToken; }
export function getCurrentUserId(fallbackUserId: string) {
  if (import.meta.env.VITE_945_AUTH_ENABLED === "false") return fallbackUserId;
  return currentUserId ?? fallbackUserId;
}
export function saveCurrentUserId(userId: string) {
  currentUserId = userId;
}
export function hasSession() { return Boolean(getAccessToken()); }
export function saveSession(session: AuthSession) {
  accessToken = session.access_token;
  currentUserId = session.user.user_id;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}
export function clearSession() {
  accessToken = null;
  currentUserId = null;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers }
    });
    return await response.json() as ApiResponse<T>;
  } catch (cause) {
    return { data: null, error: { code: "NETWORK_ERROR", message: "Unable to reach 945 backend.", details: { cause: String(cause) } } };
  }
}

export const authApi = {
  register(input: { display_name: string; email: string; password: string }) {
    return authRequest<AuthSession>("/api/auth/register", { method: "POST", body: JSON.stringify(input) });
  },
  login(input: { email: string; password: string }) {
    return authRequest<AuthSession>("/api/auth/login", { method: "POST", body: JSON.stringify(input) });
  },
  refresh() {
    if (refreshRequest) return refreshRequest;
    refreshRequest = authRequest<AuthSession>("/api/auth/refresh", { method: "POST" })
      .finally(() => { refreshRequest = null; });
    return refreshRequest;
  },
  me() {
    const token = getAccessToken();
    return authRequest<User>("/api/auth/me", { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  },
  changePassword(input: { current_password: string; new_password: string }) {
    const token = getAccessToken();
    return authRequest<{ changed: true }>("/api/auth/change-password", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: JSON.stringify(input)
    });
  },
  logout() {
    const token = getAccessToken();
    return authRequest<{ logged_out: true }>("/api/auth/logout", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
  }
};
