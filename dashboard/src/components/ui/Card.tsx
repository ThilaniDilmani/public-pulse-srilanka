import React from 'react';
import clsx from 'clsx';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'raised' | 'sunken';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
  ...props
}) => {
  const paddingStyles = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6',
  }[padding];

  const variantStyles = {
    default: 'bg-white border border-[var(--color-border)] shadow-[var(--shadow-card)]',
    raised: 'bg-white border border-[var(--color-border-subtle)] shadow-[var(--shadow-hover)]',
    sunken: 'bg-[var(--color-bg)] border border-[var(--color-border)]',
  }[variant];

  return (
    <div
      className={clsx('rounded-[var(--radius-card)] transition-shadow duration-150', paddingStyles, variantStyles, className)}
      {...props}
    >
      {children}
    </div>
  );
};
