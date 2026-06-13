import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem('access_token'),
  token: localStorage.getItem('access_token'),
  
  setToken: (token: string) => {
    localStorage.setItem('access_token', token);
    set({ isAuthenticated: true, token });
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
    set({ isAuthenticated: false, token: null });
  },
}));
