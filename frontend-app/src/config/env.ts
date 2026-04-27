const DEFAULT_CORE_SERVICE_URL = "/core-api/api/v1";
const DEFAULT_PLANNER_SERVICE_URL = "/planner-api/api/v1";

function normalizeUrl(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function toBasicAuthHeader(rawValue: string | undefined): string | null {
  if (!rawValue) {
    return null;
  }

  return rawValue.startsWith("Basic ") ? rawValue : `Basic ${btoa(rawValue)}`;
}

const coreServiceUrl = normalizeUrl(
  import.meta.env.VITE_CORE_SERVICE_URL || DEFAULT_CORE_SERVICE_URL,
);

const plannerServiceUrl = normalizeUrl(
  import.meta.env.VITE_PLANNER_SERVICE_URL || DEFAULT_PLANNER_SERVICE_URL,
);

const coreServiceAuthHeader = toBasicAuthHeader(import.meta.env.VITE_CORE_SERVICE_BASIC_AUTH);

export const appConfig = {
  appTitle: import.meta.env.VITE_APP_TITLE || "Workestrator Frontend",
  coreServiceUrl,
  plannerServiceUrl,
  coreServiceAuthHeader,
  hasCoreServiceAuth: Boolean(coreServiceAuthHeader),
} as const;

export const frontendAssumptions = {
  auth:
    "This shell assumes local MVP access through HTTP Basic credentials until a dedicated frontend login flow is added.",
  proxy:
    "Vite proxies /core-api and /planner-api during local development so browser calls do not need backend CORS changes in this slice.",
} as const;
