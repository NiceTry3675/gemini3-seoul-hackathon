import { useEffect, useState } from 'react';
import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';
import type { FrameSelection } from '../../types/workflow';

interface MetaPrompt3ScreenProps {
  frameSelections: FrameSelection[];
  onSelectOption: (frameIndex: number, optionId: string) => void;
  onStartOver: () => void;
  onGenerateTeaser: () => void;
  onBack: () => void;
}

function getCurrentFrame(frameSelections: FrameSelection[]): FrameSelection {
  const active = frameSelections.find((frame) => frame.status === 'active');
  if (active) {
    return active;
  }

  return frameSelections[frameSelections.length - 1];
}

export default function MetaPrompt3Screen({
  frameSelections,
  onSelectOption,
  onStartOver,
  onGenerateTeaser,
  onBack,
}: MetaPrompt3ScreenProps) {
  const [loadingCutId, setLoadingCutId] = useState<number | null>(null);
  const currentFrame = getCurrentFrame(frameSelections);
  const completedCuts = frameSelections.filter((frame) => frame.selectedOptionId !== null).length;
  const totalCuts = frameSelections.length;
  const allGenerated = completedCuts === totalCuts;

  useEffect(() => {
    if (allGenerated || currentFrame.status !== 'active' || currentFrame.selectedOptionId !== null) {
      setLoadingCutId(null);
      return;
    }

    const nextOption = currentFrame.options[0];
    if (!nextOption) {
      setLoadingCutId(null);
      return;
    }

    setLoadingCutId(currentFrame.frameIndex);

    const timer = window.setTimeout(() => {
      onSelectOption(currentFrame.frameIndex, nextOption.id);
      setLoadingCutId(null);
    }, 900);

    return () => {
      window.clearTimeout(timer);
    };
  }, [allGenerated, currentFrame, onSelectOption]);

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
        <StepProgress
          stepLabel="STEP 4 OF 4"
          nextLabel="Next: Pipeline Run"
          labels={['Story', 'Meta', 'Visuals', 'Export']}
          currentIndex={4}
        />

        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-5xl font-black tracking-tight text-slate-50">
                Generating Cut {allGenerated ? totalCuts : Math.min(completedCuts + 1, totalCuts)} of {totalCuts}
              </h2>
              <p className="mt-2 text-lg text-slate-400">
                Cuts are generated automatically one by one. Continue after all 9 cuts are ready.
              </p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-ts-border bg-ts-panel/60 px-3 py-1 text-xs text-ts-text-muted">
              <span className="material-symbols-outlined text-base text-ts-primary">auto_awesome</span>
              {loadingCutId !== null && !allGenerated
                ? `Rendering Cut ${String(loadingCutId).padStart(2, '0')}...`
                : `${completedCuts}/${totalCuts} complete`}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {frameSelections.map((frame) => {
              const isActive = frame.status === 'active';
              const isComplete = frame.status === 'complete';
              const isLoading = loadingCutId === frame.frameIndex && !isComplete;
              const selectedOption = frame.options.find((option) => option.id === frame.selectedOptionId);
              return (
                <div
                  key={frame.frameIndex}
                  className={`rounded-xl border p-4 ${
                    isActive
                      ? 'border-[#2b6cee] bg-[#1a2337] shadow-[0_0_16px_rgba(43,108,238,0.35)]'
                      : isComplete
                        ? 'border-slate-700 bg-[#141c2f]'
                        : 'border-slate-800 bg-[#111827] opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between text-sm font-bold uppercase">
                    <span className={isActive ? 'text-[#2b6cee]' : 'text-slate-400'}>
                      Cut {String(frame.frameIndex).padStart(2, '0')}
                    </span>
                    {frame.status === 'locked' ? (
                      <span className="material-symbols-outlined text-base text-slate-500">lock</span>
                    ) : frame.status === 'complete' ? (
                      <span className="material-symbols-outlined text-base text-emerald-400">check_circle</span>
                    ) : (
                      <span className="material-symbols-outlined animate-pulse text-base text-[#2b6cee]">
                        pending
                      </span>
                    )}
                  </div>

                  {selectedOption ? (
                    <div className="relative mt-3 h-32 overflow-hidden rounded-lg border border-slate-700 bg-slate-900/50">
                      <img
                        src={selectedOption.imageUrl}
                        alt={`Cut ${frame.frameIndex}`}
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                    </div>
                  ) : isLoading ? (
                    <div className="relative mt-3 h-32 overflow-hidden rounded-lg border border-ts-primary/40 bg-slate-900/60">
                      <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-slate-800/30 via-ts-primary/10 to-slate-800/30" />
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                        <span className="material-symbols-outlined animate-spin text-2xl text-ts-primary">
                          progress_activity
                        </span>
                        <span className="text-xs font-medium text-ts-text-muted">Generating image...</span>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-3 flex h-32 items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/50">
                      <span className="material-symbols-outlined text-4xl text-slate-500">image</span>
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span>{frame.sequenceLabel}</span>
                    <span>
                      {isLoading
                        ? 'Rendering...'
                        : isActive
                          ? 'Queued'
                          : isComplete
                            ? 'Ready'
                            : `Waiting ${frame.frameIndex - 1}`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>

      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={{
          label: 'Start Pipeline Generation',
          icon: 'auto_awesome',
          onClick: onGenerateTeaser,
          disabled: !allGenerated,
          emphasis: 'primary',
        }}
        hint="Cuts are prepared automatically. Start the backend pipeline when all 9 are ready."
      />

      <button
        type="button"
        onClick={onStartOver}
        className="fixed bottom-24 left-6 rounded-lg border border-slate-700 bg-[#0d162c]/90 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 lg:left-10"
      >
        <span className="material-symbols-outlined mr-1 align-middle text-sm">restart_alt</span>
        Start Over
      </button>
    </div>
  );
}
