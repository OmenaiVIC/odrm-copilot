import { useQuery } from '@tanstack/react-query';
import { getDetectionHotspots } from '@/lib/api';

export function useDetectionHotspots() {
  return useQuery({
    queryKey: ['detection-hotspots'],
    queryFn: getDetectionHotspots,
  });
}
