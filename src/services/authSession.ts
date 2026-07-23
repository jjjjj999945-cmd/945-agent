import type { User } from "../types/domain";
import type { ApiResponse } from "./apiTypes";

const API_BASE_URL = import.meta.env.VITE_945_API_BASE_URL ?? "http://127.0.0.1:8000";
const TOKEN_KEY = "945.auth.token";
const USER_KEY = "945.auth.user_id";

export type AuthSession = { access_token: string; token_type: "bearer"; user: User };

export function getAccessToken() { return window.localStorage.getItem(TOKEN_KEY); }
export function hasSession() { return Boolean(getAccessToken()); }
export function saveSession(session: AuthSession) {
  window.localStorage.setItem(TOKEN_KEY, session.access_token);
  window.localStorage.setItem(USER_KEY, session.user.user_id);
}
export function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
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
  me() {
    const token = getAccessToken();
    return authRequest<User>("/api/auth/me", { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  }
};
