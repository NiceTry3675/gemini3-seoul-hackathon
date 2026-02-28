import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  startIcon?: ReactNode;
  endIcon?: ReactNode;
}

function cx(...parts: Array<string | undefined | false>): string {
  return parts.filter(Boolean).join(' ');
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-ts-primary text-white shadow-lg shadow-blue-500/20 hover:bg-ts-primary-hover disabled:bg-slate-700 disabled:text-slate-400',
  secondary:
    'border border-ts-primary bg-ts-primary-soft text-ts-primary hover:bg-ts-primary-soft-hover disabled:border-slate-700 disabled:bg-slate-800/60 disabled:text-slate-500',
  outline:
    'border border-ts-border-strong bg-transparent text-ts-text hover:bg-slate-800 disabled:border-slate-700 disabled:text-slate-500',
  ghost:
    'bg-transparent text-ts-text-muted hover:text-ts-text disabled:text-slate-500',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-2.5 text-sm',
  lg: 'px-8 py-3 text-base',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  startIcon,
  endIcon,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ts-primary focus-visible:ring-offset-2 focus-visible:ring-offset-ts-nav',
        'disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...props}
    >
      {startIcon}
      <span>{children}</span>
      {endIcon}
    </button>
  );
}
