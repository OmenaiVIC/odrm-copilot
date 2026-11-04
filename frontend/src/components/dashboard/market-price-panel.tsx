'use client';

import { MarketPricesResponse } from '@/lib/types';

interface MarketPricePanelProps {
  data?: MarketPricesResponse;
  isLoading: boolean;
  isError: boolean;
  onRefresh: () => void;
  onUseMarketValues: () => void;
}

export function MarketPricePanel({
  data,
  isLoading,
  isError,
  onRefresh,
  onUseMarketValues,
}: MarketPricePanelProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse rounded-xl bg-gray-100 p-6 dark:bg-zinc-800" aria-busy="true">
        <div className="h-6 w-1/3 rounded bg-gray-300 dark:bg-zinc-700 mb-4"></div>
        <div className="h-4 w-1/2 rounded bg-gray-300 dark:bg-zinc-700"></div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
        <h3 className="font-semibold text-red-800 dark:text-red-400 mb-2">Market prices unavailable</h3>
        <p className="text-sm text-red-700 dark:text-red-300 mb-4">
          Enter your own prices below to run the screening.
        </p>
        <button
          onClick={onRefresh}
          className="rounded-lg bg-red-100 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Market Prices</h3>
        {data.is_mock && (
          <span className="rounded-full bg-yellow-100 px-3 py-1 text-xs font-bold text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-500">
            MOCK DATA
          </span>
        )}
      </div>
      
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">Natural Gas</p>
          <p className="font-medium">${data.natural_gas_price_usd_per_mmbtu.toFixed(2)} <span className="text-xs text-gray-500">/ MMBtu</span></p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Syngas</p>
          <p className="font-medium">${data.syngas_price_usd_per_kmol.toFixed(2)} <span className="text-xs text-gray-500">/ kmol</span></p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Carbon Credit</p>
          <p className="font-medium">${data.carbon_credit_price_usd_per_tonne_co2e.toFixed(2)} <span className="text-xs text-gray-500">/ tCO2e</span></p>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <p>Source: {data.source} | As of: {new Date(data.as_of).toLocaleString()}</p>
        <button
          onClick={onUseMarketValues}
          className="text-blue-600 hover:underline font-medium dark:text-blue-400"
        >
          Use market values
        </button>
      </div>
    </div>
  );
}