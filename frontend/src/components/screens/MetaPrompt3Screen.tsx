import BottomActionBar from '../layout/BottomActionBar';
import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import { PRIMARY_NAV_LINKS } from '../../data/workflowData';
import type { VisualStyleId } from '../../types/workflow';

interface MetaPrompt3ScreenProps {
  selectedStyle: VisualStyleId | null;
  selectedReferenceImage: { imageBase64: string; mimeType: string } | null;
  anchorPrompt: string;
  cutPrompts: Array<{ cutNumber: number; prompt: string }>;
  onCutPromptChange: (cutNumber: number, prompt: string) => void;
  onResetPrompts: () => void;
  onStartOver: () => void;
  onGenerateTeaser: () => void;
  onBack: () => void;
}

export default function MetaPrompt3Screen({
  selectedStyle,
  selectedReferenceImage,
  anchorPrompt,
  cutPrompts,
  onCutPromptChange,
  onResetPrompts,
  onStartOver,
  onGenerateTeaser,
  onBack,
}: MetaPrompt3ScreenProps) {
  const canExport = selectedStyle !== null && selectedReferenceImage !== null;

  return (
    <div className="min-h-screen">
      <TopNav links={PRIMARY_NAV_LINKS} />
      <main className="mx-auto flex w-full max-w-[1200px] flex-col px-6 pb-36 pt-10 lg:px-10">
        <StepProgress stepLabel="STEP 4 OF 5" nextLabel="Next: Generate" labels={['Story', 'Meta', 'Visuals', 'Export', 'Video']} currentIndex={4} />
        <section className="mx-auto mt-10 w-full max-w-[980px] space-y-8">
          <div className="space-y-2">
            <h2 className="text-5xl font-black tracking-tight text-slate-50">Export Preparation</h2>
            <p className="text-lg text-slate-400">프롬프트를 확인/수정한 뒤, 선택한 레퍼런스를 포함해 최종 이미지를 생성합니다.</p>
          </div>
          <div className="rounded-2xl border border-slate-700 bg-[#111827] p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-mono uppercase tracking-wide text-slate-500">Selected Style Template</p>
                <p className="mt-1 text-lg font-semibold text-slate-100">{selectedStyle ?? 'None selected'}</p>
              </div>
              <button type="button" onClick={onResetPrompts} className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800">Reset Prompts</button>
            </div>
            <div className="mt-4 overflow-hidden rounded-xl border border-slate-700 bg-slate-900">
              {selectedReferenceImage ? (
                <img src={`data:${selectedReferenceImage.mimeType};base64,${selectedReferenceImage.imageBase64}`} alt="Selected reference" className="h-[300px] w-full object-cover" />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-slate-400">Reference image not selected.</div>
              )}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-700 bg-[#111827] p-5">
            <p className="text-xs font-mono uppercase tracking-wide text-slate-500">Anchor Prompt</p>
            <pre className="teaser-scrollbar mt-2 max-h-40 overflow-auto rounded-lg border border-slate-700 bg-[#0f172a] p-3 text-xs leading-relaxed text-slate-200">{anchorPrompt || 'No anchor prompt'}</pre>
          </div>
          <div className="space-y-3 rounded-2xl border border-slate-700 bg-[#111827] p-5">
            <p className="text-xs font-mono uppercase tracking-wide text-slate-500">Cut Prompts (Editable)</p>
            {cutPrompts.map((item) => (
              <div key={item.cutNumber} className="space-y-2 rounded-lg border border-slate-700 bg-[#0f172a] p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cut {String(item.cutNumber).padStart(2, '0')}</p>
                <textarea className="teaser-scrollbar h-24 w-full resize-y rounded border border-slate-700 bg-[#111827] px-3 py-2 text-sm text-slate-100 outline-none focus:border-[#2b6cee]" value={item.prompt} onChange={(event) => onCutPromptChange(item.cutNumber, event.target.value)} />
              </div>
            ))}
          </div>
          {!canExport && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">Visuals 단계에서 레퍼런스 이미지를 선택해야 Export를 시작할 수 있습니다.</div>
          )}
        </section>
      </main>
      <BottomActionBar
        backAction={{ label: 'Back', icon: 'arrow_back', onClick: onBack, emphasis: 'outline' }}
        primaryAction={{ label: 'Start Export Generation', icon: 'auto_awesome', onClick: onGenerateTeaser, disabled: !canExport, emphasis: 'primary' }}
        hint="Export는 선택 레퍼런스 + 수정한 컷 프롬프트로 이미지를 생성합니다."
      />
      <button type="button" onClick={onStartOver} className="fixed bottom-24 left-6 rounded-lg border border-slate-700 bg-[#0d162c]/90 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 lg:left-10">
        <span className="material-symbols-outlined mr-1 align-middle text-sm">restart_alt</span>Start Over
      </button>
    </div>
  );
}
