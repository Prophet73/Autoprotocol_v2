import { useState, useCallback, useRef, useEffect } from 'react';

interface ConfirmOptions {
  title?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'default';
}

interface DialogState {
  open: boolean;
  message: string;
  options: ConfirmOptions;
  resolve: ((value: boolean) => void) | null;
  isAlert: boolean;
}

export function useConfirm() {
  const [state, setState] = useState<DialogState>({
    open: false,
    message: '',
    options: {},
    resolve: null,
    isAlert: false,
  });

  const confirm = useCallback((message: string, options: ConfirmOptions = {}): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ open: true, message, options, resolve, isAlert: false });
    });
  }, []);

  const alert = useCallback((message: string, options: ConfirmOptions = {}): Promise<void> => {
    return new Promise((resolve) => {
      setState({
        open: true,
        message,
        options,
        resolve: () => resolve(),
        isAlert: true,
      });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    state.resolve?.(true);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state.resolve]);

  const handleCancel = useCallback(() => {
    state.resolve?.(false);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state.resolve]);

  const ConfirmDialog = state.open ? (
    <ConfirmDialogUI
      message={state.message}
      options={state.options}
      isAlert={state.isAlert}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  ) : null;

  return { confirm, alert, ConfirmDialog };
}

function ConfirmDialogUI({
  message,
  options,
  isAlert,
  onConfirm,
  onCancel,
}: {
  message: string;
  options: ConfirmOptions;
  isAlert: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    confirmRef.current?.focus();
  }, []);

  // Trap focus within dialog
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        isAlert ? onConfirm() : onCancel();
        return;
      }
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
  }, [isAlert, onConfirm, onCancel]);

  const {
    title = isAlert ? 'Уведомление' : 'Подтверждение',
    confirmText = 'OK',
    cancelText = 'Отмена',
    variant = 'default',
  } = options;

  const confirmBtnClass =
    variant === 'danger'
      ? 'bg-red-600 hover:bg-red-700 text-white'
      : 'bg-severin-red hover:bg-severin-red-dark text-white';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40" onClick={isAlert ? onConfirm : onCancel} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 animate-in fade-in zoom-in-95"
      >
        <h3 className="text-lg font-semibold text-slate-800 mb-2">{title}</h3>
        <p className="text-sm text-slate-600 mb-6 whitespace-pre-line">{message}</p>
        <div className="flex justify-end gap-3">
          {!isAlert && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              {cancelText}
            </button>
          )}
          <button
            ref={confirmRef}
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${confirmBtnClass}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
