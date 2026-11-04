import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FinancialFields, FinancialState } from './financial-fields';

describe('FinancialFields', () => {
  const defaultState: FinancialState = {
    ch4_feed_kmol_per_h: '100',
    natural_gas_price_usd_per_mmbtu: '3.25',
    syngas_price_usd_per_kmol: '4.10',
    carbon_credit_price_usd_per_tonne_co2e: '28.50',
    co2_utilization_fraction: '0.4',
    capex_usd: '5000000',
    opex_pct_of_capex_per_year: '5',
    operating_hours_per_day: '24',
    operating_days_per_year: '330',
  };

  it('renders financial inputs and market price inputs', () => {
    render(<FinancialFields state={defaultState} onChange={vi.fn()} errors={{}} />);
    
    expect(screen.getByLabelText(/CH4 Feed Rate/i)).toHaveValue(100);
    expect(screen.getByDisplayValue('5000000')).toHaveValue(5000000);
    
    // Market prices
    expect(screen.getByLabelText(/Natural Gas/i)).toHaveValue(3.25);
    expect(screen.getByLabelText(/Syngas/i)).toHaveValue(4.10);
  });

  it('triggers onChange when editing a market price', () => {
    const onChange = vi.fn();
    render(<FinancialFields state={defaultState} onChange={onChange} errors={{}} />);
    
    fireEvent.change(screen.getByLabelText(/Natural Gas/i), { target: { value: '4.00' } });
    expect(onChange).toHaveBeenCalledWith('natural_gas_price_usd_per_mmbtu', '4.00');
  });
});