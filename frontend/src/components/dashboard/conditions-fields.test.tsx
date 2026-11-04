import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ConditionsFields, ConditionsState } from './conditions-fields';

describe('ConditionsFields', () => {
  const defaultState: ConditionsState = {
    temperature_c: '800',
    pressure_bar: '10',
    ch4_o2_ratio: '2.0',
    co2_ch4_ratio: '0.5',
    h2o_ch4_ratio: '0.2',
    ghsv_per_h: '5000',
    catalyst: 'Ni/Al2O3',
    catalyst_loading_wt_pct: '10',
    n2_dilution_mol_pct: '',
  };

  it('renders all inputs with values', () => {
    render(<ConditionsFields state={defaultState} onChange={vi.fn()} errors={{}} />);
    
    expect(screen.getByLabelText(/Temperature/i)).toHaveValue(800);
    expect(screen.getByLabelText(/^Catalyst \*$/i)).toHaveValue('Ni/Al2O3');
    expect(screen.getByLabelText(/N2 Dilution/i)).toHaveValue(null); // blank number input
  });

  it('calls onChange when a value changes', () => {
    const onChange = vi.fn();
    render(<ConditionsFields state={defaultState} onChange={onChange} errors={{}} />);
    
    fireEvent.change(screen.getByLabelText(/Temperature/i), { target: { value: '850' } });
    expect(onChange).toHaveBeenCalledWith('temperature_c', '850');
  });
});