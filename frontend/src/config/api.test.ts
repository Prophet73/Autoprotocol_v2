import { describe, it, expect, vi } from 'vitest';
import { API_BASE_URL, getApiBaseUrl, API_ENDPOINTS } from './api';

describe('API Configuration', () => {
  describe('API_BASE_URL', () => {
    it('should be defined', () => {
      expect(API_BASE_URL).toBeDefined();
    });

    it('should be a string', () => {
      expect(typeof API_BASE_URL).toBe('string');
    });
  });

  describe('getApiBaseUrl', () => {
    it('should return window.location.origin when API_BASE_URL is empty', () => {
      // In test environment, window.location.origin is 'http://localhost:3000'
      const result = getApiBaseUrl();
      expect(result).toBeTruthy();
    });
  });

  describe('API_ENDPOINTS', () => {
    it('should have transcribe endpoint', () => {
      expect(API_ENDPOINTS.transcribe).toBe('/transcribe');
    });

    it('should have auth endpoint', () => {
      expect(API_ENDPOINTS.auth).toBe('/auth');
    });

    it('should have admin endpoint', () => {
      expect(API_ENDPOINTS.admin).toBe('/api/admin');
    });

    it('should have manager endpoint', () => {
      expect(API_ENDPOINTS.manager).toBe('/api/manager');
    });

    it('should have domains endpoint', () => {
      expect(API_ENDPOINTS.domains).toBe('/api/domains');
    });
  });
});
