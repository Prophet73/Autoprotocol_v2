/**
 * Guest ID management for anonymous users.
 *
 * Generates and persists a unique guest identifier in localStorage.
 * Used for tracking upload history for anonymous users via X-Guest-ID header.
 */

const GUEST_ID_KEY = 'whisperx-guest-id';

/**
 * Get or generate guest ID.
 * If no ID exists in localStorage, generates a new UUID.
 *
 * @returns Guest UUID string
 */
export function getGuestId(): string {
  let guestId = localStorage.getItem(GUEST_ID_KEY);

  if (!guestId) {
    guestId = crypto.randomUUID();
    localStorage.setItem(GUEST_ID_KEY, guestId);
  }

  return guestId;
}

/**
 * Clear guest ID from localStorage.
 * Useful when user logs in or explicitly clears history.
 */
export function clearGuestId(): void {
  localStorage.removeItem(GUEST_ID_KEY);
}

/**
 * Check if guest ID exists.
 *
 * @returns true if guest ID is set
 */
export function hasGuestId(): boolean {
  return localStorage.getItem(GUEST_ID_KEY) !== null;
}

/**
 * Force regenerate guest ID.
 * Creates new ID even if one exists.
 *
 * @returns New guest UUID string
 */
export function regenerateGuestId(): string {
  const newId = crypto.randomUUID();
  localStorage.setItem(GUEST_ID_KEY, newId);
  return newId;
}
