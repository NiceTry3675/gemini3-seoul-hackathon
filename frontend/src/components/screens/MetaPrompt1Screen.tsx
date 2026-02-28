import { useEffect, useState } from 'react';
import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';
import { callPromptPreview } from '../../services/workflowService';
import type { PromptPreviewResult } from '../../services/workflowService';

interface MetaPrompt1ScreenProps {
  draft: string;
  storyText?: string;
  selectedStyle?: string;
  onDraftChange: (value: string) => void;
  onBack: () => void;
  onNext: () => void;
}

export default function MetaPrompt1Screen({
  draft,
  storyText,
  selectedStyle,
  onDraftChange,
  onBack,
  onNext,
}: MetaPrompt1ScreenProps) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<PromptPreviewResult | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const canProceed = draft.trim().length > 0;

  useEffect(() => {
    if (copyState === 'idle') {
      return;
    }
    const timer = window.setTimeout(() => setCopyState('idle'), 1600);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  const handleCopy = async () => {
    if (!draft) {
      return;
    }

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(draft);
      } else {
        const helper = document.createElement('textarea');
        helper.value = draft;
        helper.setAttribute('readonly', '');
        helper.style.position = 'absolute';
        helper.style.left = '-9999px';
        document.body.appendChild(helper);
        helper.select();
        document.execCommand('copy');
        document.body.removeChild(helper);
      }
      setCopyState('copied');
    } catch {
      setCopyState('error');
    }
  };

  const handlePreview = async () => {
    if (!storyText) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const backendStyle = selectedStyle || 'webtoon_cel';
      const result = await callPromptPreview(storyText, backendStyle);
      setPreviewResult(result);
      onDraftChange(result.anchor_prompt);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
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
              <div className="flex items-center border-b border-slate-700/80 bg-[#111827] px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <span className="material-symbols-outlined text-base">auto_awesome</span>
                  AI Generated Draft
                </div>
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
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1 transition-colors hover:text-slate-300"
                  >
                    <span className="material-symbols-outlined text-base">content_copy</span>
                    {copyState === 'copied' ? 'Copied' : copyState === 'error' ? 'Copy failed' : 'Copy'}
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

          <div className="space-y-4">
            <button
              type="button"
              onClick={handlePreview}
              disabled={previewLoading || !storyText}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-5 py-2.5 text-sm font-semibold text-slate-200 transition-colors hover:border-slate-500 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-base">
                {previewLoading ? 'hourglass_empty' : 'preview'}
              </span>
              {previewLoading ? 'Generating Preview...' : 'Preview Prompts'}
            </button>

            {previewError && (
              <div className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
                <span className="material-symbols-outlined mt-0.5 shrink-0 text-red-400">error</span>
                <p className="text-sm text-red-400">{previewError}</p>
              </div>
            )}

            {previewResult && (
              <div className="space-y-4 rounded-xl border border-slate-700 bg-[#151b26] p-5">
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Anchor Prompt</h3>
                  <p className="font-mono text-sm leading-relaxed text-slate-200">{previewResult.anchor_prompt}</p>
                </div>

                <div className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Panel Prompts ({previewResult.cuts.length})
                  </h3>
                  <div className="space-y-2">
                    {previewResult.cuts.map((cut) => (
                      <div
                        key={cut.index}
                        className="rounded-lg border border-slate-700/60 bg-[#111827] p-3"
                      >
                        <div className="mb-1 text-xs font-semibold text-[#2b6cee]">Panel {cut.index}</div>
                        <p className="font-mono text-sm leading-relaxed text-slate-300">{cut.prompt}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
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
