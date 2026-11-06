import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Dashboard } from './dashboard';
import { AuthProvider } from '@/components/auth/auth-provider';

global.fetch = vi.fn();

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <AuthProvider>{ui}</AuthProvider>
    </QueryClientProvider>,
  );
};

const mockAuth = () => {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.includes('/auth/me')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          id: '1',
          email: 'test@example.com',
          role: 'engineer',
        }),
      } as Response);
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        natural_gas_price_usd_per_mmbtu: 3.25,
        syngas_price_usd_per_kmol: 4.1,
        carbon_credit_price_usd_per_tonne_co2e: 28.5,
        currency: 'USD',
        source: 'mock-fixture-v1',
        is_mock: true,
        as_of: '2026-11-04T12:00:00Z',
        cached: false,
        cache_ttl_seconds: 86400,
      }),
    } as Response);
  });
};

describe('Dashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockAuth();
  });

  it('renders all main sections', async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('1. Reactor Conditions')).toBeInTheDocument();
    });
    expect(screen.getByText('2. Financial Assumptions')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Screening/i })).toBeInTheDocument();
    expect(screen.getByText(/Enter plant conditions/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('MOCK DATA')).toBeInTheDocument();
    });
  });

  it('submits the form and renders results', async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('1. Reactor Conditions')).toBeInTheDocument();
    });

    // Override the fetch mock to add the /tea response
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: '1',
            email: 'test@example.com',
            role: 'engineer',
          }),
        } as Response);
      }
      if (url.includes('/tea')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            predictions: { ch4_conversion: 0.85, syngas_yield_mol_per_mol_ch4: 2.41 },
            model_versions: { ch4_conversion: 'v1', syngas_yield_mol_per_mol_ch4: 'v1' },
            financials: {
              syngas_kmol_per_day: 100,
              syngas_nm3_per_day: 100,
              syngas_revenue_usd_per_day: 100,
              co2_consumed_tonnes_per_day: 10,
              carbon_credit_value_usd_per_day: 100,
              total_revenue_usd_per_day: 200,
              feed_cost_usd_per_day: 50,
              opex_usd_per_day: 10,
              net_cash_flow_usd_per_day: 140,
              annual_net_cash_flow_usd: 46200,
              roi_pct: 15,
              payback_years: 2.0,
              currency: 'USD',
            },
            warnings: ['carbon_credit_not_included'],
          }),
        } as Response);
      }
      // market-prices
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          natural_gas_price_usd_per_mmbtu: 3.25,
          syngas_price_usd_per_kmol: 4.1,
          carbon_credit_price_usd_per_tonne_co2e: 28.5,
          currency: 'USD',
          source: 'mock-fixture-v1',
          is_mock: true,
          as_of: '2026-11-04T12:00:00Z',
          cached: false,
          cache_ttl_seconds: 86400,
        }),
      } as Response);
    });

    fireEvent.click(screen.getByRole('button', { name: /Run Screening/i }));

    await waitFor(() => {
      expect(screen.getByText('85.00%')).toBeInTheDocument();
      expect(screen.getByText('15.00%')).toBeInTheDocument();
    });
  });
});