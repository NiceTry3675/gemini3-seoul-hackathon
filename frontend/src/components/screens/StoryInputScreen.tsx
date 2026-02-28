import TopNav from '../layout/TopNav';
import Button from '../ui/Button';
import {
  PIPELINE_LANGUAGE_OPTIONS,
  PIPELINE_STYLE_OPTIONS,
  STORY_NAV_LINKS,
} from '../../data/workflowData';
import type {
  PipelineOutputLanguage,
  PipelineStyleTemplate,
} from '../../types/workflow';

interface StoryInputScreenProps {
  manuscript: string;
  outputLanguage: PipelineOutputLanguage;
  styleTemplate: PipelineStyleTemplate;
  canSubmit: boolean;
  onManuscriptChange: (value: string) => void;
  onOutputLanguageChange: (value: PipelineOutputLanguage) => void;
  onStyleTemplateChange: (value: PipelineStyleTemplate) => void;
  onSubmit: () => void;
}

export default function StoryInputScreen({
  manuscript,
  outputLanguage,
  styleTemplate,
  canSubmit,
  onManuscriptChange,
  onOutputLanguageChange,
  onStyleTemplateChange,
  onSubmit,
}: StoryInputScreenProps) {
  return (
    <div className="min-h-screen">
      <TopNav links={STORY_NAV_LINKS} innerClassName="max-w-[1200px] px-6 lg:px-10" />

      <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-8 px-6 pb-16 pt-10 lg:px-10">
        <section className="space-y-2">
          <h2 className="text-4xl font-black tracking-tight text-slate-50">Create 9-Cut Teaser</h2>
          <p className="max-w-3xl text-slate-400">
            Backend pipeline 기준 입력값을 채우고 생성을 시작하세요. 결과는 9컷 이미지 그리드로 표시됩니다.
          </p>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-ts-border bg-ts-panel/70 p-6 md:grid-cols-2">
          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-slate-200">Output Language</span>
            <select
              value={outputLanguage}
              onChange={(event) => onOutputLanguageChange(event.target.value as PipelineOutputLanguage)}
              className="rounded-lg border border-ts-border bg-[#101624] px-3 py-2 text-slate-100 outline-none focus:border-ts-primary"
            >
              {PIPELINE_LANGUAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-slate-200">Style Template</span>
            <select
              value={styleTemplate}
              onChange={(event) => onStyleTemplateChange(event.target.value as PipelineStyleTemplate)}
              className="rounded-lg border border-ts-border bg-[#101624] px-3 py-2 text-slate-100 outline-none focus:border-ts-primary"
            >
              {PIPELINE_STYLE_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.title}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="overflow-hidden rounded-2xl border border-ts-border bg-ts-panel/70">
          <div className="border-b border-ts-border px-6 py-3 text-sm font-semibold text-slate-200">
            Manuscript
          </div>
          <textarea
            className="teaser-scrollbar h-[360px] w-full resize-none bg-transparent px-6 py-5 leading-relaxed text-slate-100 outline-none placeholder:text-slate-500"
            value={manuscript}
            onChange={(event) => onManuscriptChange(event.target.value)}
            placeholder="소설 초반 텍스트를 입력하세요."
            aria-label="Manuscript"
          />
          <div className="px-6 pb-4 text-right text-xs text-slate-500">
            {manuscript.length.toLocaleString()} chars
          </div>
        </section>

        <div className="flex justify-end">
          <Button
            onClick={onSubmit}
            disabled={!canSubmit}
            variant="primary"
            size="md"
            endIcon={<span className="material-symbols-outlined text-base">play_arrow</span>}
          >
            Start Pipeline Generation
          </Button>
        </div>
      </main>
    </div>
  );
}
