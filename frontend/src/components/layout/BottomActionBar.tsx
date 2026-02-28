import Button from '../ui/Button';

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

function Action({ action }: { action: ActionButton }) {
  const variant =
    action.emphasis === 'primary'
      ? 'primary'
      : action.emphasis === 'secondary'
        ? 'secondary'
        : 'outline';

  return (
    <Button
      onClick={action.onClick}
      disabled={action.disabled}
      variant={variant}
      size="md"
      startIcon={
        action.icon ? <span className="material-symbols-outlined text-base">{action.icon}</span> : undefined
      }
    >
      {action.label}
    </Button>
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
    <footer className="sticky bottom-0 z-10 border-t border-ts-border/80 bg-ts-nav/90 py-4 backdrop-blur-md">
      <div className={`mx-auto flex w-full items-center justify-between ${innerClassName}`}>
        <div className="flex items-center gap-4">
          {backAction ? <Action action={backAction} /> : <div />}
          {hint ? <span className="hidden text-xs text-ts-text-subtle sm:block">{hint}</span> : null}
        </div>

        <div className="flex items-center gap-3">
          {secondaryAction ? <Action action={secondaryAction} /> : null}
          {primaryAction ? <Action action={primaryAction} /> : null}
        </div>
      </div>
    </footer>
  );
}
