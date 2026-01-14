import { describe, it, expect } from 'vitest';
import type {
  CurrentUser,
  AdminUser,
  LoginResponse,
  CreateUserRequest,
} from './user';

describe('User Types', () => {
  describe('CurrentUser', () => {
    it('should accept valid user object', () => {
      const user: CurrentUser = {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        role: 'user',
        domain: null,
        is_superuser: false,
        tenant_id: null,
      };

      expect(user.id).toBe(1);
      expect(user.email).toBe('test@example.com');
      expect(user.role).toBe('user');
    });

    it('should allow null for optional fields', () => {
      const user: CurrentUser = {
        id: 1,
        email: 'test@example.com',
        username: null,
        full_name: null,
        role: 'admin',
        domain: null,
        is_superuser: true,
        tenant_id: null,
      };

      expect(user.username).toBeNull();
      expect(user.full_name).toBeNull();
    });
  });

  describe('AdminUser', () => {
    it('should include audit fields', () => {
      const user: AdminUser = {
        id: 1,
        email: 'admin@example.com',
        full_name: 'Admin User',
        is_active: true,
        is_superuser: true,
        role: 'admin',
        domain: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      expect(user.is_active).toBe(true);
      expect(user.created_at).toBeDefined();
      expect(user.updated_at).toBeDefined();
    });
  });

  describe('LoginResponse', () => {
    it('should have required token fields', () => {
      const response: LoginResponse = {
        access_token: 'jwt-token-here',
        token_type: 'bearer',
        expires_in: 3600,
      };

      expect(response.access_token).toBe('jwt-token-here');
      expect(response.token_type).toBe('bearer');
      expect(response.expires_in).toBe(3600);
    });
  });

  describe('CreateUserRequest', () => {
    it('should require email and password', () => {
      const request: CreateUserRequest = {
        email: 'new@example.com',
        password: 'securepassword123',
      };

      expect(request.email).toBe('new@example.com');
      expect(request.password).toBe('securepassword123');
    });

    it('should allow optional fields', () => {
      const request: CreateUserRequest = {
        email: 'new@example.com',
        password: 'securepassword123',
        full_name: 'New User',
        role: 'manager',
        domain: 'construction',
        is_superuser: false,
      };

      expect(request.full_name).toBe('New User');
      expect(request.role).toBe('manager');
    });
  });
});
