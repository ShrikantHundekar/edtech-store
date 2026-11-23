import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { api } from '../services/api';
import type { User, LoginCredentials, RegisterData, AuthResponse } from '../types/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUserProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user_profile');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const syncAuthState = (newUser: User | null, newTokens?: { access: string; refresh: string }) => {
    setUser(newUser);
    if (newUser) {
      localStorage.setItem('user_profile', JSON.stringify(newUser));
    } else {
      localStorage.removeItem('user_profile');
    }

    if (newTokens) {
      setToken(newTokens.access);
      localStorage.setItem('access_token', newTokens.access);
      localStorage.setItem('refresh_token', newTokens.refresh);
    }
  };

  const refreshUserProfile = async () => {
    try {
      const response = await api.get<User>('/auth/me/');
      syncAuthState(response.data);
    } catch {
      // If token expired and refresh fails, clear state
      syncAuthState(null);
      setToken(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  };

  // Initial persistent session validation on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (storedToken) {
        await refreshUserProfile();
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const response = await api.post<AuthResponse>('/auth/login/', credentials);
    const { user: loggedInUser, tokens } = response.data;
    syncAuthState(loggedInUser, tokens);
  };

  const register = async (data: RegisterData) => {
    const response = await api.post<AuthResponse>('/auth/register/', data);
    const { user: registeredUser, tokens } = response.data;
    syncAuthState(registeredUser, tokens);
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    try {
      if (refreshToken) {
        await api.post('/auth/logout/', { refresh: refreshToken });
      }
    } catch {
      // Graceful logout even if backend call fails
    } finally {
      syncAuthState(null);
      setToken(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isAdmin: user?.role === 'ADMIN',
    isLoading,
    login,
    register,
    logout,
    refreshUserProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
