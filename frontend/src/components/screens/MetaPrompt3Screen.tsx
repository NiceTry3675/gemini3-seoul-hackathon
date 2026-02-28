import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';
import type { FrameSelection } from '../../types/workflow';

interface MetaPrompt3ScreenProps {
  frameSelections: FrameSelection[];
  onSelectOption: (frameIndex: number, optionId: string) => void;
  onRegenerateCurrentFrame: (frameIndex: number) => void;
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
  onRegenerateCurrentFrame,
  onStartOver,
  onGenerateTeaser,
  onBack,
}: MetaPrompt3ScreenProps) {
  const currentFrame = getCurrentFrame(frameSelections);
  const canGenerate = frameSelections[0]?.selectedOptionId !== null;

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} innerClassName="max-w-[1320px] px-6 lg:px-10" />

      <main className="mx-auto flex w-full max-w-[1320px] flex-col px-6 py-10 lg:px-10">
        <StepProgress
          stepLabel="STEP 4 OF 4"
          nextLabel="In Progress"
          labels={['Story', 'Meta', 'Visuals', 'Generation']}
          currentIndex={4}
        />

        <section className="mt-8 space-y-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-5xl font-black tracking-tight text-slate-50">
                Generating Frame {currentFrame.frameIndex} of {frameSelections.length}
              </h2>
              <p className="mt-2 text-lg text-slate-400">
                Select the best static image for the current sequence to proceed.
              </p>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-sm text-slate-400 transition-colors hover:text-slate-200"
            >
              <span className="material-symbols-outlined text-base">filter_list</span>
              Filter Styles
            </button>
          </div>

          <div className="teaser-scrollbar flex gap-4 overflow-x-auto pb-2">
            {frameSelections.map((frame) => {
              const isActive = frame.status === 'active';
              const isComplete = frame.status === 'complete';
              return (
                <div
                  key={frame.frameIndex}
                  className={`min-w-[220px] flex-1 rounded-xl border p-4 ${
                    isActive
                      ? 'border-[#2b6cee] bg-[#1a2337] shadow-[0_0_16px_rgba(43,108,238,0.35)]'
                      : isComplete
                        ? 'border-slate-700 bg-[#141c2f]'
                        : 'border-slate-800 bg-[#111827] opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between text-sm font-bold uppercase">
                    <span className={isActive ? 'text-[#2b6cee]' : 'text-slate-400'}>
                      Frame {String(frame.frameIndex).padStart(2, '0')}
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

                  <div className="mt-3 flex h-32 items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/50">
                    <span className="material-symbols-outlined text-4xl text-slate-500">image</span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span>{frame.sequenceLabel}</span>
                    <span>
                      {isActive ? 'Selecting...' : isComplete ? 'Ready' : `Waiting ${frame.frameIndex - 1}`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div>
            <h3 className="mb-4 flex items-center gap-2 text-3xl font-bold text-slate-100">
              <span className="rounded-full bg-[#2b6cee] px-2 py-0.5 text-xs font-bold text-white">4 Options</span>
              Variations for Frame {String(currentFrame.frameIndex).padStart(2, '0')}
            </h3>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {currentFrame.options.map((option) => {
                const selected = currentFrame.selectedOptionId === option.id;
                return (
                  <article
                    key={option.id}
                    className={`overflow-hidden rounded-xl border bg-[#151b26] shadow-lg transition-all ${
                      selected ? 'border-[#2b6cee] shadow-blue-500/20' : 'border-slate-700 hover:border-[#2b6cee]/50'
                    }`}
                  >
                    <div className="relative aspect-video overflow-hidden">
                      <img src={option.imageUrl} alt={option.label} className="h-full w-full object-cover" />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
                      <span className="absolute right-3 top-3 rounded bg-black/65 px-2 py-1 font-mono text-xs text-white">
                        {option.tag}
                      </span>
                    </div>

                    <div className="space-y-3 p-4">
                      <div>
                        <h4 className="text-2xl font-bold text-white">{option.label}</h4>
                        <p className="text-sm text-slate-400">{option.subtitle}</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="flex-1 rounded-lg border border-slate-700 bg-slate-800 py-2 text-xs text-slate-300"
                        >
                          <span className="material-symbols-outlined mr-1 align-middle text-sm">edit</span>
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => onSelectOption(currentFrame.frameIndex, option.id)}
                          className={`flex-1 rounded-lg py-2 text-xs font-semibold transition-colors ${
                            selected
                              ? 'bg-[#2b6cee] text-white'
                              : 'border border-[#2b6cee]/25 bg-[#2b6cee]/10 text-[#2b6cee] hover:bg-[#2b6cee]/20'
                          }`}
                        >
                          <span className="material-symbols-outlined mr-1 align-middle text-sm">check_circle</span>
                          {selected ? 'Selected' : 'Select'}
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>
      </main>

      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        secondaryAction={{
          label: 'Regenerate Current Frame',
          icon: 'refresh',
          onClick: () => onRegenerateCurrentFrame(currentFrame.frameIndex),
          emphasis: 'secondary',
        }}
        primaryAction={{
          label: 'Generate Teaser',
          icon: 'movie_filter',
          onClick: onGenerateTeaser,
          disabled: !canGenerate,
          emphasis: 'primary',
        }}
        hint="Select at least Frame 01 to start rendering"
        innerClassName="max-w-[1320px] px-6 lg:px-10"
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
