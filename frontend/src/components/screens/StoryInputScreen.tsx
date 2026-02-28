import StepProgress from '../layout/StepProgress';
import TopNav from '../layout/TopNav';
import Button from '../ui/Button';
import { STORY_NAV_LINKS, STORY_PLACEHOLDER } from '../../data/workflowData';
import type { StoryInputMode } from '../../types/workflow';

interface StoryInputScreenProps {
  text: string;
  inputMode: StoryInputMode;
  charCount: number;
  onTextChange: (value: string) => void;
  onInputModeChange: (mode: StoryInputMode) => void;
  onNext: () => void;
}

export default function StoryInputScreen({
  text,
  inputMode,
  charCount,
  onTextChange,
  onInputModeChange,
  onNext,
}: StoryInputScreenProps) {
  return (
    <div className="min-h-screen">
      <TopNav
        links={STORY_NAV_LINKS}
        rightContent={
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm">
              Log In
            </Button>
            <Button variant="primary" size="sm">
              Sign Up
            </Button>
          </div>
        }
        innerClassName="max-w-[1200px] px-6 lg:px-8"
      />

      <main className="mx-auto flex w-full max-w-[980px] flex-col px-6 pb-16 pt-14 lg:px-12">
        <StepProgress
          stepLabel="STEP 1 OF 4"
          nextLabel="Next: Meta Prompt"
          labels={['Story', 'Meta', 'Visuals', 'Export']}
          currentIndex={1}
        />

        <div className="mx-auto mt-11 w-full max-w-[760px]">
          <div className="mb-10 text-center">
            <h2 className="text-5xl font-black tracking-tight text-slate-50">Tell your story</h2>
            <p className="mx-auto mt-4 max-w-[560px] text-xl text-slate-400">
              Enter the raw text or script you want to transform into a captivating teaser video.
            </p>
          </div>

          <section className="overflow-hidden rounded-2xl border border-ts-border bg-ts-panel/70">
            <div className="flex items-center justify-between border-b border-ts-border px-6 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <span className="material-symbols-outlined text-base">description</span>
                <span>Input Mode</span>
              </div>

              <div className="rounded-lg border border-ts-border bg-ts-nav p-1 text-sm">
                <button
                  type="button"
                  onClick={() => onInputModeChange('summary')}
                  className={`rounded px-3 py-1.5 transition-colors ${inputMode === 'summary'
                    ? 'bg-ts-primary text-white'
                    : 'text-ts-text-muted hover:text-ts-text'
                    }`}
                >
                  Summary
                </button>
                <button
                  type="button"
                  onClick={() => onInputModeChange('original')}
                  className={`rounded px-3 py-1.5 transition-colors ${inputMode === 'original'
                    ? 'bg-ts-primary text-white'
                    : 'text-ts-text-muted hover:text-ts-text'
                    }`}
                >
                  Original
                </button>
              </div>
            </div>

            <textarea
              className="teaser-scrollbar h-[320px] w-full resize-none bg-transparent px-6 py-6 text-lg leading-relaxed text-slate-100 outline-none placeholder:text-slate-500"
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder={STORY_PLACEHOLDER}
              aria-label="Story input"
            />

            <div className="flex items-center justify-end px-6 pb-5 pt-1 text-sm text-slate-500">
              {charCount} characters
            </div>
          </section>

          <div className="mt-10 flex items-center justify-end gap-6">
            <Button variant="ghost" size="sm">
              Save Draft
            </Button>
            <Button
              onClick={onNext}
              variant="primary"
              size="md"
              endIcon={<span className="material-symbols-outlined text-base">arrow_forward</span>}
            >
              Next: Meta Prompt
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
