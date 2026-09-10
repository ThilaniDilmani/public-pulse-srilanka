import React from 'react';
import clsx from 'clsx';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  className,
  style,
  ...props
}) => {
  return (
    <div
      className={clsx('skeleton', className)}
      style={{
        width: width !== undefined ? (typeof width === 'number' ? `${width}px` : width) : undefined,
        height: height !== undefined ? (typeof height === 'number' ? `${height}px` : height) : undefined,
        ...style,
      }}
      {...props}
    />
  );
};

export const KPICardSkeleton: React.FC = () => (
  <div className="p-5 bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] space-y-3">
    <Skeleton height={14} width="40%" />
    <Skeleton height={32} width="60%" />
    <Skeleton height={12} width="80%" />
  </div>
);

export const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 240 }) => (
  <div className="p-5 bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] space-y-4">
    <Skeleton height={18} width="35%" />
    <Skeleton height={height} width="100%" />
  </div>
);
