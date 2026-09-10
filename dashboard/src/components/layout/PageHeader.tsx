import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, description, actions }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-3 pb-1">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold font-heading text-[var(--color-text-main)] tracking-tight">
          {title}
        </h1>
        {description && (
          <p className="text-xs sm:text-sm text-[var(--color-text-subtle)] mt-0.5 max-w-3xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2.5 shrink-0 mt-2 sm:mt-0">{actions}</div>}
    </div>
  );
};
