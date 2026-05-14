const DEFAULT_CORE_SERVICE_URL = "/api/v1";
const DEFAULT_PLANNER_SERVICE_URL = "/planner-api/api/v1";
const DEFAULT_AI_SERVICE_URL = "/ai-api/api/v1";

function normalizeUrl(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

const coreServiceUrl = normalizeUrl(
  import.meta.env.VITE_CORE_SERVICE_URL || DEFAULT_CORE_SERVICE_URL,
);

const plannerServiceUrl = normalizeUrl(
  import.meta.env.VITE_PLANNER_SERVICE_URL || DEFAULT_PLANNER_SERVICE_URL,
);

const aiServiceUrl = normalizeUrl(
  import.meta.env.VITE_AI_SERVICE_URL || DEFAULT_AI_SERVICE_URL,
);

export const appConfig = {
  appTitle: import.meta.env.VITE_APP_TITLE || "Workestrator Frontend",
  coreServiceUrl,
  plannerServiceUrl,
  aiServiceUrl,
} as const;

export const frontendAssumptions = {
  auth:
    "Frontend auth flow now targets token-based login, refresh, and me endpoints under /api/v1/auth/.",
  proxy:
    "Vite proxies /api to core-service, /planner-api to planner-service, and /ai-api to the ai-layer during local development.",
} as const;
