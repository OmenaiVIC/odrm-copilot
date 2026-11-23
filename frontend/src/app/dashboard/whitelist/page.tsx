import type { Metadata } from 'next';
import { AuthGate } from '@/components/auth/auth-gate';
import { WhitelistPage } from '@/components/whitelist/whitelist-page';

export const metadata: Metadata = {
  title: 'Public-Good Whitelist | Valoris',
  description: 'Apply for public-good access to the ODRM dashboard.',
};

export default function WhitelistRoute() {
  return (
    <AuthGate>
      <WhitelistPage />
    </AuthGate>
  );
}