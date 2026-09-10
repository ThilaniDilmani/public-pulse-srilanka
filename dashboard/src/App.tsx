import { useState, lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { useFilterSync } from './hooks/useFilterSync';
import { ChartSkeleton } from './components/ui/Skeleton';

/* ─── Lazy pages ─────────────────────────────────────────── */
const OverviewPage         = lazy(() => import('./features/overview/OverviewPage'));
const VolumePage           = lazy(() => import('./features/explore/VolumePage'));
const TopicsPage           = lazy(() => import('./features/explore/TopicsPage'));
const StancePage           = lazy(() => import('./features/explore/StancePage'));
const TopicStancePage      = lazy(() => import('./features/explore/TopicStancePage'));
const ChannelsPage         = lazy(() => import('./features/sources/ChannelsPage'));
const ChannelDetailPage    = lazy(() => import('./features/sources/ChannelDetailPage'));
const ProgramsPage         = lazy(() => import('./features/sources/ProgramsPage'));
const ProgramDetailPage    = lazy(() => import('./features/sources/ProgramDetailPage'));
const EpisodesPage         = lazy(() => import('./features/sources/EpisodesPage'));
const InsightsPage         = lazy(() => import('./features/ai/InsightsPage'));
const InsightDetailPage    = lazy(() => import('./features/ai/InsightDetailPage'));
const EvidenceExplorerPage  = lazy(() => import('./features/ai/EvidenceExplorerPage'));
const FaithfulnessPage     = lazy(() => import('./features/ai/FaithfulnessPage'));
const DataQualityPage      = lazy(() => import('./features/data/DataQualityPage'));
const CollectionStatusPage  = lazy(() => import('./features/data/CollectionStatusPage'));
const MethodologyPage      = lazy(() => import('./features/data/MethodologyPage'));

/* ─── Page fallback ─────────────────────────────────────── */
function PageFallback() {
  return (
    <div className="p-8 space-y-4 max-w-7xl mx-auto">
      <ChartSkeleton />
      <ChartSkeleton />
    </div>
  );
}

/* ─── App shell layout ──────────────────────────────────── */
function AppShell({ children }: { children: React.ReactNode }) {
  useFilterSync();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-bg)]">
      <Sidebar isCollapsed={isCollapsed} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          isSidebarCollapsed={isCollapsed}
          onToggleSidebar={() => setIsCollapsed(!isCollapsed)}
        />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

/* ─── App ───────────────────────────────────────────────── */
export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/overview" replace />} />

          {/* Main */}
          <Route path="/overview" element={<OverviewPage />} />

          {/* Explore */}
          <Route path="/explore/volume"       element={<VolumePage />} />
          <Route path="/explore/topics"       element={<TopicsPage />} />
          <Route path="/explore/stance"       element={<StancePage />} />
          <Route path="/explore/topic-stance" element={<TopicStancePage />} />

          {/* Sources */}
          <Route path="/sources/channels"            element={<ChannelsPage />} />
          <Route path="/sources/channels/:channelId" element={<ChannelDetailPage />} />
          <Route path="/sources/programs"            element={<ProgramsPage />} />
          <Route path="/sources/programs/:programId" element={<ProgramDetailPage />} />
          <Route path="/sources/episodes"            element={<EpisodesPage />} />

          {/* AI Intelligence */}
          <Route path="/ai/insights"          element={<InsightsPage />} />
          <Route path="/ai/insights/:id"      element={<InsightDetailPage />} />
          <Route path="/ai/evidence"          element={<EvidenceExplorerPage />} />
          <Route path="/ai/faithfulness"      element={<FaithfulnessPage />} />

          {/* Data */}
          <Route path="/data/quality"         element={<DataQualityPage />} />
          <Route path="/data/collection"      element={<CollectionStatusPage />} />
          <Route path="/data/methodology"     element={<MethodologyPage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
