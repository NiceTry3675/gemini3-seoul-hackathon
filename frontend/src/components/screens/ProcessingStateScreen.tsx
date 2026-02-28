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

const STEPS: Array<{ step: number; label: string }> = [
  { step: 1, label: 'Scene Parse' },
  { step: 2, label: 'Character Generation' },
  { step: 3, label: 'Cut Plan' },
  { step: 4, label: 'Validation' },
  { step: 5, label: 'Media Generation' },
];

function statusLabel(status?: PipelineProgressEvent['status']): string {
  if (!status) return 'waiting';
  return status;
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

  return (
    <div className="min-h-screen overflow-hidden">
      <TopNav links={PROCESSING_NAV_LINKS} innerClassName="max-w-none px-8 lg:px-10" />

      <main className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 pb-12 pt-10 lg:px-10">
        <section className="rounded-2xl border border-ts-border bg-ts-panel/70 p-6">
          <h2 className="text-3xl font-bold text-slate-100">Pipeline Progress</h2>
          <p className="mt-2 text-slate-400">
            {runId ? `Run ID: ${runId}` : 'Run ID를 생성 중입니다...'}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            상태: {showError ? 'failed' : running ? 'running' : 'completed'}
          </p>
        </section>

        {!showError ? (
          <section className="space-y-3 rounded-2xl border border-ts-border bg-ts-panel/70 p-6">
            {STEPS.map((item) => {
              const progress = progressByStep[item.step];
              const status = statusLabel(progress?.status);
              const isRunning = status === 'running';
              const isCompleted = status === 'completed';
              const isFailed = status === 'failed';

              return (
                <div
                  key={item.step}
                  className={`rounded-xl border px-4 py-3 ${
                    isFailed
                      ? 'border-red-500/60 bg-red-500/10'
                      : isCompleted
                        ? 'border-emerald-500/50 bg-emerald-500/10'
                        : isRunning
                          ? 'border-ts-primary/70 bg-ts-primary/10'
                          : 'border-slate-700 bg-[#111827]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-100">
                      Step {item.step}. {item.label}
                    </span>
                    <span className="text-xs uppercase tracking-wide text-slate-400">{status}</span>
                  </div>
                  {progress?.detail ? (
                    <p className="mt-1 text-sm text-slate-300">{progress.detail}</p>
                  ) : null}
                </div>
              );
            })}
          </section>
        ) : (
          <section className="rounded-2xl border border-red-900/60 bg-[#1a1e2d]/90 p-8">
            <h3 className="text-2xl font-bold text-red-300">Pipeline failed</h3>
            <p className="mt-3 text-red-100">{errorMessage}</p>
          </section>
        )}

        <section className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg border border-slate-600 px-5 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            Back to Input
          </button>
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-[#2b6cee] px-5 py-2 text-sm font-semibold text-white hover:bg-blue-600"
          >
            Retry
          </button>
        </section>
      </main>
    </div>
  );
}
