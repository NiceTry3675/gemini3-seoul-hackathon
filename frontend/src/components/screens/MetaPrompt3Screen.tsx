import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS, FRAME_SEQUENCE } from '../../data/workflowData';
import type { ProcessingState, VideoExportModel } from '../../types/workflow';

interface MetaPrompt3ScreenProps {
  storyText: string;
  selectedStyle: string | null;
  processing: ProcessingState;
  videoExport: VideoExportModel | null;
  onStartOver: () => void;
  onGenerateTeaser: () => void;
  onNext: () => void;
  onBack: () => void;
}

export default function MetaPrompt3Screen({
  storyText,
  selectedStyle,
  processing,
  videoExport,
  onStartOver,
  onGenerateTeaser,
  onNext,
  onBack,
}: MetaPrompt3ScreenProps) {
  const storySnippet = storyText.trim().slice(0, 120);
  const isGenerating = processing.running;
  const hasImages = videoExport !== null && videoExport.sourceFrames.length > 0;
  const hasError = Boolean(processing.errorMessage);

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
        <StepProgress
          stepLabel="STEP 4 OF 4"
          nextLabel="Generate"
          labels={['Story', 'Meta', 'Visuals', 'Export']}
          currentIndex={4}
        />

        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-5xl font-black tracking-tight text-slate-50">
                {hasImages ? 'Teaser Generated' : isGenerating ? 'Generating...' : 'Ready to Generate'}
              </h2>
              <p className="mt-2 text-lg text-slate-400">
                {hasImages
                  ? '9컷 티저가 생성되었습니다. 결과를 확인하세요.'
                  : isGenerating
                    ? 'AI가 3x3 그리드로 9컷 티저를 생성하고 있습니다...'
                    : 'AI가 3x3 그리드로 9컷 티저를 한 번에 생성합니다.'}
              </p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-ts-border bg-ts-panel/60 px-3 py-1 text-xs text-ts-text-muted">
              <span className="material-symbols-outlined text-base text-ts-primary">auto_awesome</span>
              9 panels · 1 image
            </span>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-700/60 bg-[#151b26] p-5">
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <span className="material-symbols-outlined text-base text-[#2b6cee]">description</span>
                Story
              </div>
              <p className="text-sm leading-relaxed text-slate-300 line-clamp-3">
                {storySnippet}{storyText.length > 120 ? '...' : ''}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700/60 bg-[#151b26] p-5">
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <span className="material-symbols-outlined text-base text-[#2b6cee]">palette</span>
                Visual Style
              </div>
              <p className="text-lg font-bold text-slate-200">
                {selectedStyle?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) ?? 'Not selected'}
              </p>
            </div>
          </div>

          {/* Error message */}
          {hasError && (
            <div className="rounded-xl border border-red-900/60 bg-red-950/30 p-5">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined mt-0.5 text-red-400">error</span>
                <div>
                  <p className="font-semibold text-red-300">Generation failed</p>
                  <p className="mt-1 text-sm text-red-200/80">{processing.errorMessage}</p>
                </div>
              </div>
            </div>
          )}

          {/* 9-panel layout with generated images */}
          <div className="rounded-xl border border-slate-700/60 bg-[#151b26] p-5">
            <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <span className="material-symbols-outlined text-base text-[#2b6cee]">grid_view</span>
              9-Panel Storyboard Layout
            </div>
            <div className="grid grid-cols-3 gap-2">
              {FRAME_SEQUENCE.map((label, idx) => {
                const frame = hasImages ? videoExport.sourceFrames.find((f) => f.index === idx + 1) : null;

                return (
                  <div
                    key={idx}
                    className="relative aspect-square overflow-hidden rounded-lg border border-slate-700/40 bg-slate-800/40"
                  >
                    {frame ? (
                      <>
                        <img
                          src={frame.imageUrl}
                          alt={`Cut ${idx + 1}: ${label}`}
                          className="h-full w-full object-cover"
                        />
                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-2 pb-1.5 pt-4">
                          <span className="text-[10px] font-semibold text-white/90">{idx + 1}. {label}</span>
                        </div>
                      </>
                    ) : isGenerating ? (
                      <div className="flex h-full flex-col items-center justify-center gap-2">
                        <div className="size-6 animate-spin rounded-full border-2 border-[#2b6cee] border-t-transparent" />
                        <span className="text-[10px] text-slate-500">{label}</span>
                      </div>
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center">
                        <span className="text-lg font-bold text-[#2b6cee]">{idx + 1}</span>
                        <span className="mt-1 text-[10px] text-slate-500">{label}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {!hasImages && !isGenerating && (
            <div className="flex items-start gap-3 rounded-lg border border-[#2b6cee]/20 bg-[#2b6cee]/10 p-4">
              <span className="material-symbols-outlined mt-0.5 shrink-0 text-[#2b6cee]">info</span>
              <p className="text-sm leading-relaxed text-slate-300">
                <span className="font-bold text-[#2b6cee]">How it works:</span> AI generates a character anchor image,
                then creates all 9 panels in a single 3x3 grid image for speed and consistency.
              </p>
            </div>
          )}
        </section>
      </main>

      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={
          hasImages
            ? {
                label: 'Next: Video Export',
                icon: 'arrow_forward',
                onClick: onNext,
                emphasis: 'primary',
              }
            : hasError
              ? {
                  label: 'Retry',
                  icon: 'refresh',
                  onClick: onGenerateTeaser,
                  emphasis: 'primary',
                }
              : {
                  label: isGenerating ? 'Generating...' : 'Generate Teaser',
                  icon: 'movie_filter',
                  onClick: onGenerateTeaser,
                  disabled: isGenerating,
                  emphasis: 'primary',
                }
        }
        hint={hasImages ? 'Your teaser is ready. Proceed to video export.' : isGenerating ? 'Please wait while AI generates your teaser...' : 'Click to generate your 9-panel teaser.'}
      />

      {!isGenerating && (
        <button
          type="button"
          onClick={onStartOver}
          className="fixed bottom-24 left-6 rounded-lg border border-slate-700 bg-[#0d162c]/90 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 lg:left-10"
        >
          <span className="material-symbols-outlined mr-1 align-middle text-sm">restart_alt</span>
          Start Over
        </button>
      )}
    </div>
  );
}
