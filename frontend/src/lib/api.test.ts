import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getMarketPrices, postTea, ApiError } from './api';

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

    const payload = { conditions: {}, assumptions: {} } as any;
    
    await expect(postTea(payload)).rejects.toThrow(ApiError);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/tea'),
      expect.objectContaining({ 
        method: 'POST',
        body: JSON.stringify(payload)
      })
    );
  });
});