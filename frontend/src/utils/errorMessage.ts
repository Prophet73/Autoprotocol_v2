import axios from 'axios';

/**
 * Extract human-readable error message from an unknown catch error.
 * Handles Axios errors (response.data.detail) and generic Error objects.
 */
export function getApiErrorMessage(err: unknown, fallback = 'Ошибка'): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || fallback;
  }
  if (err instanceof Error) {
    return err.message || fallback;
  }
  return fallback;
}

/**
 * Get HTTP status code from an unknown catch error.
 * Returns undefined if not an Axios error or no response.
 */
export function getApiErrorStatus(err: unknown): number | undefined {
  if (axios.isAxiosError(err)) {
    return err.response?.status;
  }
  return undefined;
}
