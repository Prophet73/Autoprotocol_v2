import { useEffect, type RefObject } from 'react';

/**
 * Traps keyboard focus within a container element.
 * Tab / Shift+Tab cycle through focusable children.
 */
export function useFocusTrap(ref: RefObject<HTMLElement | null>, active = true) {
  useEffect(() => {
    if (!active) return;
    const el = ref.current;
    if (!el) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const focusable = el.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [ref, active]);
}
