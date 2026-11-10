import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatInterface } from './chat-interface';
import type { TeaResponse } from '@/lib/types';

global.fetch = vi.fn();

const TEA_RESULT: TeaResponse = {
  predictions: { ch4_conversion: 0.862, syngas_yield_mol_per_mol_ch4: 2.31 },
  model_versions: { ch4_conversion: 'v1', syngas_yield_mol_per_mol_ch4: 'v1' },
  financials: {
    syngas_kmol_per_day: 100,
    syngas_nm3_per_day: 100,
    syngas_revenue_usd_per_day: 100,
    co2_consumed_tonnes_per_day: 10,
    carbon_credit_value_usd_per_day: 100,
    total_revenue_usd_per_day: 200,
    feed_cost_usd_per_day: 50,
    opex_usd_per_day: 10,
    net_cash_flow_usd_per_day: 140,
    annual_net_cash_flow_usd: 46_200,
    roi_pct: 15,
    payback_years: 2.0,
    currency: 'USD',
  },
  warnings: [],
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: async () => body,
  } as Response;
}

function submit(message: string) {
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: message } });
  fireEvent.click(screen.getByRole('button', { name: /Ask Assistant/i }));
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders the reply and authoritative result data', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        status: 'ok',
        reply: 'The screening completed.',
        result: TEA_RESULT,
        request_id: 'req-1',
      })
    );

    render(<ChatInterface />);
    submit('Run the screening.');

    expect(await screen.findByText('The screening completed.')).toBeInTheDocument();
    expect(screen.getByText('View screening result')).toBeInTheDocument();
    expect(screen.getByText('86.20%')).toBeInTheDocument();
    expect(screen.getByText('15.00%')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat'),
      expect.objectContaining({
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Run the screening.' }],
        }),
      })
    );
  });

  it('renders needs_input without a result panel', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        status: 'needs_input',
        reply: 'Please provide the capex.',
        result: null,
        request_id: 'req-2',
      })
    );

    render(<ChatInterface />);
    submit('Run it.');

    expect(await screen.findByText('Please provide the capex.')).toBeInTheDocument();
    expect(screen.queryByText('View screening result')).not.toBeInTheDocument();
  });

  it('sends prior completed turns with the next message', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'ok',
          reply: 'At 750 C the payback is 2.0 years.',
          result: TEA_RESULT,
          request_id: 'req-1',
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'ok',
          reply: 'At 800 C the payback is 1.9 years.',
          result: TEA_RESULT,
          request_id: 'req-2',
        })
      );

    render(<ChatInterface />);
    submit('Run the screening at 750 C.');
    expect(await screen.findByText('At 750 C the payback is 2.0 years.')).toBeInTheDocument();

    submit('Now raise the temperature to 800 C and rerun.');
    expect(await screen.findByText('At 800 C the payback is 1.9 years.')).toBeInTheDocument();

    expect(vi.mocked(fetch).mock.calls[1][1]?.body).toBe(
      JSON.stringify({
        messages: [
          { role: 'user', content: 'Run the screening at 750 C.' },
          { role: 'assistant', content: 'At 750 C the payback is 2.0 years.' },
          { role: 'user', content: 'Now raise the temperature to 800 C and rerun.' },
        ],
      })
    );
  });

  it('excludes a failed unanswered turn from the next request history', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(
          {
            detail: {
              code: 'AGENT_UNAVAILABLE',
              message: 'The screening assistant is unavailable.',
              request_id: 'req-1',
            },
          },
          503
        )
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'needs_input',
          reply: 'Please provide the capex.',
          result: null,
          request_id: 'req-2',
        })
      );

    render(<ChatInterface />);
    submit('Run it.');
    expect(await screen.findByText(/Screening temporarily unavailable/)).toBeInTheDocument();

    submit('Run it again.');
    expect(await screen.findByText('Please provide the capex.')).toBeInTheDocument();

    expect(vi.mocked(fetch).mock.calls[1][1]?.body).toBe(
      JSON.stringify({
        messages: [{ role: 'user', content: 'Run it again.' }],
      })
    );
  });

  it('caps the request history to the newest ten messages', async () => {
    render(<ChatInterface />);

    for (let index = 0; index < 5; index += 1) {
      vi.mocked(fetch).mockResolvedValueOnce(
        jsonResponse({
          status: 'needs_input',
          reply: `Reply ${index}.`,
          result: null,
          request_id: `req-${index}`,
        })
      );
      submit(`Message ${index}.`);
      expect(await screen.findByText(`Reply ${index}.`)).toBeInTheDocument();
    }

    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        status: 'needs_input',
        reply: 'Final reply.',
        result: null,
        request_id: 'req-final',
      })
    );
    submit('Message 5.');
    expect(await screen.findByText('Final reply.')).toBeInTheDocument();

    const body = JSON.parse(String(vi.mocked(fetch).mock.calls[5][1]?.body)) as {
      messages: Array<{ role: string; content: string }>;
    };

    expect(body.messages).toHaveLength(10);
    expect(body.messages[0]).toEqual({ role: 'assistant', content: 'Reply 0.' });
    expect(body.messages[9]).toEqual({ role: 'user', content: 'Message 5.' });
  });

  it('shows a structured guardrail error and preserves the composer', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            code: 'BOUNDS_VIOLATION',
            message: 'conditions.temperature_c must be between 500 and 1000.',
            field: 'conditions.temperature_c',
            value: 1500,
            minimum: 500,
            maximum: 1000,
            request_id: 'req-3',
          },
        },
        422
      )
    );

    render(<ChatInterface />);
    submit('Run at 1500 C.');

    expect(await screen.findByText(/Request needs attention/)).toBeInTheDocument();
    expect(
      screen.getByText('conditions.temperature_c must be between 500 and 1000.')
    ).toBeInTheDocument();
    expect(screen.getByText(/allowed range 500 to 1000/)).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toHaveValue('Run at 1500 C.');
  });

  it('shows a retryable unavailable error without a result', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            code: 'AGENT_UNAVAILABLE',
            message: 'The screening assistant is unavailable.',
            request_id: 'req-4',
          },
        },
        503
      )
    );

    render(<ChatInterface />);
    submit('Run it.');

    expect(await screen.findByText(/Screening temporarily unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/You can retry when the service is available/)).toBeInTheDocument();
    expect(screen.queryByText('View screening result')).not.toBeInTheDocument();
  });

  it('does not submit empty, whitespace-only, or over-limit messages', () => {
    render(<ChatInterface />);
    const button = screen.getByRole('button', { name: /Ask Assistant/i });
    const textarea = screen.getByLabelText('Message');

    expect(button).toBeDisabled();
    fireEvent.change(textarea, { target: { value: '   ' } });
    expect(button).toBeDisabled();

    fireEvent.change(textarea, { target: { value: 'x'.repeat(2_001) } });
    expect(button).toBeDisabled();
    fireEvent.click(button);

    expect(fetch).not.toHaveBeenCalled();
  });

  it('prevents duplicate submissions while a request is pending', async () => {
    let resolveRequest: ((response: Response) => void) | undefined;
    vi.mocked(fetch).mockReturnValueOnce(
      new Promise<Response>((resolve) => {
        resolveRequest = resolve;
      })
    );

    render(<ChatInterface />);
    submit('Run it.');

    await waitFor(() => {
      expect(screen.getByText('Screening in progress...')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Screening.../i }));
    expect(fetch).toHaveBeenCalledTimes(1);

    resolveRequest?.(
      jsonResponse({
        status: 'needs_input',
        reply: 'Please provide capex.',
        result: null,
        request_id: 'req-5',
      })
    );

    expect(await screen.findByText('Please provide capex.')).toBeInTheDocument();
  });
});
