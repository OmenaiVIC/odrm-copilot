import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ResultsPanel } from './results-panel';
import { TeaRequest, TeaResponse } from '@/lib/types';

vi.mock('./report-download', () => ({
  ReportDownload: ({ request }: { request: TeaRequest }) => (
    <div data-testid="report-download">{request.conditions.catalyst}</div>
  ),
}));

describe('ResultsPanel', () => {
  const mockData: TeaResponse = {
    predictions: { ch4_conversion: 0.85, syngas_yield_mol_per_mol_ch4: 2.41 },
    model_versions: { ch4_conversion: 'v1-123', syngas_yield_mol_per_mol_ch4: 'v1-456' },
    financials: {
      syngas_kmol_per_day: 5000,
      syngas_nm3_per_day: 100000,
      syngas_revenue_usd_per_day: 20000,
      co2_consumed_tonnes_per_day: 10,
      carbon_credit_value_usd_per_day: 250,
      total_revenue_usd_per_day: 20250,
      feed_cost_usd_per_day: 5000,
      opex_usd_per_day: 750,
      net_cash_flow_usd_per_day: 14500,
      annual_net_cash_flow_usd: 4785000,
      roi_pct: 95.7,
      payback_years: 1.04,
      currency: 'USD',
    },
    warnings: ['negative_annual_cash_flow'],
  };

  it('renders empty state when no data', () => {
    render(<ResultsPanel isLoading={false} isError={false} />);
    expect(screen.getByText(/Enter plant conditions/i)).toBeInTheDocument();
  });

  it('renders predictions and financials correctly', () => {
    render(<ResultsPanel data={mockData} isLoading={false} isError={false} />);
    
    // Predictions
    expect(screen.getByText('85.00%')).toBeInTheDocument();
    expect(screen.getByText('2.410')).toBeInTheDocument();
    
    // Financial KPIs
    expect(screen.getByText('$4,785,000')).toBeInTheDocument(); // Annual cash flow
    expect(screen.getByText('95.70%')).toBeInTheDocument(); // ROI
    expect(screen.getByText('1.04 years')).toBeInTheDocument(); // Payback
    
    // Warnings
    expect(screen.getByText(/Annual cash flow is negative/i)).toBeInTheDocument();
  });

  it('renders the report download only when both data and request exist', () => {
    const request = {
      conditions: { catalyst: 'Ni/Al2O3' },
      assumptions: {},
    } as unknown as TeaRequest;

    const { rerender } = render(
      <ResultsPanel data={mockData} request={request} isLoading={false} isError={false} />
    );
    expect(screen.getByTestId('report-download')).toHaveTextContent('Ni/Al2O3');

    rerender(<ResultsPanel data={mockData} isLoading={false} isError={false} />);
    expect(screen.queryByTestId('report-download')).not.toBeInTheDocument();

    rerender(<ResultsPanel request={request} isLoading={false} isError={false} />);
    expect(screen.getByText(/Enter plant conditions/i)).toBeInTheDocument();
    expect(screen.queryByTestId('report-download')).not.toBeInTheDocument();
  });

  it('renders unavailable payback correctly', () => {
    const unprofitableData = {
      ...mockData,
      financials: { ...mockData.financials, payback_years: null },
    };
    render(<ResultsPanel data={unprofitableData} isLoading={false} isError={false} />);
    
    expect(screen.getByText('Not available')).toBeInTheDocument();
  });
});