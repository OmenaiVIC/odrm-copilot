import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Dashboard } from './dashboard';

global.fetch = vi.fn();

const createTestQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

describe('Dashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders all main sections', async () => {
    // Mock market prices fetch
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({
        natural_gas_price_usd_per_mmbtu: 3.25, syngas_price_usd_per_kmol: 4.10,
        carbon_credit_price_usd_per_tonne_co2e: 28.50, currency: 'USD',
        source: 'mock', is_mock: true, as_of: '', cached: false, cache_ttl_seconds: 86400
      }),
    } as Response);

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <Dashboard />
      </QueryClientProvider>
    );

    expect(screen.getByText('1. Reactor Conditions')).toBeInTheDocument();
    expect(screen.getByText('2. Financial Assumptions')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Screening/i })).toBeInTheDocument();
    expect(screen.getByText(/Enter plant conditions/i)).toBeInTheDocument();
    
    // Wait for market prices to load
    await waitFor(() => {
      expect(screen.getByText('MOCK DATA')).toBeInTheDocument();
    });
  });

  it('submits the form and renders results', async () => {
    // 1. Mock Market fetch
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ natural_gas_price_usd_per_mmbtu: 3, syngas_price_usd_per_kmol: 4, carbon_credit_price_usd_per_tonne_co2e: 25, is_mock: true, source: '', as_of: '', cached: false, cache_ttl_seconds: 0, currency: 'USD' }),
    } as Response);
    
    // 2. Mock TEA POST fetch
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({
        predictions: { ch4_conversion: 0.85, syngas_yield_mol_per_mol_ch4: 2.41 },
        model_versions: { ch4_conversion: 'v1', syngas_yield_mol_per_mol_ch4: 'v1' },
        financials: {
          syngas_kmol_per_day: 100, syngas_nm3_per_day: 100, syngas_revenue_usd_per_day: 100,
          co2_consumed_tonnes_per_day: 10, carbon_credit_value_usd_per_day: 100, total_revenue_usd_per_day: 200,
          feed_cost_usd_per_day: 50, opex_usd_per_day: 10, net_cash_flow_usd_per_day: 140,
          annual_net_cash_flow_usd: 46200, roi_pct: 15, payback_years: 2.0, currency: 'USD',
        },
        warnings: ['carbon_credit_not_included'],
      }),
    } as Response);

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <Dashboard />
      </QueryClientProvider>
    );

    // Click submit
    fireEvent.click(screen.getByRole('button', { name: /Run Screening/i }));

    // Check results appear
    await waitFor(() => {
      expect(screen.getByText('85.00%')).toBeInTheDocument();
      expect(screen.getByText('15.00%')).toBeInTheDocument();
    });
  });
});