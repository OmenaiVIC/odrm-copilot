import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReportDownload } from './report-download';
import { downloadReport, type ReportDownload as ReportDownloadResult } from '@/lib/api';
import type { TeaRequest } from '@/lib/types';

vi.mock('@/lib/api', () => ({
  downloadReport: vi.fn(),
}));

const request: TeaRequest = {
  conditions: {
    temperature_c: 800,
    pressure_bar: 10,
    ch4_o2_ratio: 2,
    co2_ch4_ratio: 0.5,
    h2o_ch4_ratio: 0.2,
    ghsv_per_h: 5000,
    catalyst: 'Ni/Al2O3',
  },
  assumptions: {
    ch4_feed_kmol_per_h: 100,
    natural_gas_price_usd_per_mmbtu: 3.25,
    syngas_price_usd_per_kmol: 4.1,
    carbon_credit_price_usd_per_tonne_co2e: 28.5,
    co2_utilization_fraction: 0,
    capex_usd: 5000000,
  },
};

const download: ReportDownloadResult = {
  blob: new Blob(['%PDF-'], { type: 'application/pdf' }),
  filename: 'odrm-esg-report-abc.pdf',
  reportId: 'abc',
  sha256: 'a'.repeat(64),
  generatedAt: '2026-11-06T12:00:00Z',
};

function renderWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportDownload request={request} />
    </QueryClientProvider>
  );
}

describe('ReportDownload', () => {
  const createObjectURL = vi.fn(() => 'blob:report');
  const revokeObjectURL = vi.fn();
  let clickedHref: string | null;
  let clickedDownload: string | null;

  beforeEach(() => {
    vi.resetAllMocks();
    clickedHref = null;
    clickedDownload = null;
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: revokeObjectURL,
    });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(
      function (this: HTMLAnchorElement) {
        clickedHref = this.href;
        clickedDownload = this.download;
      }
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders an accessible secondary button that does not submit a form', () => {
    renderWithClient();

    const button = screen.getByRole('button', { name: 'Download ESG Report' });
    expect(button).toHaveAttribute('type', 'button');
  });

  it('downloads the server filename and revokes the object URL', async () => {
    vi.mocked(downloadReport).mockResolvedValueOnce(download);
    renderWithClient();

    fireEvent.click(screen.getByRole('button', { name: 'Download ESG Report' }));

    await screen.findByText('Report downloaded.');
    expect(downloadReport).toHaveBeenCalledWith(request);
    expect(createObjectURL).toHaveBeenCalledWith(download.blob);
    expect(clickedDownload).toBe('odrm-esg-report-abc.pdf');
    expect(clickedHref).toBe('blob:report');
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report');
    expect(screen.getByRole('status')).toHaveTextContent('Report downloaded.');
  });

  it('disables the button and announces progress while generating', async () => {
    let resolveDownload!: (value: ReportDownloadResult) => void;
    vi.mocked(downloadReport).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveDownload = resolve;
      })
    );
    renderWithClient();

    fireEvent.click(screen.getByRole('button', { name: 'Download ESG Report' }));

    const button = await screen.findByRole('button', { name: 'Generating PDF...' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');

    resolveDownload(download);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Download ESG Report' })).toBeEnabled();
    });
  });

  it('shows an accessible alert when report generation fails', async () => {
    vi.mocked(downloadReport).mockRejectedValueOnce(new Error('boom'));
    renderWithClient();

    fireEvent.click(screen.getByRole('button', { name: 'Download ESG Report' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Report generation failed. Please try again.');
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Download ESG Report' })).toBeEnabled();
  });
});
