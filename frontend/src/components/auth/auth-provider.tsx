'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getCurrentUser, postLogin, postLogout } from '@/lib/api';
import type { AuthUser } from '@/lib/types';

type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

interface AuthContextType {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);
  const queryClient = useQueryClient();

  // Bootstrapping auth on mount
  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        setUser(u);
        setStatus('authenticated');
      })
      .catch(() => {
        setUser(null);
        setStatus('anonymous');
      });
  }, []);

  // Listen for 401 events from the API client
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setStatus('anonymous');
      queryClient.clear();
    };
    window.addEventListener('odrm:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('odrm:unauthorized', handleUnauthorized);
  }, [queryClient]);

  const login = async (email: string, password: string) => {
    const res = await postLogin(email, password);
    setUser(res.user);
    setStatus('authenticated');
  };

  const logout = async () => {
    try {
      await postLogout();
    } finally {
      setUser(null);
      setStatus('anonymous');
      queryClient.clear();
    }
  };

  return (
    <AuthContext.Provider value={{ status, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}