/**
 * User Types
 *
 * Shared type definitions for user-related data.
 */

/**
 * Current authenticated user info (from /auth/me)
 */
export interface CurrentUser {
  id: number;
  email: string;
  username: string | null;
  full_name: string | null;
  role: string;
  domain: string | null;  // Legacy single domain
  domains: string[];  // Multiple domains
  active_domain: string | null;  // Currently selected domain
  is_superuser: boolean;
  tenant_id: number | null;
}

/**
 * User record from admin panel (includes audit fields)
 */
export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role: string;
  domain: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * User list response from admin API
 */
export interface UserListResponse {
  users: AdminUser[];
  total: number;
}

/**
 * Login response
 */
export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

/**
 * Create user request
 */
export interface CreateUserRequest {
  email: string;
  password: string;
  full_name?: string;
  role?: string;
  domain?: string;
  is_superuser?: boolean;
}

/**
 * Assign role request
 */
export interface AssignRoleRequest {
  user_id: number;
  role: string;
  domain?: string;
}
