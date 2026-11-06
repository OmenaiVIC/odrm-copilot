import type { ChatResponse, MarketPricesResponse, TeaRequest, TeaResponse } from './types';

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

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
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
  return apiFetch<MarketPricesResponse>('/market-prices', {
    method: 'GET',
  });
}

export interface ReportDownload {
  blob: Blob;
  filename: string;
  reportId: string | null;
  sha256: string | null;
  generatedAt: string | null;
}

const DEFAULT_REPORT_FILENAME = 'odrm-esg-report.pdf';

function reportFilename(disposition: string | null): string {
  if (!disposition) {
    return DEFAULT_REPORT_FILENAME;
  }
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match ? match[1] : DEFAULT_REPORT_FILENAME;
}

export async function downloadReport(
  request: TeaRequest,
): Promise<ReportDownload> {
  const url = `${API_BASE_URL.replace(/\/$/, "")}/report`;
  const response = await fetch(url, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ApiError(
      response.status,
      `API request failed (${response.status} ${response.statusText})`,
      detail,
    );
  }

  return {
    blob: await response.blob(),
    filename: reportFilename(response.headers.get('Content-Disposition')),
    reportId: response.headers.get('X-Report-Id'),
    sha256: response.headers.get('X-Report-SHA256'),
    generatedAt: response.headers.get('X-Report-Generated-At'),
  };
}

export async function postTea(request: TeaRequest): Promise<TeaResponse> {
  return apiFetch<TeaResponse>('/tea', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function postChat(message: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}
