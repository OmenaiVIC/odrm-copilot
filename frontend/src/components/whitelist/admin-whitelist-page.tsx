'use client';

import { type FormEvent, useState } from 'react';
import { ApiError } from '@/lib/api';
import type { WhitelistApplication, WhitelistStatus } from '@/lib/types';
import { useAuth } from '@/components/auth/auth-provider';
import {
  useApproveWhitelistApplication,
  useRejectWhitelistApplication,
  useWhitelistApplications,
} from '@/hooks/use-whitelist';

type StatusFilter = 'all' | WhitelistStatus;

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

const STATUS_STYLES: Record<WhitelistStatus, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  approved:
    'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_LABELS: Record<WhitelistStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
};

function StatusBadge({ status }: { status: WhitelistStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    let detail: unknown = error.detail;
    if (detail && typeof detail === 'object' && 'detail' in detail) {
      detail = (detail as { detail: unknown }).detail;
    }
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === 'string' && message.length > 0) {
        return message;
      }
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === 'string') {
        return first.msg;
      }
    }
  }
  if (error instanceof Error && error.message.length > 0) {
    return error.message;
  }
  return 'The request could not be completed. Please try again.';
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

export function AdminWhitelistPage() {
  const { user } = useAuth();

  if (user?.role !== 'admin') {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-8">
        <section className="rounded-xl border border-red-200 bg-white p-6 shadow-sm dark:border-red-900 dark:bg-zinc-900">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Access denied
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            You need an administrator account to review public-good applications.
          </p>
        </section>
      </main>
    );
  }

  return <AdminWhitelistContent />;
}

function AdminWhitelistContent() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [rejectTarget, setRejectTarget] = useState<WhitelistApplication | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const applicationsQuery = useWhitelistApplications(
    statusFilter === 'all' ? undefined : statusFilter,
  );
  const approveMutation = useApproveWhitelistApplication();
  const rejectMutation = useRejectWhitelistApplication();
  const decisionPending = approveMutation.isPending || rejectMutation.isPending;

  const handleApprove = async (application: WhitelistApplication) => {
    setError(null);
    try {
      await approveMutation.mutateAsync(application.id);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  const handleReject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!rejectTarget || rejectReason.trim().length === 0) {
      return;
    }
    setError(null);
    try {
      await rejectMutation.mutateAsync({
        applicationId: rejectTarget.id,
        reason: rejectReason.trim(),
      });
      setRejectTarget(null);
      setRejectReason('');
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <main className="mx-auto max-w-6xl p-4 md:p-8">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
          Public-good review
        </p>
        <h1 className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
          Whitelist Applications
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Review public-good access requests. Approval grants the applicant the public_good
          role immediately.
        </p>
      </header>

      <section className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-2">
            <label
              htmlFor="whitelist-status-filter"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Status
            </label>
            <select
              id="whitelist-status-filter"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 dark:border-zinc-700 dark:bg-zinc-950 dark:text-gray-100 sm:w-48"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {applicationsQuery.data && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {applicationsQuery.data.total} application
              {applicationsQuery.data.total === 1 ? '' : 's'}
            </p>
          )}
        </div>

        {applicationsQuery.isLoading && (
          <p className="mt-6 text-sm text-gray-500 animate-pulse dark:text-gray-400">
            Loading applications...
          </p>
        )}

        {applicationsQuery.isError && (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
          >
            <p>{errorMessage(applicationsQuery.error)}</p>
            <button
              type="button"
              onClick={() => applicationsQuery.refetch()}
              className="mt-3 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
            >
              Try again
            </button>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
          >
            {error}
          </div>
        )}

        {applicationsQuery.data && applicationsQuery.data.items.length === 0 && (
          <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
            No applications match this filter.
          </p>
        )}

        {applicationsQuery.data && applicationsQuery.data.items.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm dark:divide-zinc-800">
              <thead className="bg-gray-50 dark:bg-zinc-950/50">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Applicant
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Status
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Reason
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Decision reason
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Submitted
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 font-semibold text-gray-700 dark:text-gray-300"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-zinc-800">
                {applicationsQuery.data.items.map((application) => (
                  <tr key={application.id}>
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {application.user_email}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={application.status} />
                    </td>
                    <td className="max-w-xs whitespace-pre-wrap break-words px-4 py-3 text-gray-700 dark:text-gray-300">
                      {application.reason}
                    </td>
                    <td className="max-w-xs whitespace-pre-wrap break-words px-4 py-3 text-gray-700 dark:text-gray-300">
                      {application.decision_reason ?? '—'}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-700 dark:text-gray-300">
                      {formatDate(application.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            void handleApprove(application);
                          }}
                          disabled={decisionPending || application.status !== 'pending'}
                          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setRejectTarget(application);
                            setRejectReason('');
                            setError(null);
                          }}
                          disabled={decisionPending || application.status !== 'pending'}
                          className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {rejectTarget && (
          <form
            onSubmit={handleReject}
            className="mt-6 rounded-xl border border-red-200 bg-red-50/50 p-5 dark:border-red-900 dark:bg-red-950/20"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-red-700 dark:text-red-300">
                  Reject application
                </p>
                <h2 className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                  {rejectTarget.user_email}
                </h2>
              </div>
              <StatusBadge status={rejectTarget.status} />
            </div>
            <div className="mt-4 flex flex-col gap-2">
              <label
                htmlFor="reject-reason"
                className="text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Rejection reason
              </label>
              <textarea
                id="reject-reason"
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
                rows={4}
                maxLength={2000}
                required
                aria-describedby="reject-reason-help"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 dark:border-zinc-700 dark:bg-zinc-950 dark:text-gray-100"
              />
              <p
                id="reject-reason-help"
                className="text-xs text-gray-500 dark:text-gray-400"
              >
                {rejectReason.length} / 2000 characters
              </p>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={rejectMutation.isPending || rejectReason.trim().length === 0}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
              >
                {rejectMutation.isPending ? 'Rejecting...' : 'Confirm rejection'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setRejectTarget(null);
                  setRejectReason('');
                  setError(null);
                }}
                disabled={rejectMutation.isPending}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200 disabled:opacity-50 dark:bg-zinc-800 dark:text-gray-300 dark:hover:bg-zinc-700"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
}