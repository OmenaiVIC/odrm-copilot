'use client';

import { type FormEvent, useState } from 'react';
import { ApiError } from '@/lib/api';
import type { WhitelistStatus } from '@/lib/types';
import { useAuth } from '@/components/auth/auth-provider';
import { useApplyForWhitelist, useMyWhitelistApplication } from '@/hooks/use-whitelist';

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

export function WhitelistPage() {
  const { user } = useAuth();
  const applicationQuery = useMyWhitelistApplication();
  const applyMutation = useApplyForWhitelist();
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const application = applicationQuery.data ?? null;
  const isAdmin = user?.role === 'admin';
  const isEligible = user?.role === 'commercial' || user?.role === 'viewer';
  const hasApprovedAccess =
    user?.role === 'public_good' || application?.status === 'approved';
  const showPending = !hasApprovedAccess && application?.status === 'pending';
  const showRejected = !hasApprovedAccess && application?.status === 'rejected';
  const showForm =
    isEligible &&
    !hasApprovedAccess &&
    (!application || application.status === 'rejected');
  const isReapply = application?.status === 'rejected';

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = reason.trim();
    if (trimmed.length === 0 || applyMutation.isPending) {
      return;
    }
    setError(null);
    try {
      await applyMutation.mutateAsync(trimmed);
      setReason('');
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-4 md:p-8">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
          Public-good access
        </p>
        <h1 className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
          Public-Good Whitelist
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Eligible researchers, NGOs, regulators, and NGFCP permit holders can request free
          access to the ODRM dashboard and ESG export.
        </p>
      </header>

      {isAdmin && (
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Admins already have full access
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            An administrator account cannot submit a public-good application.
          </p>
        </section>
      )}

      {!isAdmin && applicationQuery.isLoading && (
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-sm text-gray-500 animate-pulse dark:text-gray-400">
            Loading your application...
          </p>
        </section>
      )}

      {!isAdmin && applicationQuery.isError && (
        <section
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
        >
          <h2 className="text-lg font-semibold">Could not load your application</h2>
          <p className="mt-2 text-sm">{errorMessage(applicationQuery.error)}</p>
          <button
            type="button"
            onClick={() => applicationQuery.refetch()}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
          >
            Try again
          </button>
        </section>
      )}

      {!isAdmin && !applicationQuery.isLoading && !applicationQuery.isError && (
        <>
          {hasApprovedAccess && (
            <section
              role="status"
              className="rounded-xl border border-emerald-200 bg-white p-6 shadow-sm dark:border-emerald-900 dark:bg-zinc-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Status
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                    Application approved
                  </h2>
                </div>
                <StatusBadge status="approved" />
              </div>
              <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                Your account has public-good access. The backend enforces this role on every
                request.
              </p>
              {application && (
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-medium text-gray-500 dark:text-gray-400">
                      Submitted
                    </dt>
                    <dd className="mt-1 text-gray-800 dark:text-gray-200">
                      {formatDate(application.created_at)}
                    </dd>
                  </div>
                  {application.decision_reason && (
                    <div>
                      <dt className="font-medium text-gray-500 dark:text-gray-400">
                        Reviewer note
                      </dt>
                      <dd className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                        {application.decision_reason}
                      </dd>
                    </div>
                  )}
                </dl>
              )}
            </section>
          )}

          {showPending && application && (
            <section
              role="status"
              className="rounded-xl border border-amber-200 bg-white p-6 shadow-sm dark:border-amber-900 dark:bg-zinc-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Status
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                    Application pending
                  </h2>
                </div>
                <StatusBadge status="pending" />
              </div>
              <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                Your application is awaiting review.
              </p>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-gray-500 dark:text-gray-400">
                    Submitted
                  </dt>
                  <dd className="mt-1 text-gray-800 dark:text-gray-200">
                    {formatDate(application.created_at)}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium text-gray-500 dark:text-gray-400">Reason</dt>
                  <dd className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                    {application.reason}
                  </dd>
                </div>
              </dl>
            </section>
          )}

          {showRejected && application && (
            <section
              role="status"
              className="rounded-xl border border-red-200 bg-white p-6 shadow-sm dark:border-red-900 dark:bg-zinc-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Status
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
                    Application rejected
                  </h2>
                </div>
                <StatusBadge status="rejected" />
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-gray-500 dark:text-gray-400">
                    Submitted
                  </dt>
                  <dd className="mt-1 text-gray-800 dark:text-gray-200">
                    {formatDate(application.created_at)}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium text-gray-500 dark:text-gray-400">Reason</dt>
                  <dd className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                    {application.reason}
                  </dd>
                </div>
                {application.decision_reason && (
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-gray-500 dark:text-gray-400">
                      Reviewer note
                    </dt>
                    <dd className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {application.decision_reason}
                    </dd>
                  </div>
                )}
              </dl>
            </section>
          )}

          {showForm && (
            <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {isReapply
                  ? 'Reapply for public-good access'
                  : 'Apply for public-good access'}
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {isReapply
                  ? 'Your previous application was rejected. You can submit a new reason for review.'
                  : 'Tell the review team how you qualify under the public-good criteria.'}
              </p>
              <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <label
                    htmlFor="whitelist-reason"
                    className="text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    {isReapply ? 'Reason for reapplying' : 'Reason for application'}
                  </label>
                  <textarea
                    id="whitelist-reason"
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    rows={5}
                    maxLength={2000}
                    required
                    aria-describedby="whitelist-reason-help"
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 dark:border-zinc-700 dark:bg-zinc-950 dark:text-gray-100"
                  />
                  <p
                    id="whitelist-reason-help"
                    className="text-xs text-gray-500 dark:text-gray-400"
                  >
                    {reason.length} / 2000 characters
                  </p>
                </div>
                {error && (
                  <p
                    role="alert"
                    className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
                  >
                    {error}
                  </p>
                )}
                <button
                  type="submit"
                  disabled={applyMutation.isPending || reason.trim().length === 0}
                  className="self-start rounded-lg bg-emerald-600 px-5 py-2 font-semibold text-white shadow-sm transition-colors hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50"
                >
                  {applyMutation.isPending
                    ? 'Submitting...'
                    : isReapply
                      ? 'Reapply'
                      : 'Submit application'}
                </button>
              </form>
            </section>
          )}

          {!hasApprovedAccess && !showPending && !showRejected && !showForm && (
            <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Your account is not eligible to apply
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Only commercial and viewer accounts can request public-good access.
              </p>
            </section>
          )}
        </>
      )}
    </main>
  );
}