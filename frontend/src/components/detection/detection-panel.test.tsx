import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DetectionPanel } from './detection-panel';

const HOTSPOTS = [
  {
    id: 'mock-nogiet-001',
    latitude: 4.8156,
    longitude: 7.0498,
    intensity_ppb: 2450.0,
    detected_at: '2026-01-05T09:30:00Z',
    source: 'mock_nogiet',
  },
  {
    id: 'mock-nogiet-005',
    latitude: 4.8167,
    longitude: 7.0333,
    intensity_ppb: 2280.0,
    detected_at: '2026-02-10T11:20:00Z',
    source: 'mock_nogiet',
  },
];

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DetectionPanel />
    </QueryClientProvider>,
  );
}

describe('DetectionPanel', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => HOTSPOTS,
      }),
    );
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('renders hotspot rows from the detection endpoint', async () => {
    renderPanel();

    expect(await screen.findByText('mock-nogiet-001')).toBeInTheDocument();
    expect(screen.getByText('mock-nogiet-005')).toBeInTheDocument();
    expect(screen.getByText('SYNTHETIC DATA')).toBeInTheDocument();
    expect(screen.getByText('4.8156, 7.0498')).toBeInTheDocument();
    expect(screen.getByText('2,450 ppb')).toBeInTheDocument();
    expect(screen.getByText('2026-01-05 09:30 UTC')).toBeInTheDocument();
    expect(screen.getAllByText('mock_nogiet')).toHaveLength(2);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/detection/hotspots'),
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('copies coordinates and shows confirmation', async () => {
    renderPanel();

    const button = await screen.findByRole('button', {
      name: 'Copy coordinates for mock-nogiet-001',
    });
    fireEvent.click(button);

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        '4.8156, 7.0498',
      ),
    );
    expect(await screen.findByText('Copied')).toBeInTheDocument();
  });
});
