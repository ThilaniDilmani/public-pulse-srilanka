import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  ...props
}) => {
  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 rounded-[var(--radius-button)]',
    md: 'text-sm px-4 py-2 rounded-[var(--radius-button)] font-medium',
    lg: 'text-base px-5 py-2.5 rounded-[var(--radius-button)] font-medium',
  }[size];

  const variantStyles = {
    primary: 'bg-[var(--color-primary-500)] text-white hover:bg-[var(--color-primary-600)] active:bg-[var(--color-primary-700)] shadow-sm',
    secondary: 'bg-[var(--color-accent-500)] text-slate-900 hover:bg-[var(--color-accent-600)] hover:text-white',
    outline: 'bg-white border border-[var(--color-border-strong)] text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)]',
    ghost: 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-main)]',
  }[variant];

  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
        sizeStyles,
        variantStyles,
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : null}
      {children}
    </button>
  );
};
