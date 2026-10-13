import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-app";

const BASE =
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-xl font-medium " +
  "transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:scale-[0.97] " +
  "disabled:pointer-events-none disabled:opacity-50 " +
  FOCUS;

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-white shadow-sm shadow-accent/30 hover:bg-[#8d70ff] active:bg-[#6c4cf0]",
  secondary: "border border-line bg-surface-2 text-fg hover:border-muted/50 hover:bg-[#232a3b]",
  ghost: "text-muted hover:bg-surface-2 hover:text-fg",
  danger: "bg-danger/15 text-danger hover:bg-danger/25 border border-danger/30",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-4 text-sm sm:text-[0.95rem]",
};

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", type = "button", className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(BASE, VARIANTS[variant], SIZES[size], className)}
      {...rest}
    />
  );
});

type Tone = "default" | "danger" | "ok";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  tone?: Tone;
};

const TONES: Record<Tone, string> = {
  default: "text-muted hover:bg-surface-2 hover:text-fg",
  danger: "text-muted hover:bg-danger/15 hover:text-danger",
  ok: "text-ok hover:bg-ok/15",
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, tone = "default", type = "button", className, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cx(
        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
        "transition-colors duration-150 active:scale-95 disabled:pointer-events-none disabled:opacity-50",
        FOCUS,
        TONES[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});
