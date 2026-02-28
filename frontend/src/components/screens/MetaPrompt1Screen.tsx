import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';

interface MetaPrompt1ScreenProps {
  draft: string;
  historyCount: number;
  onDraftChange: (value: string) => void;
  onRegenerate: () => void;
  onBack: () => void;
  onNext: () => void;
}

export default function MetaPrompt1Screen({
  draft,
  historyCount,
  onDraftChange,
  onRegenerate,
  onBack,
  onNext,
}: MetaPrompt1ScreenProps) {
  const canProceed = draft.trim().length > 0;

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 py-10 lg:px-10">
        <StepProgress
          stepLabel="STEP 2 OF 4"
          nextLabel="Next: Choose Visual Style"
          labels={['Story', 'Meta', 'Visuals', 'Export']}
          currentIndex={2}
        />

        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="space-y-2">
            <h2 className="text-5xl font-black tracking-tight text-slate-50">Refine Meta Prompt</h2>
            <p className="text-lg text-slate-400">
              Review and tweak the AI-generated meta prompt below to guide the visual generation style.
            </p>
          </div>

          <div className="group relative">
            <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-[#2b6cee]/50 to-purple-600/40 opacity-30 blur transition duration-500 group-hover:opacity-50" />
            <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-[#151b26] shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-700/80 bg-[#111827] px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <span className="material-symbols-outlined text-base">auto_awesome</span>
                  AI Generated Draft
                </div>
                <button
                  type="button"
                  onClick={onRegenerate}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#2b6cee] transition-colors hover:text-blue-400"
                >
                  <span className="material-symbols-outlined text-sm">refresh</span>
                  Regenerate
                </button>
              </div>

              <textarea
                className="teaser-scrollbar h-[320px] w-full resize-none bg-transparent p-5 font-mono text-lg leading-relaxed text-slate-200 outline-none placeholder:text-slate-500"
                spellCheck={false}
                value={draft}
                onChange={(event) => onDraftChange(event.target.value)}
              />

              <div className="flex items-center justify-between border-t border-slate-700/70 px-5 py-3 text-xs text-slate-500">
                <span>{draft.length} characters</span>
                <div className="flex items-center gap-5">
                  <button type="button" className="inline-flex items-center gap-1 transition-colors hover:text-slate-300">
                    <span className="material-symbols-outlined text-base">content_copy</span>
                    Copy
                  </button>
                  <button type="button" className="inline-flex items-center gap-1 transition-colors hover:text-slate-300">
                    <span className="material-symbols-outlined text-base">history</span>
                    History ({historyCount})
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-lg border border-[#2b6cee]/20 bg-[#2b6cee]/10 p-4">
            <span className="material-symbols-outlined mt-0.5 shrink-0 text-[#2b6cee]">lightbulb</span>
            <p className="text-sm leading-relaxed text-slate-300">
              <span className="font-bold text-[#2b6cee]">Pro Tip:</span> Add camera angle, lens, and mood cues here.
              This prompt drives style consistency across generated frames.
            </p>
          </div>
        </section>
      </main>

      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={{
          label: 'Next: Choose Visual Style',
          icon: 'arrow_forward',
          onClick: onNext,
          disabled: !canProceed,
          emphasis: 'primary',
        }}
      />
    </div>
  );
}
