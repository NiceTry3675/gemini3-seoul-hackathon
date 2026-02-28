interface StepProgressProps {
  stepLabel: string;
  nextLabel?: string;
  labels: string[];
  currentIndex: number;
}

export default function StepProgress({
  stepLabel,
  nextLabel,
  labels,
  currentIndex,
}: StepProgressProps) {
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-end justify-between">
        <span className="text-sm font-bold uppercase tracking-wider text-[#2b6cee]">{stepLabel}</span>
        {nextLabel ? <span className="text-sm text-slate-400">{nextLabel}</span> : null}
      </div>

      <div className="flex w-full gap-1">
        {labels.map((label, index) => {
          const active = index < currentIndex;
          return (
            <div
              key={label}
              className={`h-2 flex-1 rounded-full ${active ? 'bg-[#2b6cee]' : 'bg-slate-800'}`}
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
              index < currentIndex ? 'text-[#2b6cee]' : 'text-slate-500'
            }
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
