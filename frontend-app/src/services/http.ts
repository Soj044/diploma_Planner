type QueryValue = string | number | boolean | null | undefined;

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

interface JsonClientOptions {
  authHeader?: string | null;
}

function stringifyPayload(payload: unknown): string {
  if (payload === null || payload === undefined) {
    return "";
  }

  if (typeof payload === "string") {
    return payload.trim();
  }

  if (Array.isArray(payload)) {
    return payload.map((item) => stringifyPayload(item)).filter(Boolean).join(", ");
  }

  if (typeof payload === "object") {
    return Object.entries(payload as Record<string, unknown>)
      .map(([key, value]) => `${key}: ${stringifyPayload(value)}`)
      .filter((item) => item !== ": ")
      .join("; ");
  }

  return String(payload);
}

function joinUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

function withQuery(url: string, query: Record<string, QueryValue> | undefined): string {
  if (!query) {
    return url;
  }

  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  const queryString = params.toString();
  return queryString ? `${url}?${queryString}` : url;
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    const detailText = stringifyPayload(detail);
    if (detailText) {
      return detailText;
    }
  }

  const payloadText = stringifyPayload(payload);
  if (payloadText) {
    return payloadText;
  }

  return fallback;
}

async function parsePayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return JSON.parse(text) as unknown;
  }

  return text;
}

export function createJsonClient(baseUrl: string, options: JsonClientOptions = {}) {
  async function request<T>(
    method: string,
    path: string,
    payload?: unknown,
    query?: Record<string, QueryValue>,
  ): Promise<T> {
    const url = withQuery(joinUrl(baseUrl, path), query);
    const headers = new Headers({
      Accept: "application/json",
    });

    if (payload !== undefined) {
      headers.set("Content-Type", "application/json");
    }

    if (options.authHeader) {
      headers.set("Authorization", options.authHeader);
    }

    const response = await fetch(url, {
      method,
      headers,
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });

    const parsedPayload = await parsePayload(response);

    if (!response.ok) {
      throw new ApiError(
        getErrorMessage(parsedPayload, `${method} ${path} failed with status ${response.status}`),
        response.status,
        parsedPayload,
      );
    }

    return parsedPayload as T;
  }

  return {
    get<T>(path: string, query?: Record<string, QueryValue>) {
      return request<T>("GET", path, undefined, query);
    },
    post<T>(path: string, payload: unknown) {
      return request<T>("POST", path, payload);
    },
    put<T>(path: string, payload: unknown) {
      return request<T>("PUT", path, payload);
    },
    patch<T>(path: string, payload: unknown) {
      return request<T>("PATCH", path, payload);
    },
    delete<T>(path: string) {
      return request<T>("DELETE", path);
    },
  };
}

export function describeRequestError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Unexpected request error.";
}
