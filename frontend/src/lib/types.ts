export interface MarketPricesResponse {
  natural_gas_price_usd_per_mmbtu: number;
  syngas_price_usd_per_kmol: number;
  carbon_credit_price_usd_per_tonne_co2e: number;
  currency: string;
  source: string;
  is_mock: boolean;
  as_of: string;
  cached: boolean;
  cache_ttl_seconds: number;
}

export interface PredictRequest {
  temperature_c: number;
  pressure_bar: number;
  ch4_o2_ratio: number;
  co2_ch4_ratio: number;
  h2o_ch4_ratio: number;
  ghsv_per_h: number;
  catalyst: string;
  catalyst_loading_wt_pct?: number | null;
  n2_dilution_mol_pct?: number | null;
}

export interface TeaAssumptions {
  ch4_feed_kmol_per_h: number;
  natural_gas_price_usd_per_mmbtu: number;
  syngas_price_usd_per_kmol: number;
  carbon_credit_price_usd_per_tonne_co2e: number;
  co2_utilization_fraction: number;
  capex_usd: number;
  opex_pct_of_capex_per_year?: number;
  operating_hours_per_day?: number;
  operating_days_per_year?: number;
}

export interface TeaRequest {
  conditions: PredictRequest;
  assumptions: TeaAssumptions;
}

export interface TeaFinancials {
  syngas_kmol_per_day: number;
  syngas_nm3_per_day: number;
  syngas_revenue_usd_per_day: number;
  co2_consumed_tonnes_per_day: number;
  carbon_credit_value_usd_per_day: number;
  total_revenue_usd_per_day: number;
  feed_cost_usd_per_day: number;
  opex_usd_per_day: number;
  net_cash_flow_usd_per_day: number;
  annual_net_cash_flow_usd: number;
  roi_pct: number;
  payback_years: number | null;
  currency: string;
}

export interface TeaResponse {
  predictions: {
    ch4_conversion: number;
    syngas_yield_mol_per_mol_ch4: number;
  };
  model_versions: {
    ch4_conversion: string;
    syngas_yield_mol_per_mol_ch4: string;
  };
  financials: TeaFinancials;
  warnings: string[];
}

export type ChatStatus = 'ok' | 'needs_input';

export interface ChatRequest {
  message: string;
}

export interface ChatErrorDetail {
  code: string;
  message: string;
  request_id?: string;
  field?: string | null;
  value?: number | string | null;
  minimum?: number | null;
  maximum?: number | null;
  missing_fields?: string[];
}

export interface ChatResponse {
  status: ChatStatus;
  reply: string;
  result: TeaResponse | null;
  request_id: string;
}

export interface AuthUser {
  id: string;
  email: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
}
