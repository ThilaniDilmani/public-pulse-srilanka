import React from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { MatrixHeatmap } from '../../components/charts/MatrixHeatmap';
import { Card } from '../../components/ui/Card';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import { useTopicStanceMatrix } from '../../hooks/useAnalytics';

export const TopicStancePage: React.FC = () => {
  const { data: matrix, isLoading } = useTopicStanceMatrix();

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Topic × Stance Matrix"
        description="Cross-tabulate public discourse topic distribution against comment stance orientation."
      />

      <GlobalFilterBar />
      <ScopeIndicator />

      <Card>
        {isLoading ? (
          <ChartSkeleton height={280} />
        ) : (
          <MatrixHeatmap matrix={matrix?.matrix || {}} />
        )}
      </Card>

      {/* Analytical Guidance Panel */}
      <div className="p-4 bg-white border border-slate-200 rounded-lg text-xs space-y-2 shadow-xs">
        <h4 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          How to Interpret this Matrix
        </h4>
        <p className="text-[var(--color-text-muted)] leading-relaxed">
          The 5 × 3 Topic × Stance matrix displays the joint frequency distribution of macro-topics
          and stance orientations. Each cell represents comments classified with both that specific topic
          and stance. Toggle between <strong>Counts</strong>, <strong>Row Percentages</strong> (topic breakdown across stances),
          and <strong>Column Percentages</strong> (stance breakdown across topics).
        </p>
      </div>
    </div>
  );
};

export default TopicStancePage;
