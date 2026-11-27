'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useDetectionHotspots } from '@/hooks/use-detection';
import type { Hotspot } from '@/lib/types';

const COPY_FEEDBACK_MS = 2000;

type CopyStatus = 'copied' | 'failed';

interface CopyFeedback {
  id: string;
  status: CopyStatus;
}

function formatUtc(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

const HotspotMap = dynamic(() => import('./hotspot-map'), {
  ssr: false,
  loading: () => (
    <div className="p-4 text-sm text-gray-500 dark:text-gray-400">
      Loading map...
    </div>
  ),
});

export function DetectionPanel() {
  const { data, isLoading, isError, refetch } = useDetectionHotspots();
  const [copyFeedback, setCopyFeedback] = useState<CopyFeedback | null>(null);
  const feedbackTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (feedbackTimeout.current !== null) {
        clearTimeout(feedbackTimeout.current);
      }
    };
  }, []);

  const showCopyFeedback = (id: string, status: CopyStatus) => {
    if (feedbackTimeout.current !== null) {
      clearTimeout(feedbackTimeout.current);
    }
    setCopyFeedback({ id, status });
    feedbackTimeout.current = setTimeout(() => {
      setCopyFeedback(null);
      feedbackTimeout.current = null;
    }, COPY_FEEDBACK_MS);
  };

  const handleCopy = async (hotspot: Hotspot) => {
    try {
      await navigator.clipboard.writeText(
        `${hotspot.latitude}, ${hotspot.longitude}`,
      );
      showCopyFeedback(hotspot.id, 'copied');
    } catch {
      showCopyFeedback(hotspot.id, 'failed');
    }
  };

  const copyLabel = (hotspot: Hotspot): string => {
    if (copyFeedback?.id !== hotspot.id) {
      return 'Copy coordinates';
    }
    return copyFeedback.status === 'copied' ? 'Copied' : 'Copy failed';
  };

  const copyAriaLabel = (hotspot: Hotspot): string => {
    if (copyFeedback?.id !== hotspot.id) {
      return `Copy coordinates for ${hotspot.id}`;
    }
    return copyFeedback.status === 'copied'
      ? `Copied coordinates for ${hotspot.id}`
      : `Failed to copy coordinates for ${hotspot.id}`;
  };

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between mb-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Methane Detection Hotspots
            </h2>
            <span className="rounded-full bg-yellow-100 px-3 py-1 text-xs font-bold text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-500">
              SYNTHETIC DATA
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Synthetic demonstration data. Not real observations or regulatory measurements.
          </p>
        </div>
      </div>

      {isLoading && (
        <p role="status" className="text-sm text-gray-500 dark:text-gray-400">
          Loading detection hotspots...
        </p>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30"
        >
          <p className="text-sm text-red-700 dark:text-red-300">
            Detection hotspots unavailable.
          </p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="mt-3 rounded-lg bg-red-100 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && data && data.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No hotspots returned.
        </p>
      )}

      {!isLoading && !isError && data && data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
            {data.length} hotspot{data.length === 1 ? '' : 's'}
          </p>
          <div className="mb-4">
            <HotspotMap hotspots={data} />
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-zinc-800">
                  <th scope="col" className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                    Hotspot
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                    Coordinates
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                    Intensity
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                    Detected
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                    Source
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-gray-500 dark:text-gray-400">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.map((hotspot) => (
                  <tr
                    key={hotspot.id}
                    className="border-b border-gray-100 last:border-0 dark:border-zinc-800/60"
                  >
                    <td className="px-3 py-3 font-mono text-xs text-gray-900 dark:text-gray-100">
                      {hotspot.id}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-gray-900 dark:text-gray-100">
                      {hotspot.latitude.toFixed(4)}, {hotspot.longitude.toFixed(4)}
                    </td>
                    <td className="px-3 py-3 text-gray-900 dark:text-gray-100">
                      {hotspot.intensity_ppb.toLocaleString('en-US')} ppb
                    </td>
                    <td className="px-3 py-3 text-gray-900 dark:text-gray-100">
                      {formatUtc(hotspot.detected_at)}
                    </td>
                    <td className="px-3 py-3 text-gray-900 dark:text-gray-100">
                      {hotspot.source}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => void handleCopy(hotspot)}
                        aria-label={copyAriaLabel(hotspot)}
                        className="rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400 dark:hover:bg-emerald-900/50 transition-colors"
                      >
                        {copyLabel(hotspot)}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p aria-live="polite" className="sr-only">
            {copyFeedback?.status === 'copied'
              ? 'Coordinates copied.'
              : copyFeedback?.status === 'failed'
                ? 'Copy failed.'
                : ''}
          </p>
        </>
      )}
    </section>
  );
}