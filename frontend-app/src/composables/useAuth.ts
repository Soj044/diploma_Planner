import { computed } from "vue";

import {
  bootstrapAuth,
  getAuthState,
  hasRole,
  isAuthenticated,
  login,
  logout,
  refreshAccessToken,
  signup,
} from "../services/auth-service";

const state = getAuthState();

export function useAuth() {
  return {
    state,
    user: computed(() => state.user),
    role: computed(() => state.user?.role ?? null),
    employeeId: computed(() => state.user?.employee_id ?? null),
    isAuthenticated: computed(() => isAuthenticated()),
    isBootstrapping: computed(() => state.isBootstrapping),
    canAccess: (roles: string[]) => hasRole(roles),
    bootstrapAuth,
    refreshAccessToken,
    login,
    signup,
    logout,
  };
}
