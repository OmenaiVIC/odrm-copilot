import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MarketPricePanel } from './market-price-panel';

describe('MarketPricePanel', () => {
  const mockData = {
    natural_gas_price_usd_per_mmbtu: 3.25,
    syngas_price_usd_per_kmol: 4.10,
    carbon_credit_price_usd_per_tonne_co2e: 28.50,
    currency: 'USD',
    source: 'mock-fixture-v1',
    is_mock: true,
    as_of: '2026-11-04T12:00:00Z',
    cached: false,
    cache_ttl_seconds: 86400,
  };

  it('renders the loading state', () => {
    render(<MarketPricePanel isLoading={true} isError={false} onRefresh={vi.fn()} onUseMarketValues={vi.fn()} />);
    expect(screen.getByRole('generic', { busy: true })).toBeInTheDocument();
  });

  it('renders the error state', () => {
    render(<MarketPricePanel isLoading={false} isError={true} onRefresh={vi.fn()} onUseMarketValues={vi.fn()} />);
    expect(screen.getByText(/Market prices unavailable/i)).toBeInTheDocument();
  });

  it('renders mock data correctly and triggers actions', () => {
    const onRefresh = vi.fn();
    const onUseMarketValues = vi.fn();
    
    render(
      <MarketPricePanel 
        data={mockData} 
        isLoading={false} 
        isError={false} 
        onRefresh={onRefresh} 
        onUseMarketValues={onUseMarketValues} 
      />
    );

    expect(screen.getByText('MOCK DATA')).toBeInTheDocument();
    expect(screen.getByText('$3.25')).toBeInTheDocument();
    expect(screen.getByText('$4.10')).toBeInTheDocument();
    expect(screen.getByText('$28.50')).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Use market values/i));
    expect(onUseMarketValues).toHaveBeenCalled();
  });
});