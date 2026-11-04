import { Field } from '@/components/ui/field';

export interface FinancialState {
  ch4_feed_kmol_per_h: string;
  natural_gas_price_usd_per_mmbtu: string;
  syngas_price_usd_per_kmol: string;
  carbon_credit_price_usd_per_tonne_co2e: string;
  co2_utilization_fraction: string;
  capex_usd: string;
  opex_pct_of_capex_per_year: string;
  operating_hours_per_day: string;
  operating_days_per_year: string;
}

interface FinancialFieldsProps {
  state: FinancialState;
  onChange: (field: keyof FinancialState, value: string) => void;
  errors: Partial<Record<keyof FinancialState, string>>;
}

export function FinancialFields({ state, onChange, errors }: FinancialFieldsProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field
          label="CH4 Feed Rate"
          unit="kmol/h"
          id="ch4_feed_kmol_per_h"
          value={state.ch4_feed_kmol_per_h}
          onChange={(e) => onChange('ch4_feed_kmol_per_h', e.target.value)}
          error={errors.ch4_feed_kmol_per_h}
        />
        <Field
          label="CAPEX"
          unit="USD"
          id="capex_usd"
          value={state.capex_usd}
          onChange={(e) => onChange('capex_usd', e.target.value)}
          error={errors.capex_usd}
        />
        <Field
          label="CO2 Utilization"
          unit="fraction (0-1)"
          id="co2_utilization_fraction"
          value={state.co2_utilization_fraction}
          onChange={(e) => onChange('co2_utilization_fraction', e.target.value)}
          error={errors.co2_utilization_fraction}
        />
      </div>

      <div className="border-t border-gray-200 pt-4 dark:border-zinc-800">
        <h4 className="text-sm font-semibold mb-4 text-gray-700 dark:text-gray-300">Market Prices (Editable)</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Field
            label="Natural Gas"
            unit="USD/MMBtu"
            id="natural_gas_price_usd_per_mmbtu"
            value={state.natural_gas_price_usd_per_mmbtu}
            onChange={(e) => onChange('natural_gas_price_usd_per_mmbtu', e.target.value)}
            error={errors.natural_gas_price_usd_per_mmbtu}
          />
          <Field
            label="Syngas"
            unit="USD/kmol"
            id="syngas_price_usd_per_kmol"
            value={state.syngas_price_usd_per_kmol}
            onChange={(e) => onChange('syngas_price_usd_per_kmol', e.target.value)}
            error={errors.syngas_price_usd_per_kmol}
          />
          <Field
            label="Carbon Credit"
            unit="USD/tCO2e"
            id="carbon_credit_price_usd_per_tonne_co2e"
            value={state.carbon_credit_price_usd_per_tonne_co2e}
            onChange={(e) => onChange('carbon_credit_price_usd_per_tonne_co2e', e.target.value)}
            error={errors.carbon_credit_price_usd_per_tonne_co2e}
          />
        </div>
      </div>

      <details className="group border-t border-gray-200 pt-4 dark:border-zinc-800">
        <summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
          Advanced Assumptions
        </summary>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <Field
            label="OPEX"
            unit="% of CAPEX/year"
            id="opex_pct_of_capex_per_year"
            value={state.opex_pct_of_capex_per_year}
            onChange={(e) => onChange('opex_pct_of_capex_per_year', e.target.value)}
            error={errors.opex_pct_of_capex_per_year}
            required={false}
          />
          <Field
            label="Operating Hours"
            unit="h/day"
            id="operating_hours_per_day"
            value={state.operating_hours_per_day}
            onChange={(e) => onChange('operating_hours_per_day', e.target.value)}
            error={errors.operating_hours_per_day}
            required={false}
          />
          <Field
            label="Operating Days"
            unit="days/year"
            id="operating_days_per_year"
            value={state.operating_days_per_year}
            onChange={(e) => onChange('operating_days_per_year', e.target.value)}
            error={errors.operating_days_per_year}
            required={false}
          />
        </div>
      </details>
    </div>
  );
}