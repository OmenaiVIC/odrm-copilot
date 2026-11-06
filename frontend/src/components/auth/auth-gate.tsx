'use client';

import { useAuth } from './auth-provider';
import { LoginForm } from './login-form';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
        <p className="text-gray-500 animate-pulse">Loading...</p>
      </div>
    );
  }

  if (status === 'anonymous') {
    return <LoginForm />;
  }

  return <>{children}</>;
}