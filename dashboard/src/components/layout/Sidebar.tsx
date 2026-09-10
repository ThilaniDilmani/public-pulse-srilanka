import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  PieChart,
  Grid,
  Tv,
  Layers,
  Film,
  Sparkles,
  Search,
  ShieldCheck,
  CheckCircle2,
  Database,
  BookOpen,
  Menu,
  X,
  Compass,
} from 'lucide-react';

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'OVERVIEW',
    items: [
      { label: 'Overview', path: '/overview', icon: LayoutDashboard },
    ],
  },
  {
    title: 'EXPLORE',
    items: [
      { label: 'Discourse', path: '/explore/volume', icon: TrendingUp },
      { label: 'Topics', path: '/explore/topics', icon: PieChart },
      { label: 'Stance', path: '/explore/stance', icon: Compass },
      { label: 'Topic × Stance', path: '/explore/topic-stance', icon: Grid },
    ],
  },
  {
    title: 'SOURCES',
    items: [
      { label: 'Channels', path: '/sources/channels', icon: Tv },
      { label: 'Programs', path: '/sources/programs', icon: Layers },
      { label: 'Episodes', path: '/sources/episodes', icon: Film },
    ],
  },
  {
    title: 'AI INTELLIGENCE',
    items: [
      { label: 'Insights', path: '/ai/insights', icon: Sparkles },
      { label: 'Evidence Explorer', path: '/ai/evidence', icon: Search },
      { label: 'Faithfulness', path: '/ai/faithfulness', icon: ShieldCheck },
    ],
  },
  {
    title: 'DATA',
    items: [
      { label: 'Data Quality', path: '/data/quality', icon: CheckCircle2 },
      { label: 'Collection Status', path: '/data/collection', icon: Database },
    ],
  },
  {
    title: 'METHODOLOGY',
    items: [
      { label: 'Methodology', path: '/data/methodology', icon: BookOpen },
    ],
  },
];

interface SidebarProps {
  isCollapsed: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed }) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        className="md:hidden fixed top-3 left-3 z-50 p-2 bg-white text-slate-700 border border-slate-200 rounded-lg shadow-sm"
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        aria-label="Toggle Navigation Menu"
      >
        {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 bg-white border-r border-[var(--color-border)] flex flex-col transition-all duration-200 ease-in-out shadow-[var(--shadow-xs)] ${
          isCollapsed ? 'md:w-16' : 'md:w-60'
        } ${
          isMobileOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className={`h-14 border-b border-[var(--color-border)] flex items-center shrink-0 ${
          isCollapsed ? 'justify-center px-0' : 'px-5 gap-3'
        }`}>
          {/* Subtle Sri Lankan Maroon Civic Emblem */}
          <div className="w-8 h-8 rounded-lg bg-[var(--color-brand-maroon)] text-white flex items-center justify-center font-bold text-xs shadow-xs shrink-0">
            PP
          </div>

          {!isCollapsed && (
            <div className="overflow-hidden">
              <h1 className="font-heading font-bold text-sm tracking-tight text-[var(--color-text-main)] leading-none flex items-center gap-1.5">
                Public Pulse
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-brand-gold)]" />
              </h1>
              <p className="text-[10px] text-[var(--color-text-subtle)] font-medium mt-0.5 uppercase tracking-wider">
                Civic Intelligence
              </p>
            </div>
          )}
        </div>

        {/* Navigation Section Links */}
        <nav className="flex-1 overflow-y-auto py-3 space-y-4 px-2">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-0.5">
              {!isCollapsed && (
                <h2 className="px-3 text-[10px] font-bold text-[var(--color-text-subtle)] tracking-wider uppercase mb-1">
                  {section.title}
                </h2>
              )}

              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setIsMobileOpen(false)}
                    title={isCollapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-[var(--radius-button)] transition-colors relative group ${
                        isCollapsed ? 'justify-center px-0' : ''
                      } ${
                        isActive
                          ? 'bg-[var(--color-primary-100)] text-[var(--color-primary-600)] font-semibold'
                          : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-main)]'
                      }`
                    }
                  >
                    <Icon size={17} className="shrink-0" />
                    {!isCollapsed && <span className="truncate">{item.label}</span>}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer Info */}
        {!isCollapsed && (
          <div className="p-3 border-t border-[var(--color-border)] text-[11px] text-[var(--color-text-subtle)] space-y-0.5 bg-slate-50/50 shrink-0">
            <p className="font-semibold text-slate-700">Public Pulse Platform</p>
            <p className="text-[10px] text-slate-500">XLM-R Classifier • Grounded LLM</p>
          </div>
        )}
      </aside>
    </>
  );
};
