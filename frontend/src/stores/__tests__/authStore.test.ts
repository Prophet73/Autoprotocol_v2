import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../authStore';
import type { CurrentUser } from '../../types/user';

const initialState = useAuthStore.getState();

const fakeUser: CurrentUser = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  full_name: 'Test User',
  role: 'user',
  domain: 'construction',
  domains: ['construction'],
  active_domain: 'construction',
  is_superuser: false,
  tenant_id: null,
};

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState(initialState, true);
  });

  it('should have isAuthenticated=false and token=null on init', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.token).toBeNull();
  });

  it('login should set token, user and isAuthenticated', () => {
    useAuthStore.getState().login('fake-token-123', fakeUser);

    const state = useAuthStore.getState();
    expect(state.token).toBe('fake-token-123');
    expect(state.user).toEqual(fakeUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('login with refreshToken should store it', () => {
    useAuthStore.getState().login('token', fakeUser, 'refresh-token');

    const state = useAuthStore.getState();
    expect(state.refreshToken).toBe('refresh-token');
  });

  it('logout should clear state', () => {
    useAuthStore.getState().login('token', fakeUser);
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
