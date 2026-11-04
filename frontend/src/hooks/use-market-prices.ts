import { useQuery } from '@tanstack/react-query';
import { getMarketPrices } from '@/lib/api';

export function useMarketPrices() {
  return useQuery({
    queryKey: ['market-prices'],
    queryFn: getMarketPrices,
  });
}