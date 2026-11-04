import { Field } from '@/components/ui/field';

export interface ConditionsState {
  temperature_c: string;
  pressure_bar: string;
  ch4_o2_ratio: string;
  co2_ch4_ratio: string;
  h2o_ch4_ratio: string;
  ghsv_per_h: string;
  catalyst: string;
  catalyst_loading_wt_pct: string;
  n2_dilution_mol_pct: string;
}

interface ConditionsFieldsProps {
  state: ConditionsState;
  onChange: (field: keyof ConditionsState, value: string) => void;
  errors: Partial<Record<keyof ConditionsState, string>>;
}

const CATALYSTS = ['Ni/Al2O3', 'Ni-MgO', 'Rh', 'Pt', 'none', 'other'];

export function ConditionsFields({ state, onChange, errors }: ConditionsFieldsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Field
        label="Temperature"
        unit="°C"
        id="temperature_c"
        value={state.temperature_c}
        onChange={(e) => onChange('temperature_c', e.target.value)}
        error={errors.temperature_c}
      />
      <Field
        label="Pressure"
        unit="bar"
        id="pressure_bar"
        value={state.pressure_bar}
        onChange={(e) => onChange('pressure_bar', e.target.value)}
        error={errors.pressure_bar}
      />
      <Field
        label="CH4:O2 Ratio"
        unit="mol/mol"
        id="ch4_o2_ratio"
        value={state.ch4_o2_ratio}
        onChange={(e) => onChange('ch4_o2_ratio', e.target.value)}
        error={errors.ch4_o2_ratio}
      />
      <Field
        label="CO2:CH4 Ratio"
        unit="mol/mol"
        id="co2_ch4_ratio"
        value={state.co2_ch4_ratio}
        onChange={(e) => onChange('co2_ch4_ratio', e.target.value)}
        error={errors.co2_ch4_ratio}
      />
      <Field
        label="H2O:CH4 Ratio"
        unit="mol/mol"
        id="h2o_ch4_ratio"
        value={state.h2o_ch4_ratio}
        onChange={(e) => onChange('h2o_ch4_ratio', e.target.value)}
        error={errors.h2o_ch4_ratio}
      />
      <Field
        label="GHSV"
        unit="1/h"
        id="ghsv_per_h"
        value={state.ghsv_per_h}
        onChange={(e) => onChange('ghsv_per_h', e.target.value)}
        error={errors.ghsv_per_h}
      />
      
      <Field
        label="Catalyst"
        id="catalyst"
        value={state.catalyst}
        onChange={(e) => onChange('catalyst', e.target.value)}
        error={errors.catalyst}
      >
        <select
          id="catalyst"
          value={state.catalyst}
          onChange={(e) => onChange('catalyst', e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700 dark:text-white"
        >
          {CATALYSTS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </Field>

      <Field
        label="Catalyst Loading"
        unit="wt%"
        id="catalyst_loading_wt_pct"
        value={state.catalyst_loading_wt_pct}
        onChange={(e) => onChange('catalyst_loading_wt_pct', e.target.value)}
        error={errors.catalyst_loading_wt_pct}
        required={false}
      />
      <Field
        label="N2 Dilution"
        unit="mol%"
        id="n2_dilution_mol_pct"
        value={state.n2_dilution_mol_pct}
        onChange={(e) => onChange('n2_dilution_mol_pct', e.target.value)}
        error={errors.n2_dilution_mol_pct}
        required={false}
      />
    </div>
  );
}