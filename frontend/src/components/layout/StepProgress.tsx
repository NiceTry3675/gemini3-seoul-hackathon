interface StepProgressProps {
  stepLabel: string;
  nextLabel?: string;
  labels: string[];
  currentIndex: number;
  className?: string;
}

export default function StepProgress({
  stepLabel,
  nextLabel,
  labels,
  currentIndex,
  className,
}: StepProgressProps) {
  return (
    <div className={`mx-auto flex w-full max-w-[980px] flex-col gap-2.5 ${className ?? ''}`}>
      <div className="flex items-end justify-between">
        <span className="text-sm font-bold uppercase tracking-wider text-ts-primary">{stepLabel}</span>
        {nextLabel ? <span className="text-sm text-ts-text-muted">{nextLabel}</span> : null}
      </div>

      <div className="flex w-full gap-1">
        {labels.map((label, index) => {
          const active = index < currentIndex;
          return (
            <div
              key={label}
              className={`h-2 flex-1 rounded-full ${active ? 'bg-ts-primary' : 'bg-slate-800'}`}
              aria-hidden="true"
            />
          );
        })}
      </div>

      <div className="flex justify-between pt-1 text-xs font-medium">
        {labels.map((label, index) => (
          <span
            key={label}
            className={
              index < currentIndex ? 'text-ts-primary' : 'text-ts-text-subtle'
            }
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
