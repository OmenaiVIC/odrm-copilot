import type {
  MarketPricesResponse,
  TeaRequest,
  TeaResponse,
  LoginResponse,
  AuthUser,
  ChatMessage,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface ReportDownload {
  blob: Blob;
  filename: string;
  reportId: string | null;
  sha256: string | null;
  generatedAt: string | null;
}

export interface ChatResponse {
  status: "ok" | "needs_input";
  reply: string;
  result: TeaResponse | null;
  request_id: string;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }

    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("odrm:unauthorized"));
    }

    throw new ApiError(
      response.status,
      `API request failed (${response.status} ${response.statusText})`,
      detail,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getMarketPrices(): Promise<MarketPricesResponse> {
  return apiFetch<MarketPricesResponse>("/market-prices", {
    method: "GET",
  });
}

export async function postTea(request: TeaRequest): Promise<TeaResponse> {
  return apiFetch<TeaResponse>("/tea", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function postChat(messages: ChatMessage[]): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}

export async function downloadReport(
  request: TeaRequest,
): Promise<ReportDownload> {
  const url = `${API_BASE_URL.replace(/\/$/, "")}/report`;
  const response = await fetch(url, {
    method: "POST",
    cache: "no-store",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }

    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("odrm:unauthorized"));
    }

    throw new ApiError(
      response.status,
      `API request failed (${response.status} ${response.statusText})`,
      detail,
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? "odrm-esg-report.pdf";

  return {
    blob,
    filename,
    reportId: response.headers.get("x-report-id"),
    sha256: response.headers.get("x-report-sha256"),
    generatedAt: response.headers.get("x-report-generated-at"),
  };
}

export async function postLogin(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/me", {
    method: "GET",
  });
}

export async function postLogout(): Promise<void> {
  return apiFetch<void>("/auth/logout", {
    method: "POST",
  });
}