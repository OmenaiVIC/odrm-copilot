import type { Metadata } from 'next';
import { AuthGate } from '@/components/auth/auth-gate';
import { AdminWhitelistPage } from '@/components/whitelist/admin-whitelist-page';

export const metadata: Metadata = {
  title: 'Whitelist Review | Valoris',
  description: 'Review public-good access requests.',
};

export default function AdminWhitelistRoute() {
  return (
    <AuthGate>
      <AdminWhitelistPage />
    </AuthGate>
  );
}