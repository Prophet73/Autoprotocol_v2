import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DomainSwitcher } from '../DomainSwitcher';
import { useAuthStore } from '../../stores/authStore';
import type { CurrentUser } from '../../types/user';

vi.mock('../../api/client', () => ({
  getDomains: vi.fn().mockResolvedValue([
    { id: 'construction', name: 'ДПУ', meeting_types_count: 3 },
    { id: 'dct', name: 'ДЦТ', meeting_types_count: 2 },
  ]),
}));

vi.mock('../../api/adminApi', () => ({
  authApi: {
    setActiveDomain: vi.fn(),
  },
}));

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

const initialState = useAuthStore.getState();

describe('DomainSwitcher', () => {
  beforeEach(() => {
    useAuthStore.setState(initialState, true);
  });

  it('should display current domain name', async () => {
    useAuthStore.setState({
      user: fakeUser,
      isAuthenticated: true,
      token: 'fake-token',
    });

    render(<DomainSwitcher />);

    const domainButton = await screen.findByText('ДПУ');
    expect(domainButton).toBeInTheDocument();
  });
});
