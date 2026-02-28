import TopNav from '../layout/TopNav';
import { PROCESSING_NAV_LINKS } from '../../data/workflowData';
import type { PipelineProgressEvent } from '../../types/workflow';

interface ProcessingStateScreenProps {
  running: boolean;
  runId: string | null;
  progressByStep: Record<number, PipelineProgressEvent>;
  errorMessage: string | null;
  onRetry: () => void;
  onBack: () => void;
}

export default function ProcessingStateScreen({
  running,
  runId,
  progressByStep,
  errorMessage,
  onRetry,
  onBack,
}: ProcessingStateScreenProps) {
  const showError = Boolean(errorMessage);
  const steps = Object.values(progressByStep).sort((a, b) => a.step - b.step);

  return (
    <div className="min-h-screen overflow-hidden">
      <TopNav links={PROCESSING_NAV_LINKS} innerClassName="max-w-none px-8 lg:px-10" />

      <main className="relative flex min-h-[calc(100vh-72px)] items-center justify-center px-6">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#2b6cee]/20 blur-[120px]" />
        </div>

        {!showError ? (
          <section className="relative z-10 flex w-full max-w-md flex-col items-center gap-8 text-center">
            <div className="relative">
              <div className="size-16 rounded-full border-4 border-slate-800" />
              <div className="absolute inset-0 size-16 animate-spin rounded-full border-4 border-[#2b6cee] border-t-transparent" />
              <span className="material-symbols-outlined absolute inset-0 m-auto h-6 w-6 text-[#2b6cee]">
                auto_awesome
              </span>
            </div>

            <div className="space-y-3">
              <h2 className="text-4xl font-bold text-slate-100">Generating your vision...</h2>
              <p className="text-slate-400">
                Our AI is analyzing your inputs and crafting the perfect teaser. This might take a few
                seconds.
              </p>
              {runId ? (
                <p className="text-xs text-slate-600">Run ID: {runId}</p>
              ) : null}
            </div>

            {steps.length > 0 ? (
              <ul className="w-full space-y-2 text-left">
                {steps.map((evt) => (
                  <li key={evt.step} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
                    {evt.status === 'completed' ? (
                      <span className="material-symbols-outlined text-base text-emerald-400">check_circle</span>
                    ) : evt.status === 'failed' ? (
                      <span className="material-symbols-outlined text-base text-red-400">error</span>
                    ) : (
                      <span className="material-symbols-outlined animate-spin text-base text-[#2b6cee]">progress_activity</span>
                    )}
                    <span className="flex-1 text-sm text-slate-300">{evt.step_name}</span>
                    {evt.detail ? (
                      <span className="text-xs text-slate-500">{evt.detail}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex items-center gap-2">
                <div className="size-2 rounded-full bg-[#2b6cee]" />
                <div className="size-2 rounded-full bg-[#2b6cee]/60" />
                <div className="size-2 rounded-full bg-[#2b6cee]/30" />
              </div>
            )}

            {!running ? (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-lg border border-[#2b6cee]/30 bg-[#2b6cee]/10 px-5 py-2 text-sm font-medium text-[#2b6cee]"
              >
                Continue
              </button>
            ) : null}
          </section>
        ) : (
          <section className="relative z-10 w-full max-w-xl rounded-2xl border border-red-900/60 bg-[#1a1e2d]/90 p-8 text-center shadow-2xl">
            <h2 className="text-3xl font-bold text-red-300">Render failed</h2>
            <p className="mt-4 text-base leading-relaxed text-red-100">{errorMessage}</p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={onBack}
                className="rounded-lg border border-slate-600 px-5 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
              >
                Back to Selection
              </button>
              <button
                type="button"
                onClick={onRetry}
                className="rounded-lg bg-[#2b6cee] px-5 py-2 text-sm font-semibold text-white hover:bg-blue-600"
              >
                Retry Render
              </button>
            </div>
          </section>
        )}

        <div className="absolute bottom-12 right-12 hidden w-64 rounded-xl border border-slate-700 bg-[#161f32] p-2 shadow-xl lg:block">
          <div className="relative aspect-video rounded-lg bg-slate-700/70">
            <span className="material-symbols-outlined absolute inset-0 m-auto h-8 w-8 animate-pulse text-slate-500">
              image
            </span>
          </div>
          <div className="mt-3 space-y-2 px-1">
            <div className="h-2 w-3/4 animate-pulse rounded bg-slate-700" />
            <div className="h-2 w-1/2 animate-pulse rounded bg-slate-700" />
          </div>
        </div>
      </main>
    </div>
  );
}
