import * as React from 'react'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '@/lib/api'

export type UserRole = 'Developer' | 'Reviewer' | 'Admin';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  name: string;
  username: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch (error) {
      // Not authenticated — clear user state silently
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();

    // When api.ts broadcasts an unauthorized event (e.g. cookie expired),
    // clear out the local user state. ProtectedRoute will then redirect to /login.
    const handleUnauthorized = () => {
      setUser(null);
      setIsLoading(false);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = async (username: string, password: string) => {
    // The backend expects application/x-www-form-urlencoded for OAuth2PasswordRequestForm
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const { data } = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    // The backend sets an HttpOnly cookie AND returns the token in the body.
    // Store the token in localStorage as a fallback Authorization header source
    // for environments where cross-origin cookies may be blocked (dev mismatches).
    if (data?.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      // Attach it immediately to the axios instance default headers
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
    }

    // Cookie is now set (and/or token attached to headers); fetch user to populate context
    await fetchUser();
  };

  const register = async (username: string, email: string, password: string) => {
    await api.post('/auth/register', { username, email, password });
    // Automatically log in the user after registration
    await login(username, password);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      // Clear the stored token and axios default header
      localStorage.removeItem('auth_token');
      delete api.defaults.headers.common['Authorization'];
      setUser(null);
    }
  };

  // On startup, restore Authorization header from localStorage if a session token exists.
  // This handles the case where cookies are blocked but the token was previously stored.
  useEffect(() => {
    const stored = localStorage.getItem('auth_token');
    if (stored) {
      api.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
    }
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
