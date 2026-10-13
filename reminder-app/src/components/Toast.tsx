import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { BellIcon, CheckIcon, XIcon } from "./Icons";

export type ToastTone = "info" | "success" | "warning";

export interface ToastOptions {
  tone?: ToastTone;
  action?: { label: string; onClick: () => void };
  durationMs?: number;
}

interface ToastApi {
  show(message: string, opts?: ToastOptions): void;
}

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  action?: { label: string; onClick: () => void };
  durationMs: number;
}

const DEFAULT_DURATION = 4000;
const MAX_TOASTS = 3;

const ToastContext = createContext<ToastApi | null>(null);

const NOOP_API: ToastApi = { show: () => {} };

export function useToast(): ToastApi {
  return useContext(ToastContext) ?? NOOP_API;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, opts?: ToastOptions) => {
    const item: ToastItem = {
      id: nextId.current++,
      message,
      tone: opts?.tone ?? "info",
      action: opts?.action,
      durationMs: opts?.durationMs ?? DEFAULT_DURATION,
    };
    setToasts((list) => [...list, item].slice(-MAX_TOASTS));
  }, []);

  const api = useMemo<ToastApi>(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      {typeof document !== "undefined" &&
        createPortal(
          <div
            aria-live="polite"
            aria-atomic="false"
            role="status"
            className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 px-4"
            style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 1rem)" }}
          >
            <AnimatePresence initial={false}>
              {toasts.map((t) => (
                <ToastCard key={t.id} toast={t} onDismiss={dismiss} />
              ))}
            </AnimatePresence>
          </div>,
          document.body,
        )}
    </ToastContext.Provider>
  );
}

const TONE_STYLES: Record<ToastTone, { icon: string; bar: string }> = {
  info: { icon: "bg-accent-soft text-accent", bar: "bg-accent" },
  success: { icon: "bg-ok/15 text-ok", bar: "bg-ok" },
  warning: { icon: "bg-warn/15 text-warn", bar: "bg-warn" },
};

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </svg>
  );
}

function ToneIcon({ tone }: { tone: ToastTone }) {
  const cls = "h-4 w-4";
  if (tone === "success") return <CheckIcon className={cls} />;
  if (tone === "warning") return <WarningIcon className={cls} />;
  return <BellIcon className={cls} />;
}

const FOCUS = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false);
  const remaining = useRef(toast.durationMs);
  const startedAt = useRef(0);

  // Auto-dismiss timer that pauses while hovered / focused.
  useEffect(() => {
    if (paused || toast.durationMs <= 0 || !Number.isFinite(toast.durationMs)) return;
    startedAt.current = Date.now();
    const timer = window.setTimeout(() => onDismiss(toast.id), Math.max(0, remaining.current));
    return () => {
      window.clearTimeout(timer);
      remaining.current -= Date.now() - startedAt.current;
    };
  }, [paused, toast.id, toast.durationMs, onDismiss]);

  const tone = TONE_STYLES[toast.tone];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12, scale: 0.96, transition: { duration: 0.15 } }}
      transition={{ type: "spring", stiffness: 500, damping: 36 }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="pointer-events-auto relative flex w-full max-w-md items-center gap-3 overflow-hidden rounded-2xl border border-line bg-surface-2/95 py-2.5 pl-3 pr-2 text-sm text-fg shadow-xl shadow-black/40 backdrop-blur"
    >
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tone.icon}`}
        aria-hidden="true"
      >
        <ToneIcon tone={toast.tone} />
      </span>
      <p className="min-w-0 flex-1 break-words leading-snug">{toast.message}</p>
      {toast.action && (
        <button
          type="button"
          onClick={() => {
            toast.action?.onClick();
            onDismiss(toast.id);
          }}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft ${FOCUS}`}
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        title="Dismiss"
        className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-fg ${FOCUS}`}
      >
        <XIcon className="h-4 w-4" />
      </button>
      {toast.durationMs > 0 && Number.isFinite(toast.durationMs) && (
        <motion.span
          aria-hidden="true"
          className={`absolute bottom-0 left-0 h-0.5 w-full origin-left opacity-60 ${tone.bar}`}
          initial={{ scaleX: 1 }}
          animate={{ scaleX: 0 }}
          transition={{ duration: toast.durationMs / 1000, ease: "linear" }}
          style={{ animationPlayState: paused ? "paused" : "running" }}
        />
      )}
    </motion.div>
  );
}
