import { TeaResponse } from '@/lib/types';

interface ResultsPanelProps {
  data?: TeaResponse;
  isLoading: boolean;
  isError: boolean;
}

const WARNING_MESSAGES: Record<string, string> = {
  carbon_credit_not_included: 'CO2 utilization is zero. Carbon credit revenue is not included.',
  negative_annual_cash_flow: 'Annual cash flow is negative. Payback is not available.',
  syngas_yield_out_of_envelope: 'Predicted syngas yield is outside the screening envelope.',
  zero_syngas_price: 'Syngas price is zero. Product revenue is zero.',
  zero_carbon_price: 'Carbon-credit price is zero. Credit value is zero.',
};

export function ResultsPanel({ data, isLoading, isError }: ResultsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex h-full min-h-[400px] animate-pulse flex-col items-center justify-center rounded-xl bg-gray-100 p-6 dark:bg-zinc-800" aria-busy="true">
        <p className="text-gray-500 font-medium">Running screening...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
        <h3 className="font-semibold text-red-800 dark:text-red-400">Screening failed</h3>
        <p className="text-sm text-red-700 dark:text-red-300 mt-2">Adjust your inputs and try again.</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 dark:border-zinc-800 dark:bg-zinc-900/50">
        <p className="text-gray-500 text-center max-w-xs">
          Enter plant conditions and financial assumptions, then click <strong>Run Screening</strong> to see the AI predictions and financial ROI.
        </p>
      </div>
    );
  }

  const { predictions, financials, warnings, model_versions } = data;

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Predictions */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="text-lg font-semibold mb-4">AI Process Predictions</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
            <p className="text-sm text-blue-800 dark:text-blue-300 mb-1">CH4 Conversion</p>
            <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">
              {(predictions.ch4_conversion * 100).toFixed(2)}%
            </p>
          </div>
          <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
            <p className="text-sm text-green-800 dark:text-green-300 mb-1">Syngas Yield</p>
            <p className="text-2xl font-bold text-green-900 dark:text-green-100">
              {predictions.syngas_yield_mol_per_mol_ch4.toFixed(3)} <span className="text-sm font-normal">mol/mol CH4</span>
            </p>
          </div>
        </div>
      </div>

      {/* 2. Financials */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="text-lg font-semibold mb-4">Financial Screening</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="rounded-lg border border-gray-100 p-4 dark:border-zinc-800">
            <p className="text-sm text-gray-500 mb-1">Annual Net Cash Flow</p>
            <p className={`text-xl font-bold ${financials.annual_net_cash_flow_usd < 0 ? 'text-red-600' : 'text-gray-900 dark:text-white'}`}>
              ${financials.annual_net_cash_flow_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>
          <div className="rounded-lg border border-gray-100 p-4 dark:border-zinc-800">
            <p className="text-sm text-gray-500 mb-1">ROI</p>
            <p className={`text-xl font-bold ${financials.roi_pct < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {financials.roi_pct.toFixed(2)}%
            </p>
          </div>
          <div className="rounded-lg border border-gray-100 p-4 dark:border-zinc-800">
            <p className="text-sm text-gray-500 mb-1">Payback Period</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">
              {financials.payback_years !== null 
                ? `${financials.payback_years.toFixed(2)} years` 
                : 'Not available'}
            </p>
          </div>
        </div>

        <details className="group">
          <summary className="cursor-pointer text-sm text-blue-600 hover:underline dark:text-blue-400">
            View detailed financial breakdown
          </summary>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 uppercase bg-gray-50 dark:bg-zinc-800 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 rounded-tl-lg">Metric</th>
                  <th className="px-4 py-2 rounded-tr-lg text-right">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-zinc-800">
                <tr><td className="px-4 py-2">Syngas Production</td><td className="px-4 py-2 text-right">{financials.syngas_kmol_per_day.toFixed(2)} kmol/day</td></tr>
                <tr><td className="px-4 py-2">Total Revenue</td><td className="px-4 py-2 text-right">${financials.total_revenue_usd_per_day.toFixed(2)} / day</td></tr>
                <tr><td className="px-4 py-2">Feed Cost</td><td className="px-4 py-2 text-right">${financials.feed_cost_usd_per_day.toFixed(2)} / day</td></tr>
                <tr><td className="px-4 py-2">OPEX</td><td className="px-4 py-2 text-right">${financials.opex_usd_per_day.toFixed(2)} / day</td></tr>
                <tr><td className="px-4 py-2">Net Cash Flow</td><td className="px-4 py-2 text-right">${financials.net_cash_flow_usd_per_day.toFixed(2)} / day</td></tr>
              </tbody>
            </table>
          </div>
        </details>
      </div>

      {/* 3. Warnings */}
      {warnings.length > 0 && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-900/50 dark:bg-yellow-900/20">
          <h4 className="text-sm font-semibold text-yellow-800 dark:text-yellow-500 mb-2">Warnings</h4>
          <ul className="list-disc list-inside space-y-1">
           {warnings.map((code: string) => (
            <li key={code} className="text-sm text-yellow-700 dark:text-yellow-400">
              {WARNING_MESSAGES[code] || code}
            </li>
    ))}
          </ul>
        </div>
      )}

      {/* 4. Provenance */}
      <div className="text-xs text-gray-400 dark:text-gray-500">
        <p>Model Provenance:</p>
        <ul className="list-disc list-inside mt-1 space-y-0.5">
          <li>CH4 Model: {model_versions.ch4_conversion}</li>
          <li>Syngas Model: {model_versions.syngas_yield_mol_per_mol_ch4}</li>
        </ul>
      </div>
    </div>
  );
}