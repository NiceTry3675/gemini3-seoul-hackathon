import type { VideoExportModel } from '../../types/workflow';

interface VideoExportScreenProps {
  videoExport: VideoExportModel;
  onBack: () => void;
  onDownload: () => void;
}

export default function VideoExportScreen({
  videoExport,
  onBack,
  onDownload,
}: VideoExportScreenProps) {
  return (
    <div className="min-h-screen overflow-hidden bg-[#0c1427] text-slate-100">
      <header className="border-b border-slate-800 bg-[#0a1225]/90 px-6 py-4 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="size-8 text-[#2b6cee]">
              <svg className="size-full" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M8.57829 8.57829C5.52816 11.6284 3.451 15.5145 2.60947 19.7452C1.76794 23.9758 2.19984 28.361 3.85056 32.3462C5.50128 36.3314 8.29667 39.7376 11.8832 42.134C15.4698 44.5305 19.6865 45.8096 24 45.8096C28.3135 45.8096 32.5302 44.5305 36.1168 42.134C39.7033 39.7375 42.4987 36.3314 44.1494 32.3462C45.8002 28.361 46.2321 23.9758 45.3905 19.7452C44.549 15.5145 42.4718 11.6284 39.4217 8.57829L24 24L8.57829 8.57829Z"
                  fill="currentColor"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">TeaserStudio</h1>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm font-semibold uppercase tracking-wide text-slate-400">STEP 5 OF 5</span>
            <button
              type="button"
              className="rounded-lg border border-slate-700 bg-slate-800/70 px-4 py-2 text-sm font-semibold text-slate-100"
            >
              Export History
            </button>
          </div>
        </div>
      </header>

      <main className="flex min-h-[calc(100vh-148px)] overflow-hidden">
        <section className="teaser-scrollbar flex flex-1 flex-col items-center overflow-y-auto p-6">
          <div className="w-full max-w-[1120px]">
            <header className="mb-6 text-left">
              <h2 className="text-5xl font-black tracking-tight text-slate-50">{videoExport.title}</h2>
              <p className="mt-2 text-lg text-slate-400">{videoExport.subtitle}</p>
            </header>

            <article className="mx-auto w-full max-w-[980px]">
              <div className="mx-auto w-full max-w-[360px]">
                <div className="relative aspect-[9/16] overflow-hidden rounded-xl border border-slate-700 bg-black shadow-2xl">
                  <img src={videoExport.previewImageUrl} alt="Teaser preview" className="h-full w-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-transparent to-black/70" />

                  <button
                    type="button"
                    aria-label="Play preview"
                    className="absolute inset-0 flex items-center justify-center"
                  >
                    <span className="flex size-16 items-center justify-center rounded-full border border-white/30 bg-white/20 backdrop-blur-sm">
                      <span className="material-symbols-outlined text-4xl">play_arrow</span>
                    </span>
                  </button>

                  <div className="absolute inset-x-0 bottom-0 px-4 py-4">
                    <div className="h-1 rounded-full bg-white/30">
                      <div className="h-full w-1/3 rounded-full bg-[#2b6cee]" />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs font-medium text-white">
                      <span>0:05 / 0:15</span>
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-lg">volume_up</span>
                        <span className="material-symbols-outlined text-lg">fullscreen</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-8">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Source Frames</p>
                <div
                  className="grid gap-3"
                  style={{ gridTemplateColumns: `repeat(${videoExport.sourceFrames.length}, minmax(0, 1fr))` }}
                >
                  {videoExport.sourceFrames.map((frame) => (
                    <div
                      key={frame.index}
                      className="relative aspect-video overflow-hidden rounded-lg border border-slate-700"
                    >
                      <img src={frame.imageUrl} alt={`Frame ${frame.index}`} className="h-full w-full object-cover" />
                      <span className="absolute bottom-1 right-1 rounded bg-black/65 px-1 text-[10px] font-mono text-white">
                        {String(frame.index).padStart(2, '0')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </article>
          </div>
        </section>

        <aside className="hidden w-80 shrink-0 border-l border-slate-800 bg-[#131c30] lg:flex lg:flex-col">
          <div className="border-b border-slate-800 p-6">
            <h3 className="text-3xl font-bold text-slate-100">Video Settings</h3>
            <p className="mt-1 text-sm text-slate-400">Configuration used for generation</p>
          </div>

          <div className="space-y-6 p-6">
            {[
              { icon: 'music_note', label: 'Music Style', value: videoExport.settings.musicStyle },
              { icon: 'transition_push', label: 'Transition', value: videoExport.settings.transition },
              { icon: 'timer', label: 'Duration', value: videoExport.settings.duration },
              { icon: 'aspect_ratio', label: 'Format', value: videoExport.settings.format },
            ].map((item) => (
              <div key={item.label} className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <span className="material-symbols-outlined text-lg">{item.icon}</span>
                  <span>{item.label}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800/80 p-3 text-base text-slate-100">
                  <span>{item.value}</span>
                  <span className="material-symbols-outlined text-[#2b6cee]">tune</span>
                </div>
              </div>
            ))}
          </div>

        </aside>
      </main>

      <footer className="border-t border-slate-800 bg-[#0a1225]/90 p-6">
        <div className="mx-auto flex w-full max-w-[1100px] items-center justify-between">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-slate-400 transition-colors hover:text-slate-100"
          >
            <span className="material-symbols-outlined text-xl">arrow_back</span>
            <span className="font-medium">Back</span>
          </button>

          <div className="flex items-center gap-4">
            <span className="hidden text-xs text-slate-500 sm:block">
              Rendering complete ({videoExport.renderSeconds}s)
            </span>
            <button
              type="button"
              onClick={onDownload}
              className="inline-flex min-w-[220px] items-center justify-center gap-2 rounded-lg bg-[#2b6cee] px-6 py-3 font-bold text-white shadow-lg shadow-blue-500/20 transition-colors hover:bg-blue-600"
            >
              <span className="material-symbols-outlined">download</span>
              Download Short-form
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
