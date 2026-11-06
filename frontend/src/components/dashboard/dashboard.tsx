'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useMarketPrices } from '@/hooks/use-market-prices';
import { postTea } from '@/lib/api';
import { ConditionsFields, ConditionsState } from './conditions-fields';
import { FinancialFields, FinancialState } from './financial-fields';
import { MarketPricePanel } from './market-price-panel';
import { ResultsPanel } from './results-panel';
import { RoadmapBanner } from './roadmap-banner';
import { validateNumber, BOUNDS } from '@/lib/validation';
import { TeaRequest } from '@/lib/types';
import { useAuth } from '@/components/auth/auth-provider';

const DEFAULT_CONDITIONS: ConditionsState = {
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

const DEFAULT_FINANCIALS: FinancialState = {
  ch4_feed_kmol_per_h: '100',
  natural_gas_price_usd_per_mmbtu: '3.25',
  syngas_price_usd_per_kmol: '4.10',
  carbon_credit_price_usd_per_tonne_co2e: '28.50',
  co2_utilization_fraction: '0.0',
  capex_usd: '5000000',
  opex_pct_of_capex_per_year: '5.0',
  operating_hours_per_day: '24.0',
  operating_days_per_year: '330.0',
};

export function Dashboard() {
  const { user, logout } = useAuth();

  const [conditions, setConditions] = useState<ConditionsState>(DEFAULT_CONDITIONS);
  const [financials, setFinancials] = useState<FinancialState>(DEFAULT_FINANCIALS);
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasEditedPrices, setHasEditedPrices] = useState(false);

  const marketQuery = useMarketPrices();
  
  const teaMutation = useMutation({
    mutationFn: postTea,
  });

  const [prevMarketData, setPrevMarketData] = useState(marketQuery.data);

  // Adjust state during render when market data changes
  if (marketQuery.data !== prevMarketData) {
    setPrevMarketData(marketQuery.data);
    if (!hasEditedPrices && marketQuery.data) {
      setFinancials((prev) => ({
        ...prev,
        natural_gas_price_usd_per_mmbtu: marketQuery.data.natural_gas_price_usd_per_mmbtu.toString(),
        syngas_price_usd_per_kmol: marketQuery.data.syngas_price_usd_per_kmol.toString(),
        carbon_credit_price_usd_per_tonne_co2e: marketQuery.data.carbon_credit_price_usd_per_tonne_co2e.toString(),
      }));
    }
  }

  const handleConditionChange = (field: keyof ConditionsState, value: string) => {
    setConditions((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const handleFinancialChange = (field: keyof FinancialState, value: string) => {
    setFinancials((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
    
    if (['natural_gas_price_usd_per_mmbtu', 'syngas_price_usd_per_kmol', 'carbon_credit_price_usd_per_tonne_co2e'].includes(field)) {
      setHasEditedPrices(true);
    }
  };

  const handleUseMarketValues = () => {
    if (marketQuery.data) {
      setFinancials((prev) => ({
        ...prev,
        natural_gas_price_usd_per_mmbtu: marketQuery.data.natural_gas_price_usd_per_mmbtu.toString(),
        syngas_price_usd_per_kmol: marketQuery.data.syngas_price_usd_per_kmol.toString(),
        carbon_credit_price_usd_per_tonne_co2e: marketQuery.data.carbon_credit_price_usd_per_tonne_co2e.toString(),
      }));
      setHasEditedPrices(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    // Validate Conditions
    const condParsed: Record<string, number | string | null> = {};
    for (const [key, val] of Object.entries(conditions)) {
      if (key === 'catalyst') {
        condParsed[key] = val;
        continue;
      }
      const isOptional = key === 'catalyst_loading_wt_pct' || key === 'n2_dilution_mol_pct';
      const { parsed, error } = validateNumber(val, key as keyof typeof BOUNDS, isOptional);
      if (error) newErrors[key] = error;
      if (parsed !== null) condParsed[key] = parsed;
      if (parsed === null && !isOptional) condParsed[key] = null;
    }

    // Validate Financials
    const finParsed: Record<string, number> = {};
    for (const [key, val] of Object.entries(financials)) {
      const isOptional = ['opex_pct_of_capex_per_year', 'operating_hours_per_day', 'operating_days_per_year'].includes(key);
      const { parsed, error } = validateNumber(val, key as keyof typeof BOUNDS, isOptional);
      if (error) newErrors[key] = error;
      if (parsed !== null) finParsed[key] = parsed;
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const payload: TeaRequest = {
      conditions: condParsed as unknown as TeaRequest['conditions'],
      assumptions: finParsed as unknown as TeaRequest['assumptions'],
    };

    teaMutation.mutate(payload);
  };

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 flex flex-col gap-8">
      
      {/* Brand & User Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between border-b border-gray-200 pb-4 dark:border-zinc-800 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-2">
            <span className="bg-gradient-to-r from-emerald-600 to-teal-400 bg-clip-text text-transparent">
              VALORIS
            </span>
            <span className="text-gray-300 dark:text-zinc-700 font-light text-2xl">|</span>
            <span className="text-gray-900 dark:text-white font-light tracking-widest text-xl uppercase mt-1">
              ODRM Copilot
            </span>
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Flare-gas valorization screening</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">{user?.email}</span>
          <button
            onClick={logout}
            className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-zinc-800 dark:text-gray-300 dark:hover:bg-zinc-700 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        
        {/* LEFT COLUMN: Inputs */}
        <div className="flex flex-col gap-8">
          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">1. Reactor Conditions</h2>
            <ConditionsFields state={conditions} onChange={handleConditionChange} errors={errors} />
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 flex flex-col gap-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">2. Financial Assumptions</h2>
            
            <MarketPricePanel 
              data={marketQuery.data} 
              isLoading={marketQuery.isLoading} 
              isError={marketQuery.isError} 
              onRefresh={() => marketQuery.refetch()}
              onUseMarketValues={handleUseMarketValues}
            />

            <FinancialFields state={financials} onChange={handleFinancialChange} errors={errors} />
          </section>

          <button
            type="submit"
            disabled={teaMutation.isPending}
            className="w-full rounded-xl bg-emerald-600 px-6 py-3 font-semibold text-white shadow-sm hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50 transition-colors"
          >
            {teaMutation.isPending ? 'Running Screening...' : 'Run Screening'}
          </button>
        </div>

        {/* RIGHT COLUMN: Results */}
        <div className="sticky top-8">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">3. Screening Result</h2>
          <ResultsPanel 
            data={teaMutation.data} 
            isLoading={teaMutation.isPending} 
            isError={teaMutation.isError} 
            request={teaMutation.variables}
          />
          {teaMutation.isError && (
            <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/30 dark:text-red-400">
              Failed to calculate: {teaMutation.error instanceof Error ? teaMutation.error.message : 'Check backend connection.'}
            </div>
          )}
        </div>
      </form>

      <div className="mt-8">
        <RoadmapBanner />
      </div>
    </div>
  );
}