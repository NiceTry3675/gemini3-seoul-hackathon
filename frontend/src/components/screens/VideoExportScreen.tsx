import type { PipelineResultModel } from '../../types/workflow';

interface VideoExportScreenProps {
  result: PipelineResultModel;
  onBack: () => void;
  onDownload: () => void;
}

function toDataUrl(mimeType: string, base64: string): string {
  return `data:${mimeType};base64,${base64}`;
}

export default function VideoExportScreen({
  result,
  onBack,
  onDownload,
}: VideoExportScreenProps) {
  const cuts = [...result.cuts].sort((a, b) => a.cut_number - b.cut_number);

  return (
    <div className="min-h-screen bg-[#0c1427] text-slate-100">
      <header className="border-b border-slate-800 bg-[#0a1225]/90 px-6 py-4">
        <div className="mx-auto flex w-full max-w-[1280px] items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">TeaserStudio Result</h1>
          <button
            type="button"
            onClick={onDownload}
            className="inline-flex items-center gap-2 rounded-lg bg-[#2b6cee] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600"
          >
            <span className="material-symbols-outlined text-base">download</span>
            Download JSON
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[1280px] flex-col gap-8 px-6 py-8">
        <section className="rounded-2xl border border-slate-800 bg-[#101a30] p-5">
          <h2 className="text-lg font-semibold">Characters</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            {result.characters.characters.map((character) => (
              <article key={character.name} className="rounded-lg border border-slate-700 bg-[#0d162b] p-4">
                <h3 className="font-semibold text-slate-100">{character.name}</h3>
                <p className="mt-1 text-sm text-slate-400">{character.role}</p>
                <p className="mt-2 text-sm text-slate-300">{character.appearance}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-bold">9-Cut Grid</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {cuts.map((cut) => (
              <article key={cut.cut_number} className="overflow-hidden rounded-xl border border-slate-700 bg-[#111a2f]">
                <div className="relative aspect-square bg-black">
                  {cut.image_base64 ? (
                    <img
                      src={toDataUrl(cut.mime_type || 'image/png', cut.image_base64)}
                      alt={`Cut ${cut.cut_number}`}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-slate-500">
                      Image unavailable
                    </div>
                  )}
                  <span className="absolute left-2 top-2 rounded bg-black/70 px-2 py-1 text-xs font-semibold">
                    CUT {String(cut.cut_number).padStart(2, '0')}
                  </span>
                </div>

                <div className="space-y-2 p-3 text-sm">
                  <p className="text-slate-300">{cut.description}</p>
                  {cut.dialogue.length > 0 ? (
                    <p className="text-slate-400">Dialogue: {cut.dialogue.join(' / ')}</p>
                  ) : null}
                  {cut.narration ? <p className="text-slate-400">Narration: {cut.narration}</p> : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        {result.validation_report ? (
          <section className="rounded-2xl border border-slate-800 bg-[#101a30] p-5">
            <h2 className="text-lg font-semibold">Validation</h2>
            <p className="mt-2 text-sm text-slate-300">{result.validation_report.summary}</p>
          </section>
        ) : null}

        <footer className="flex items-center justify-between">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-slate-300 hover:text-white"
          >
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to Input
          </button>
        </footer>
      </main>
    </div>
  );
}
