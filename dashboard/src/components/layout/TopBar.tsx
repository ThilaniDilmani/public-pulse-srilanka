import React from 'react';
import { useLocation } from 'react-router-dom';
import { PanelLeftClose, PanelLeft, ShieldCheck, ChevronRight } from 'lucide-react';

interface TopBarProps {
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

const ROUTE_LABELS: Record<string, { section: string; title: string }> = {
  '/overview':             { section: 'Overview', title: 'Civic Discourse Overview' },
  '/explore/volume':       { section: 'Explore',  title: 'Discourse Volume & Trends' },
  '/explore/topics':       { section: 'Explore',  title: 'Topic Distribution' },
  '/explore/stance':       { section: 'Explore',  title: 'Stance Orientation' },
  '/explore/topic-stance': { section: 'Explore',  title: 'Topic × Stance Matrix' },
  '/sources/channels':     { section: 'Sources',  title: 'Channels Catalog' },
  '/sources/programs':     { section: 'Sources',  title: 'Programs Catalog' },
  '/sources/episodes':     { section: 'Sources',  title: 'Episodes Index' },
  '/ai/insights':          { section: 'AI Intelligence', title: 'Grounded AI Insights' },
  '/ai/evidence':          { section: 'AI Intelligence', title: 'Evidence Explorer' },
  '/ai/faithfulness':      { section: 'AI Intelligence', title: 'Faithfulness Verification' },
  '/data/quality':         { section: 'Data',     title: 'Data Quality & Coverage' },
  '/data/collection':      { section: 'Data',     title: 'Collection Status' },
  '/data/methodology':     { section: 'Methodology', title: 'System Methodology' },
};

export const TopBar: React.FC<TopBarProps> = ({
  isSidebarCollapsed,
  onToggleSidebar,
}) => {
  const location = useLocation();

  const matchedRoute = Object.keys(ROUTE_LABELS).find(r => location.pathname.startsWith(r)) || '/overview';
  const meta = ROUTE_LABELS[matchedRoute] || { section: 'Overview', title: 'Civic Discourse Overview' };

  return (
    <header className="h-14 bg-white border-b border-[var(--color-border)] px-4 sm:px-6 flex items-center justify-between shrink-0 z-10 shadow-[var(--shadow-xs)]">
      <div className="flex items-center gap-3">
        {/* Desktop Collapse Toggle Button */}
        <button
          onClick={onToggleSidebar}
          className="hidden md:flex items-center justify-center w-8 h-8 rounded-lg text-[var(--color-text-subtle)] hover:text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] transition-colors"
          title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          aria-label="Toggle Sidebar Navigation"
        >
          {isSidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
        </button>

        {/* Master Breadcrumb Navigation */}
        <nav className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-text-subtle)]">
          <span className="font-semibold text-slate-800">Public Pulse</span>
          <ChevronRight size={13} className="text-slate-300 shrink-0" />
          <span className="text-slate-600">{meta.section}</span>
          <ChevronRight size={13} className="text-slate-300 shrink-0" />
          <span className="text-[var(--color-text-main)] font-semibold">{meta.title}</span>
        </nav>
      </div>

      {/* Right Header Status Bar */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-pill)] bg-slate-50 border border-slate-200 text-[11px] font-mono font-medium text-slate-700">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>XLM-R Classifier Active</span>
        </div>
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-pill)] bg-amber-50 border border-amber-200 text-[11px] font-mono font-medium text-amber-800">
          <ShieldCheck size={13} className="text-amber-600 shrink-0" />
          <span>Grounded LLM Verified</span>
        </div>
      </div>
    </header>
  );
};
