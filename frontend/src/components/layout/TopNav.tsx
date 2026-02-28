import type { ReactNode } from 'react';
import LogoMark from './LogoMark';

export interface NavItem {
  label: string;
  active?: boolean;
}

interface TopNavProps {
  links: readonly NavItem[] | NavItem[];
  rightContent?: ReactNode;
  innerClassName?: string;
}

function DefaultRightContent() {
  return (
    <div className="flex items-center gap-4">
      <button
        type="button"
        aria-label="Notifications"
        className="rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-800/70 hover:text-slate-100"
      >
        <span className="material-symbols-outlined text-xl">notifications</span>
      </button>
      <div className="size-9 rounded-full border border-slate-600 bg-slate-700" aria-hidden="true" />
    </div>
  );
}

export default function TopNav({
  links,
  rightContent,
  innerClassName = 'max-w-[1200px] px-6 lg:px-10',
}: TopNavProps) {
  return (
    <header className="w-full border-b border-slate-800/80 bg-[#0a1225]/90 backdrop-blur-md">
      <div className={`mx-auto flex w-full items-center justify-between py-4 ${innerClassName}`}>
        <div className="flex items-center gap-3">
          <LogoMark />
          <h1 className="text-xl font-bold tracking-tight text-slate-100">TeaserStudio</h1>
        </div>

        <nav className="hidden items-center gap-8 md:flex">
          {links.map((link) => (
            <button
              key={link.label}
              type="button"
              className={`text-sm font-medium transition-colors ${
                link.active ? 'text-[#2b6cee]' : 'text-slate-300 hover:text-[#2b6cee]'
              }`}
            >
              {link.label}
            </button>
          ))}
        </nav>

        {rightContent ?? <DefaultRightContent />}
      </div>
    </header>
  );
}
