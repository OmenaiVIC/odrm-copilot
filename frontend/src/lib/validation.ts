export const BOUNDS = {
  temperature_c: { min: 500, max: 1000 },
  pressure_bar: { min: 1, max: 30 },
  ch4_o2_ratio: { min: 1.4, max: 2.5 },
  co2_ch4_ratio: { min: 0, max: 1.5 },
  h2o_ch4_ratio: { min: 0, max: 1.5 },
  ghsv_per_h: { min: 1000, max: 100000 },
  catalyst_loading_wt_pct: { min: 0, max: 20 },
  n2_dilution_mol_pct: { min: 0, max: 50 },
  ch4_feed_kmol_per_h: { min: 0.0001, max: 1000000 },
  natural_gas_price_usd_per_mmbtu: { min: 0, max: 1000 },
  syngas_price_usd_per_kmol: { min: 0, max: 1000000 },
  carbon_credit_price_usd_per_tonne_co2e: { min: 0, max: 100000 },
  co2_utilization_fraction: { min: 0, max: 1 },
  capex_usd: { min: 0.0001, max: 1000000000000 },
  opex_pct_of_capex_per_year: { min: 0, max: 100 },
  operating_hours_per_day: { min: 0.0001, max: 24 },
  operating_days_per_year: { min: 0.0001, max: 365 },
};

export function validateNumber(
  value: string,
  field: keyof typeof BOUNDS,
  isOptional = false
): { parsed: number | null; error: string | null } {
  if (isOptional && value.trim() === '') {
    return { parsed: null, error: null };
  }

  const num = Number(value);
  if (isNaN(num) || !isFinite(num)) {
    return { parsed: null, error: 'Must be a valid number' };
  }

  const { min, max } = BOUNDS[field];
  if (num < min || num > max) {
    return { parsed: null, error: `Must be between ${min} and ${max}` };
  }

  return { parsed: num, error: null };
}