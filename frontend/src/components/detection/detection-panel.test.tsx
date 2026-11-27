import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { DetectionPanel } from './detection-panel';

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({
    children,
    position,
  }: {
    children: ReactNode;
    position: [number, number];
  }) => (
    <div data-testid="map-marker" data-lat={position[0]} data-lng={position[1]}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: ReactNode }) => (
    <div data-testid="map-popup">{children}</div>
  ),
}));

vi.mock('leaflet/dist/leaflet.css', () => ({}));

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

    expect((await screen.findAllByText('mock-nogiet-001')).length).toBeGreaterThan(0);
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

  it('renders the map when hotspots are loaded', async () => {
    renderPanel();

    await screen.findAllByText('mock-nogiet-001');
    await waitFor(() =>
      expect(screen.getByTestId('map-container')).toBeInTheDocument(),
    );
  });

  it('renders one marker per hotspot at the correct coordinates', async () => {
    renderPanel();

    await screen.findAllByText('mock-nogiet-001');
    const markers = await waitFor(() => screen.getAllByTestId('map-marker'));
    expect(markers).toHaveLength(2);
    expect(markers[0]).toHaveAttribute('data-lat', '4.8156');
    expect(markers[0]).toHaveAttribute('data-lng', '7.0498');
    expect(markers[1]).toHaveAttribute('data-lat', '4.8167');
    expect(markers[1]).toHaveAttribute('data-lng', '7.0333');
  });
});