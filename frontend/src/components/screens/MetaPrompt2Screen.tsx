import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS, STYLE_OPTIONS } from '../../data/workflowData';
import type { VisualStyleId } from '../../types/workflow';

interface MetaPrompt2ScreenProps {
  selectedStyle: VisualStyleId | null;
  referenceImages: Partial<Record<VisualStyleId, { imageBase64: string; mimeType: string }>>;
  loading: boolean;
  errorMessage: string | null;
  canProceed: boolean;
  onSelectStyle: (style: VisualStyleId) => void;
  onRegenerate: () => void;
  onBack: () => void;
  onNext: () => void;
}

export default function MetaPrompt2Screen({
  selectedStyle,
  referenceImages,
  loading,
  errorMessage,
  canProceed,
  onSelectStyle,
  onRegenerate,
  onBack,
  onNext,
}: MetaPrompt2ScreenProps) {
  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
        <StepProgress
          stepLabel="STEP 3 OF 4"
          nextLabel="Next: Export"
          labels={['Story', 'Meta', 'Visuals', 'Export']}
          currentIndex={3}
        />

        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="space-y-2">
            <h2 className="text-5xl font-black tracking-tight text-slate-50">Choose Reference Image</h2>
            <p className="max-w-4xl text-lg text-slate-400">
              `backend/system_instruction.toml` style templates 기반으로 생성된 4개 레퍼런스 이미지입니다.
              선택한 레퍼런스를 Export 단계 이미지 생성에 사용합니다.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {STYLE_OPTIONS.map((style) => {
              const selected = selectedStyle === style.id;
              const generated = referenceImages[style.id];
              return (
                <button
                  key={style.id}
                  type="button"
                  onClick={() => onSelectStyle(style.id)}
                  className="group relative overflow-visible text-left"
                  aria-pressed={selected}
                >
                  <div
                    className={`absolute -inset-[2px] rounded-xl blur-sm transition-all duration-300 ${
                      selected
                        ? 'bg-[#2b6cee] opacity-100'
                        : 'bg-[#2b6cee]/0 opacity-0 group-hover:bg-[#2b6cee]/50 group-hover:opacity-100'
                    }`}
                  />

                  <div
                    className={`relative flex h-full flex-col overflow-hidden rounded-xl border transition-colors ${
                      selected
                        ? 'border-[#2b6cee] bg-[#151b26] shadow-2xl shadow-blue-500/20'
                        : 'border-slate-700 bg-[#111827] hover:border-[#2b6cee]/50'
                    }`}
                  >
                    <div className="relative aspect-[3/4] overflow-hidden">
                      {generated ? (
                        <img
                          src={`data:${generated.mimeType};base64,${generated.imageBase64}`}
                          alt={style.title}
                          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
                        />
                      ) : loading ? (
                        <div className="flex h-full items-center justify-center bg-slate-900 text-slate-400">
                          <span className="material-symbols-outlined animate-spin text-2xl">progress_activity</span>
                        </div>
                      ) : (
                        <img
                          src={style.imageUrl}
                          alt={style.title}
                          className="h-full w-full object-cover opacity-40 transition-transform duration-700 group-hover:scale-110"
                        />
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-900/20 to-transparent" />
                      {selected ? (
                        <span className="absolute right-3 top-3 rounded bg-[#2b6cee] px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-white">
                          Selected
                        </span>
                      ) : null}
                    </div>

                    <div className="space-y-1 p-4">
                      <p className="text-[11px] font-mono uppercase tracking-wide text-slate-500">
                        {style.id}
                      </p>
                      <h3 className="text-2xl font-bold text-slate-100">{style.title}</h3>
                      <p className="line-clamp-2 text-sm text-slate-400">{style.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {errorMessage ? (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
              {errorMessage}
            </div>
          ) : null}

          <div className="flex items-center gap-3 rounded-lg border border-[#2b6cee]/20 bg-[#2b6cee]/10 p-4">
            <span className="material-symbols-outlined shrink-0 text-[#2b6cee]">palette</span>
            <p className="text-sm text-slate-300">
              <span className="font-semibold text-[#2b6cee]">Note:</span> 레퍼런스는 초기 로딩 시 생성됩니다.
              필요하면 재생성해서 다시 선택하세요.
            </p>
            <button
              type="button"
              onClick={onRegenerate}
              className="ml-auto rounded-md border border-ts-border px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800"
              disabled={loading}
            >
              Regenerate
            </button>
          </div>
        </section>
      </main>

      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={{
          label: 'Next: Export',
          icon: 'movie_filter',
          onClick: onNext,
          disabled: !canProceed || loading,
          emphasis: 'primary',
        }}
      />
    </div>
  );
}
