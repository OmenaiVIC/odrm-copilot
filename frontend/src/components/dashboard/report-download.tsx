'use client';

import { useMutation } from '@tanstack/react-query';
import { downloadReport, type ReportDownload as ReportDownloadResult } from '@/lib/api';
import type { TeaRequest } from '@/lib/types';

interface ReportDownloadProps {
  request: TeaRequest;
}

export function ReportDownload({ request }: ReportDownloadProps) {
  const mutation = useMutation({
    mutationFn: (variables: TeaRequest) => downloadReport(variables),
  });

  const handleDownload = () => {
    mutation.mutate(request, {
      onSuccess: (result: ReportDownloadResult) => {
        const objectUrl = URL.createObjectURL(result.blob);
        const anchor = document.createElement('a');
        try {
          anchor.href = objectUrl;
          anchor.download = result.filename;
          document.body.appendChild(anchor);
          anchor.click();
        } finally {
          anchor.remove();
          URL.revokeObjectURL(objectUrl);
        }
      },
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={handleDownload}
        disabled={mutation.isPending}
        aria-busy={mutation.isPending}
        className="w-full rounded-xl border border-blue-600 bg-white px-6 py-3 font-semibold text-blue-700 shadow-sm transition-colors hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 dark:border-blue-500 dark:bg-zinc-900 dark:text-blue-400 dark:hover:bg-blue-950/40"
      >
        {mutation.isPending ? 'Generating PDF...' : 'Download ESG Report'}
      </button>

      {mutation.isError && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/30 dark:text-red-400"
        >
          Report generation failed. Please try again.
        </p>
      )}

      <p role="status" aria-live="polite" className="text-sm text-green-700 dark:text-green-400">
        {mutation.isSuccess ? 'Report downloaded.' : ''}
      </p>
    </div>
  );
}
