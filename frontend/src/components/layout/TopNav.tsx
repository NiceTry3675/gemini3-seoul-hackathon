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

export default function TopNav({
  links,
  rightContent,
  innerClassName = 'max-w-[1200px] px-6 lg:px-10',
}: TopNavProps) {
  return (
    <header className="w-full border-b border-ts-border/80 bg-ts-nav/90 backdrop-blur-md">
      <div className={`mx-auto flex w-full items-center justify-between py-4 ${innerClassName}`}>
        <div className="flex items-center gap-3">
          <LogoMark />
          <h1 className="text-xl font-bold tracking-tight text-ts-text">TeaserStudio</h1>
        </div>

        {links.length > 0 ? (
          <nav className="hidden items-center gap-8 md:flex">
            {links.map((link) => (
              <button
                key={link.label}
                type="button"
                className={`text-sm font-medium transition-colors ${
                  link.active ? 'text-ts-primary' : 'text-ts-text-muted hover:text-ts-primary'
                }`}
              >
                {link.label}
              </button>
            ))}
          </nav>
        ) : (
          <div className="hidden md:block" />
        )}

        {rightContent ?? <div className="hidden md:block" />}
      </div>
    </header>
  );
}
