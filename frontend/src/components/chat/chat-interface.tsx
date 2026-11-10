'use client';

import { useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ApiError, postChat } from '@/lib/api';
import type { ChatErrorDetail, ChatMessage, TeaResponse } from '@/lib/types';
import { ResultsPanel } from '@/components/dashboard/results-panel';

const MAX_MESSAGE_CHARS = 2_000;
const MAX_HISTORY_MESSAGES = 10;

interface ChatEntry {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  result: TeaResponse | null;
}

interface UiError {
  title: string;
  message: string;
  requestId?: string;
  retryable: boolean;
  field?: string;
  minimum?: number | null;
  maximum?: number | null;
  missingFields?: string[];
}

const GUARDRAIL_CODES = new Set([
  'BOUNDS_VIOLATION',
  'UNKNOWN_CATALYST',
  'MISSING_ARGUMENTS',
  'INVALID_ARGUMENTS',
  'TEA_REJECTED',
]);

function structuredDetail(detail: unknown): ChatErrorDetail | null {
  if (!detail || typeof detail !== 'object') {
    return null;
  }
  const candidate = detail as Record<string, unknown>;
  if (typeof candidate.code !== 'string' || typeof candidate.message !== 'string') {
    return null;
  }
  return candidate as unknown as ChatErrorDetail;
}

function unwrapDetail(detail: unknown): unknown {
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    return (detail as { detail: unknown }).detail;
  }
  return detail;
}

function standardValidationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) {
    return null;
  }
  const first = detail[0] as { msg?: unknown } | null;
  return typeof first?.msg === 'string' ? first.msg : null;
}

function describeError(error: unknown): UiError {
  if (error instanceof ApiError) {
    const rawDetail = unwrapDetail(error.detail);
    const detail = structuredDetail(rawDetail);
    if (detail) {
      if (GUARDRAIL_CODES.has(detail.code)) {
        return {
          title: 'Request needs attention',
          message: detail.message,
          requestId: detail.request_id,
          retryable: false,
          field: detail.field ?? undefined,
          minimum: detail.minimum,
          maximum: detail.maximum,
          missingFields: detail.missing_fields,
        };
      }
      return {
        title:
          detail.code === 'AGENT_UNAVAILABLE' || detail.code === 'TEA_UNAVAILABLE'
            ? 'Screening temporarily unavailable'
            : 'Screening failed',
        message:
          detail.code === 'AGENT_UNAVAILABLE' || detail.code === 'TEA_UNAVAILABLE'
            ? `${detail.message} Please try again in a moment.`
            : detail.message,
        requestId: detail.request_id,
        retryable:
          error.status === 503 ||
          detail.code === 'AGENT_UNAVAILABLE' ||
          detail.code === 'TEA_UNAVAILABLE',
      };
    }

    if (error.status === 422) {
      return {
        title: 'Request needs attention',
        message: standardValidationMessage(rawDetail) ?? 'Check the message and try again.',
        retryable: false,
      };
    }

    return {
      title: error.status === 503 ? 'Screening temporarily unavailable' : 'Screening failed',
      message:
        error.status === 503
          ? 'The screening service is unavailable. Please try again in a moment.'
          : 'The screening service could not complete this request.',
      retryable: error.status >= 500,
    };
  }

  return {
    title: 'Screening temporarily unavailable',
    message: 'Could not reach the screening service. Check your connection and try again.',
    retryable: true,
  };
}

export function ChatInterface() {
  const [message, setMessage] = useState('');
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<UiError | null>(null);
  const nextId = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmed = message.trim();
  const isTooLong = trimmed.length > MAX_MESSAGE_CHARS;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending || trimmed.length === 0 || isTooLong) {
      return;
    }

    const history: ChatMessage[] = entries.map(({ role, content }) => ({
      role,
      content,
    }));
    while (history.at(-1)?.role === 'user') {
      history.pop();
    }
    history.push({ role: 'user', content: trimmed });
    const requestMessages = history.slice(-MAX_HISTORY_MESSAGES);

    nextId.current += 1;
    const userEntry: ChatEntry = {
      id: nextId.current,
      role: 'user',
      content: trimmed,
      result: null,
    };

    setEntries((previous) => [...previous, userEntry]);
    setError(null);
    setIsPending(true);

    try {
      const response = await postChat(requestMessages);
      nextId.current += 1;
      setEntries((previous) => [
        ...previous,
        {
          id: nextId.current,
          role: 'assistant',
          content: response.reply,
          result: response.status === 'ok' ? response.result : null,
        },
      ]);
      setMessage('');
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setIsPending(false);
      textareaRef.current?.focus();
    }
  };

  return (
    <section className="max-w-7xl mx-auto px-4 pb-8 md:px-8 md:pb-12">
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          4. Valoris AI Assistant
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Describe the reactor conditions, feed, prices, and capex in plain language. This is a
          screening result, not investment advice.
        </p>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          The assistant uses recent messages from this tab; history is not saved across refreshes.
        </p>

        <div
          className="mt-4 flex flex-col gap-3"
          aria-live="polite"
          aria-busy={isPending}
        >
          {entries.map((entry) => (
            <div
              key={entry.id}
              className={
                entry.role === 'user'
                  ? 'self-end rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-950 dark:bg-emerald-900/30 dark:text-emerald-100 max-w-[85%]'
                  : 'self-start rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-800 dark:bg-zinc-800 dark:text-gray-200 max-w-[85%]'
              }
            >
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">
                {entry.role === 'user' ? 'You' : 'Screening assistant'}
              </p>
              
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {entry.content}
                </ReactMarkdown>
              </div>

              {entry.result && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm font-medium text-emerald-600 hover:underline dark:text-emerald-400">
                    View screening result
                  </summary>
                  <div className="mt-4">
                    <ResultsPanel data={entry.result} isLoading={false} isError={false} />
                  </div>
                </details>
              )}
            </div>
          ))}

          {isPending && (
            <p className="self-start rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-500 dark:bg-zinc-800 dark:text-gray-400">
              Screening in progress...
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
            >
              <p className="font-semibold">Error: {error.title}</p>
              <p className="mt-1">{error.message}</p>
              {error.field && (
                <p className="mt-1">
                  Field: <span className="font-mono">{error.field}</span>
                  {typeof error.minimum === 'number' && typeof error.maximum === 'number'
                    ? ` (allowed range ${error.minimum} to ${error.maximum})`
                    : ''}
                </p>
              )}
              {error.missingFields && error.missingFields.length > 0 && (
                <p className="mt-1">Missing: {error.missingFields.join(', ')}</p>
              )}
              {error.requestId && <p className="mt-1">Request ID: {error.requestId}</p>}
              {error.retryable && <p className="mt-1">You can retry when the service is available.</p>}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
          <label
            htmlFor="chat-message"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Message
          </label>
          <textarea
            id="chat-message"
            ref={textareaRef}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            rows={4}
            maxLength={MAX_MESSAGE_CHARS}
            placeholder="At 750 C, 5 bar, CH4:O2 2.0, ... what is the conversion, yield, and payback?"
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 dark:border-zinc-700 dark:bg-zinc-950 dark:text-gray-100"
          />
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {trimmed.length} / {MAX_MESSAGE_CHARS} characters. Enter submits; Shift+Enter adds a
              new line.
            </p>
            <button
              type="submit"
              disabled={isPending || trimmed.length === 0 || isTooLong}
              className="rounded-lg bg-emerald-600 px-5 py-2 font-semibold text-white shadow-sm transition-colors hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50"
            >
              {isPending ? 'Screening...' : 'Ask Assistant'}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}