import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/components/auth/auth-provider';
import {
  getMyWhitelistApplication,
  getWhitelistApplications,
  postWhitelistApplication,
  postWhitelistApplicationApproval,
  postWhitelistApplicationRejection,
} from '@/lib/api';
import type { WhitelistStatus } from '@/lib/types';

export function useMyWhitelistApplication() {
  const { status, user } = useAuth();

  return useQuery({
    queryKey: ['whitelist', 'me', user?.id ?? 'anonymous'],
    queryFn: getMyWhitelistApplication,
    enabled: status === 'authenticated' && user !== null,
    retry: false,
  });
}

export function useWhitelistApplications(statusFilter?: WhitelistStatus) {
  const { user } = useAuth();

  return useQuery({
    queryKey: ['whitelist', 'applications', statusFilter ?? 'all'],
    queryFn: () => getWhitelistApplications(statusFilter),
    enabled: user?.role === 'admin',
  });
}

export function useApplyForWhitelist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (reason: string) => postWhitelistApplication(reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['whitelist'] }),
  });
}

export function useApproveWhitelistApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (applicationId: string) =>
      postWhitelistApplicationApproval(applicationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['whitelist'] });
      await queryClient.invalidateQueries({ queryKey: ['whitelist', 'applications'] });
    },
  });
}

export function useRejectWhitelistApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      applicationId,
      reason,
    }: {
      applicationId: string;
      reason: string;
    }) => postWhitelistApplicationRejection(applicationId, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['whitelist'] });
      await queryClient.invalidateQueries({ queryKey: ['whitelist', 'applications'] });
    },
  });
}