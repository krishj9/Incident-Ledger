/**
 * Auth context for the Director Portal.
 * Web-only: uses localStorage for token persistence.
 * Shared auth logic mirrors mobile AuthContext pattern.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import { OpenAPI } from '@incident-ledger/api-client';

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export type UserProfile = {
  user_id: string;
  display_name: string;
  role: string;
  center_id: string;
  center_name: string;
  center_code: string;
  center_timezone: string;
};

type AuthContextType = {
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'incident_ledger_director_token';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Configure API base URL
  OpenAPI.BASE = API_BASE;

  async function loadProfile(tok: string) {
    try {
      OpenAPI.TOKEN = tok;
      const res = await fetch(`${API_BASE}/v1/me`, {
        headers: { Authorization: `Bearer ${tok}` },
      });
      if (res.ok) {
        const profile = await res.json();
        setUser(profile);
      }
    } catch (e) {
      console.error('Failed to load user profile', e);
    }
  }

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
    if (stored) {
      setToken(stored);
      OpenAPI.TOKEN = stored;
      loadProfile(stored).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const signIn = async (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    OpenAPI.TOKEN = newToken;
    await loadProfile(newToken);
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    OpenAPI.TOKEN = undefined;
  };

  return (
    <AuthContext.Provider value={{ token, user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
