import React from 'react';
import clsx from 'clsx';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'accent' | 'crit' | 'neut' | 'supp' | 'supported' | 'partially_supported' | 'unsupported' | 'contradicted' | 'outline';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  ...props
}) => {
  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1 font-medium',
  }[size];

  const variantStyles: Record<string, string> = {
    primary: 'bg-[var(--color-primary-100)] text-[var(--color-primary-700)] border border-[var(--color-primary-300)]',
    accent: 'bg-[var(--color-accent-100)] text-[var(--color-accent-700)] border border-[var(--color-accent-500)]',
    crit: 'bg-[var(--color-crit-subtle)] text-[var(--color-crit)] font-semibold',
    neut: 'bg-[var(--color-neut-subtle)] text-[var(--color-neut)] font-semibold',
    supp: 'bg-[var(--color-supp-subtle)] text-[var(--color-supp)] font-semibold',
    supported: 'bg-[#D4EFDF] text-[#1E8449] font-bold',
    partially_supported: 'bg-[#FDEBD0] text-[#B9770E] font-bold',
    unsupported: 'bg-[#FADBD8] text-[#C0392B] font-bold',
    contradicted: 'bg-[#F2D7D5] text-[#7B241C] font-bold',
    outline: 'bg-transparent border border-[var(--color-border-strong)] text-[var(--color-text-muted)]',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center rounded-[var(--radius-pill)] tracking-wide',
        sizeStyles,
        variantStyles[variant] || variantStyles.primary,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
