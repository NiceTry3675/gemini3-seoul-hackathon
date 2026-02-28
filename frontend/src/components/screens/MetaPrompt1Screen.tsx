import { useEffect, useState } from 'react';
import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';

interface MetaPrompt1ScreenProps {
  draft: string;
  loading: boolean;
  errorMessage: string | null;
  onRegenerate: () => void;
  onBack: () => void;
  onNext: () => void;
}

export default function MetaPrompt1Screen({
  draft,
  loading,
  errorMessage,
  onRegenerate,
  onBack,
  onNext,
}: MetaPrompt1ScreenProps) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle');
  const canProceed = draft.trim().length > 0 && !loading;

  useEffect(() => {
    if (copyState === 'idle') return;
    const timer = window.setTimeout(() => setCopyState('idle'), 1600);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  const handleCopy = async () => {
    if (!draft) return;
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

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />
      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
        <StepProgress stepLabel="STEP 2 OF 5" nextLabel="Next: Choose Visual Style" labels={['Story', 'Meta', 'Visuals', 'Export', 'Video']} currentIndex={2} />
        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="space-y-2">
            <h2 className="text-5xl font-black tracking-tight text-slate-50">Gemini 3 JSON Output</h2>
            <p className="text-lg text-slate-400">Gemini preview 결과를 JSON으로 표시합니다. 다음 단계에서 스타일 선택 및 생성 흐름으로 이어집니다.</p>
          </div>
          <div className="group relative">
            <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-[#2b6cee]/50 to-purple-600/40 opacity-30 blur transition duration-500 group-hover:opacity-50" />
            <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-[#151b26] shadow-xl">
              <div className="flex items-center border-b border-slate-700/80 bg-[#111827] px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <span className="material-symbols-outlined text-base">auto_awesome</span>
                  Gemini Preview JSON
                </div>
              </div>
              <pre className="teaser-scrollbar h-[320px] w-full overflow-auto bg-transparent p-5 font-mono text-sm leading-relaxed text-slate-200">
                {loading ? 'Generating preview JSON via Gemini 3...' : draft || '{ }'}
              </pre>
              <div className="flex items-center justify-between border-t border-slate-700/70 px-5 py-3 text-xs text-slate-500">
                <span>{draft.length} characters</span>
                <div className="flex items-center gap-5">
                  <button type="button" onClick={onRegenerate} className="inline-flex items-center gap-1 transition-colors hover:text-slate-300" disabled={loading}>
                    <span className="material-symbols-outlined text-base">refresh</span>Regenerate
                  </button>
                  <button type="button" onClick={handleCopy} className="inline-flex items-center gap-1 transition-colors hover:text-slate-300">
                    <span className="material-symbols-outlined text-base">content_copy</span>
                    {copyState === 'copied' ? 'Copied' : copyState === 'error' ? 'Copy failed' : 'Copy'}
                  </button>
                </div>
              </div>
            </div>
          </div>
          {errorMessage ? (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">{errorMessage}</div>
          ) : null}
          <div className="flex items-start gap-3 rounded-lg border border-[#2b6cee]/20 bg-[#2b6cee]/10 p-4">
            <span className="material-symbols-outlined mt-0.5 shrink-0 text-[#2b6cee]">lightbulb</span>
            <p className="text-sm leading-relaxed text-slate-300">
              <span className="font-bold text-[#2b6cee]">Note:</span> 이 JSON은 Scene/Character/Cut preview가 포함된 결과로, 다음 단계에서 스타일 선택 및 생성 흐름으로 이어집니다.
            </p>
          </div>
        </section>
      </main>
      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={{ label: 'Next: Choose Visual Style', icon: 'arrow_forward', onClick: onNext, disabled: !canProceed, emphasis: 'primary' }}
      />
    </div>
  );
}
