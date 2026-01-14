/**
 * API Configuration
 *
 * Single source of truth for API URLs and settings.
 * In dev mode, Vite proxy handles API calls.
 * In production, set VITE_API_URL to the backend URL.
 */

// API base URL - empty string uses Vite proxy in dev mode
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Helper to get full URL for downloads (needs absolute URL)
export function getApiBaseUrl(): string {
  return API_BASE_URL || window.location.origin;
}

// API endpoints prefixes
export const API_ENDPOINTS = {
  transcribe: '/transcribe',
  auth: '/auth',
  admin: '/api/admin',
  manager: '/api/manager',
  domains: '/api/domains',
} as const;
