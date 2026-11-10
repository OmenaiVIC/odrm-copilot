import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getMarketPrices, postChat, postTea, downloadReport, ApiError } from './api';

// Mock global fetch
global.fetch = vi.fn();

describe('API Client', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('getMarketPrices calls the correct endpoint', async () => {
    const mockData = { natural_gas_price_usd_per_mmbtu: 3.25 };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    } as Response);

    const result = await getMarketPrices();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/market-prices'),
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual(mockData);
  });

  it('postTea sends the correct payload and throws on error', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: 'Validation Error' }),
    } as Response);

    const payload = {
      conditions: {},
      assumptions: {},
    } as unknown as Parameters<typeof postTea>[0];

    await expect(postTea(payload)).rejects.toThrow(ApiError);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/tea'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
      })
    );
  });

  it('downloadReport posts the payload to the report endpoint', async () => {
    const blob = new Blob(['%PDF-'], { type: 'application/pdf' });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Headers(),
      blob: async () => blob,
    } as Response);

    const payload = {
      conditions: {},
      assumptions: {},
    } as unknown as Parameters<typeof downloadReport>[0];

    const result = await downloadReport(payload);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/report'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
        cache: 'no-store',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
    expect(result.blob).toBe(blob);
    expect(result.filename).toBe('odrm-esg-report.pdf');
    expect(result.reportId).toBeNull();
    expect(result.sha256).toBeNull();
    expect(result.generatedAt).toBeNull();
  });

  it('downloadReport parses filename and compliance headers', async () => {
    const blob = new Blob(['%PDF-'], { type: 'application/pdf' });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Headers({
        'Content-Disposition': 'attachment; filename="odrm-esg-report-abc123.pdf"',
        'X-Report-Id': 'abc123',
        'X-Report-SHA256': 'a'.repeat(64),
        'X-Report-Generated-At': '2026-11-06T12:00:00Z',
      }),
      blob: async () => blob,
    } as Response);

    const result = await downloadReport({} as Parameters<typeof downloadReport>[0]);

    expect(result).toEqual({
      blob,
      filename: 'odrm-esg-report-abc123.pdf',
      reportId: 'abc123',
      sha256: 'a'.repeat(64),
      generatedAt: '2026-11-06T12:00:00Z',
    });
  });

  it('downloadReport falls back to a default filename when the header is malformed', async () => {
    const blob = new Blob(['%PDF-'], { type: 'application/pdf' });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Headers({ 'Content-Disposition': 'inline' }),
      blob: async () => blob,
    } as Response);

    const result = await downloadReport({} as Parameters<typeof downloadReport>[0]);

    expect(result.filename).toBe('odrm-esg-report.pdf');
  });

  it('downloadReport throws ApiError with parsed detail on failure', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({ detail: 'Report generation failed.' }),
    } as Response);

    await expect(
      downloadReport({} as Parameters<typeof downloadReport>[0])
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      detail: { detail: 'Report generation failed.' },
    });
  });

  it('postChat posts the messages and returns the parsed response', async () => {
    const mockResponse = {
      status: 'ok',
      reply: 'Screening complete.',
      result: null,
      request_id: 'req-1',
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    const messages = [
      { role: 'user' as const, content: 'Run the screening.' },
      { role: 'assistant' as const, content: 'The payback is 2 years.' },
      { role: 'user' as const, content: 'Now raise the temperature to 800 C.' },
    ];

    const result = await postChat(messages);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ messages }),
        credentials: 'include',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
    expect(result).toEqual(mockResponse);
  });
});
