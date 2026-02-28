interface ActionButton {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: string;
  emphasis?: 'primary' | 'secondary' | 'outline';
}

interface BottomActionBarProps {
  backAction?: ActionButton;
  secondaryAction?: ActionButton;
  primaryAction?: ActionButton;
  hint?: string;
  innerClassName?: string;
}

function getButtonClasses(emphasis: ActionButton['emphasis'], disabled = false): string {
  if (disabled) {
    return 'cursor-not-allowed border border-slate-700 bg-slate-800/60 text-slate-500';
  }

  switch (emphasis) {
    case 'primary':
      return 'bg-[#2b6cee] text-white shadow-lg shadow-blue-500/20 hover:bg-blue-600';
    case 'secondary':
      return 'border border-[#2b6cee] bg-[#2b6cee]/10 text-[#2b6cee] hover:bg-[#2b6cee]/20';
    default:
      return 'border border-slate-600 bg-transparent text-slate-300 hover:bg-slate-800';
  }
}

function Action({ action }: { action: ActionButton }) {
  return (
    <button
      type="button"
      onClick={action.onClick}
      disabled={action.disabled}
      className={`inline-flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-medium transition-colors ${getButtonClasses(
        action.emphasis,
        action.disabled,
      )}`}
    >
      {action.icon ? <span className="material-symbols-outlined text-base">{action.icon}</span> : null}
      <span>{action.label}</span>
    </button>
  );
}

export default function BottomActionBar({
  backAction,
  secondaryAction,
  primaryAction,
  hint,
  innerClassName = 'max-w-[1100px] px-6 lg:px-10',
}: BottomActionBarProps) {
  return (
    <footer className="sticky bottom-0 z-10 border-t border-slate-800/80 bg-[#0a1225]/90 py-4 backdrop-blur-md">
      <div className={`mx-auto flex w-full items-center justify-between ${innerClassName}`}>
        <div className="flex items-center gap-4">
          {backAction ? <Action action={backAction} /> : <div />}
          {hint ? <span className="hidden text-xs text-slate-500 sm:block">{hint}</span> : null}
        </div>

        <div className="flex items-center gap-3">
          {secondaryAction ? <Action action={secondaryAction} /> : null}
          {primaryAction ? <Action action={primaryAction} /> : null}
        </div>
      </div>
    </footer>
  );
}
