import { reactive, readonly } from "vue";

import { appConfig } from "../config/env";
import type { AuthResponse, AuthUser, LoginRequest, SignupRequest } from "../types/api";
import { ApiError, createJsonClient } from "./http";

type AuthStatus = "booting" | "authenticated" | "guest";

interface AuthState {
  status: AuthStatus;
  accessToken: string | null;
  user: AuthUser | null;
  isBootstrapping: boolean;
  isRefreshing: boolean;
  bootstrapCompleted: boolean;
  lastError: string;
}

const state = reactive<AuthState>({
  status: "booting",
  accessToken: null,
  user: null,
  isBootstrapping: false,
  isRefreshing: false,
  bootstrapCompleted: false,
  lastError: "",
});

const client = createJsonClient(appConfig.coreServiceUrl, {
  defaultCredentials: "include",
  getAccessToken,
  onUnauthorized: refreshAccessToken,
});

let bootstrapPromise: Promise<void> | null = null;
let refreshPromise: Promise<boolean> | null = null;

function applyAuthPayload(payload: AuthResponse) {
  state.accessToken = payload.access;
  state.user = payload.user;
  state.status = "authenticated";
  state.lastError = "";
}

export function getAccessToken(): string | null {
  return state.accessToken;
}

export function getAuthState() {
  return readonly(state);
}

export function isAuthenticated(): boolean {
  return Boolean(state.accessToken && state.user);
}

export function hasRole(roles: string[]): boolean {
  return Boolean(state.user && roles.includes(state.user.role));
}

export function clearSession() {
  state.accessToken = null;
  state.user = null;
  state.status = "guest";
}

export async function fetchMe(): Promise<AuthUser> {
  const user = await client.get<AuthUser>("/auth/me", undefined, {
    credentials: "include",
  });
  state.user = user;
  state.status = "authenticated";
  return user;
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    state.isRefreshing = true;

    try {
      const payload = await client.post<AuthResponse>(
        "/auth/refresh",
        undefined,
        {
          auth: "none",
          credentials: "include",
          retryOnUnauthorized: false,
        },
      );
      applyAuthPayload(payload);
      return true;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        return false;
      }

      state.lastError = error instanceof Error ? error.message : "Auth refresh failed.";
      clearSession();
      return false;
    } finally {
      state.isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function bootstrapAuth(): Promise<void> {
  if (state.bootstrapCompleted) {
    return;
  }

  if (bootstrapPromise) {
    return bootstrapPromise;
  }

  bootstrapPromise = (async () => {
    state.isBootstrapping = true;
    state.lastError = "";

    try {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        await fetchMe();
      } else {
        clearSession();
      }
    } catch (error: unknown) {
      state.lastError = error instanceof Error ? error.message : "Auth bootstrap failed.";
      clearSession();
    } finally {
      state.bootstrapCompleted = true;
      state.isBootstrapping = false;
      bootstrapPromise = null;
    }
  })();

  return bootstrapPromise;
}

export async function login(payload: LoginRequest): Promise<AuthUser> {
  const response = await client.post<AuthResponse>("/auth/login", payload, {
    auth: "none",
    credentials: "include",
    retryOnUnauthorized: false,
  });
  applyAuthPayload(response);
  return fetchMe();
}

export async function signup(payload: SignupRequest): Promise<AuthUser> {
  const response = await client.post<AuthResponse>("/auth/signup", payload, {
    auth: "none",
    credentials: "include",
    retryOnUnauthorized: false,
  });
  applyAuthPayload(response);
  return fetchMe();
}

export async function logout(): Promise<void> {
  try {
    await client.post<null>("/auth/logout", undefined, {
      auth: "none",
      credentials: "include",
      retryOnUnauthorized: false,
    });
  } finally {
    clearSession();
  }
}
