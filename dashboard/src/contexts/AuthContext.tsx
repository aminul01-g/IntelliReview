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
    // Guard: skip the network call entirely when there is no stored token.
    // This prevents a guaranteed 401 on /auth/me (and the subsequent
    // /auth/refresh retry) when the user has never logged in.
    const storedToken = localStorage.getItem('auth_token');
    if (!storedToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

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
    // Fetch user on mount. The request interceptor in api.ts automatically
    // attaches the token from localStorage to every outgoing request, so
    // there is no race condition — the token is read at request-time.
    fetchUser();

    // When api.ts broadcasts an unauthorized event (e.g. token expired and
    // refresh failed), clear out the local user state so ProtectedRoute
    // redirects to /login.
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
    // Store the token in localStorage — the request interceptor in api.ts
    // reads it on every request, so no need to set axios defaults here.
    if (data?.access_token) {
      localStorage.setItem('auth_token', data.access_token);
    }

    // Token is now stored; fetch user to populate context
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
      // Clear the stored token so the request interceptor stops attaching it
      localStorage.removeItem('auth_token');
      setUser(null);
    }
  };

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

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context as AuthContextType;
};
