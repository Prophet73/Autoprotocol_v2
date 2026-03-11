import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { CurrentUser } from '../types/user';

// Re-export for backwards compatibility
export type User = CurrentUser;

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  // Actions
  setToken: (token: string) => void;
  setTokens: (token: string, refreshToken: string) => void;
  login: (token: string, user: User, refreshToken?: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setToken: (token: string) => {
        set({ token });
      },

      setTokens: (token: string, refreshToken: string) => {
        set({ token, refreshToken });
      },

      login: (token: string, user: User, refreshToken?: string) => {
        set({ token, refreshToken: refreshToken ?? null, user, isAuthenticated: true });
      },

      logout: () => {
        set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
      },

      setUser: (user: User) => {
        set({ user });
      },
    }),
    {
      name: 'whisperx-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
