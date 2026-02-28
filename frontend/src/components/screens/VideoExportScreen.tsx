import { useState, useCallback } from 'react';
import type { VideoExportModel } from '../../types/workflow';
import { startVideoGeneration } from '../../services/workflowService';
import type { VideoGenCallbacks } from '../../services/workflowService';

interface VideoExportScreenProps {
  videoExport: VideoExportModel;
  storyText: string;
  onBack: () => void;
  onDownload: () => void;
  onReset: () => void;
}

export default function VideoExportScreen({
  videoExport,
  storyText,
  onBack,
  onDownload,
  onReset,
}: VideoExportScreenProps) {
  const [videoStatus, setVideoStatus] = useState<'idle' | 'generating' | 'complete' | 'error'>('idle');
  const [videoProgress, setVideoProgress] = useState(0);
  const [videoMessage, setVideoMessage] = useState('');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);

  const handleGenerateVideo = useCallback(async () => {
    setVideoStatus('generating');
    setVideoProgress(0);
    setVideoError(null);

    const cutsBase64 = videoExport.sourceFrames.map((frame) => {
      const prefix = 'data:image/png;base64,';
      return frame.imageUrl.startsWith(prefix)
        ? frame.imageUrl.slice(prefix.length)
        : frame.imageUrl;
    });

    const callbacks: VideoGenCallbacks = {
      onProgress: (progress, message) => {
        setVideoProgress(progress);
        setVideoMessage(message);
      },
      onComplete: (videoBase64, _duration) => {
        setVideoUrl(`data:video/mp4;base64,${videoBase64}`);
        setVideoStatus('complete');
      },
      onError: (error) => {
        setVideoError(error);
        setVideoStatus('error');
      },
    };

    try {
      await startVideoGeneration(cutsBase64, callbacks, undefined, storyText);
    } catch (err) {
      setVideoError(err instanceof Error ? err.message : 'Video generation failed');
      setVideoStatus('error');
    }
  }, [videoExport.sourceFrames, storyText]);

  return (
    <div className="min-h-screen bg-[#0c1427] text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800/60 bg-[#0a1225]/90 px-6 py-4 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-[#2b6cee]/15">
              <span className="material-symbols-outlined text-xl text-[#2b6cee]">smart_display</span>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">TeaserStudio</h1>
              <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Video Export</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700/60 bg-slate-800/50 px-3 py-1 text-xs text-slate-400">
              <span className="material-symbols-outlined text-sm text-[#2b6cee]">auto_awesome</span>
              Powered by Veo 3.1
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-6 py-8 lg:flex-row lg:px-10">
        {/* Left: Video Preview */}
        <section className="flex flex-1 flex-col items-center">
          <div className="w-full max-w-[420px]">
            {/* Video Card */}
            <div className="relative overflow-hidden rounded-2xl border border-slate-700/50 bg-[#111827] shadow-2xl shadow-black/40">
              <div className="relative aspect-[9/16] bg-black">
                {videoStatus === 'complete' && videoUrl ? (
                  <video
                    src={videoUrl}
                    controls
                    autoPlay
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <>
                    <img
                      src={videoExport.previewImageUrl}
                      alt="Teaser preview"
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/80" />

                    {/* Idle: Generate button */}
                    {videoStatus === 'idle' && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                        <button
                          type="button"
                          onClick={handleGenerateVideo}
                          className="group flex flex-col items-center gap-3 transition-transform hover:scale-105"
                        >
                          <span className="flex size-20 items-center justify-center rounded-full bg-[#2b6cee] shadow-lg shadow-blue-500/30 transition-shadow group-hover:shadow-blue-500/50">
                            <span className="material-symbols-outlined text-5xl text-white">play_arrow</span>
                          </span>
                          <span className="rounded-full bg-black/50 px-5 py-2 text-sm font-bold text-white backdrop-blur-md">
                            Generate Video with Veo 3.1
                          </span>
                        </button>
                        <p className="max-w-[240px] text-center text-xs text-white/50">
                          AI will animate your first frame into a cinematic teaser video
                        </p>
                      </div>
                    )}

                    {/* Generating: Progress */}
                    {videoStatus === 'generating' && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-5 bg-black/40 px-8 backdrop-blur-sm">
                        <div className="relative">
                          <div className="size-20 rounded-full border-4 border-slate-600/50" />
                          <div className="absolute inset-0 size-20 animate-spin rounded-full border-4 border-[#2b6cee] border-t-transparent" />
                          <span className="material-symbols-outlined absolute inset-0 m-auto flex h-8 w-8 items-center justify-center text-[#2b6cee]">
                            movie
                          </span>
                        </div>
                        <div className="w-full max-w-[280px] space-y-2">
                          <p className="text-center text-sm font-semibold text-white">
                            {videoMessage || 'Generating video...'}
                          </p>
                          <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#2b6cee] to-[#6d9ef7] transition-all duration-500"
                              style={{ width: `${videoProgress}%` }}
                            />
                          </div>
                          <p className="text-center text-xs text-white/40">
                            Veo 3.1 processing · This may take 1-5 minutes
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Error */}
                    {videoStatus === 'error' && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black/50 px-6 backdrop-blur-sm">
                        <div className="flex size-16 items-center justify-center rounded-full bg-red-500/20">
                          <span className="material-symbols-outlined text-4xl text-red-400">warning</span>
                        </div>
                        <div className="text-center">
                          <p className="font-semibold text-red-300">Generation Failed</p>
                          <p className="mt-1 text-xs leading-relaxed text-red-200/60">{videoError}</p>
                        </div>
                        <button
                          type="button"
                          onClick={handleGenerateVideo}
                          className="rounded-full bg-[#2b6cee] px-5 py-2 text-sm font-bold text-white shadow-lg transition-colors hover:bg-blue-500"
                        >
                          Retry
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Video status bar */}
              <div className="flex items-center justify-between border-t border-slate-700/40 bg-[#0d162c] px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className={`size-2 rounded-full ${
                    videoStatus === 'complete' ? 'bg-emerald-400' :
                    videoStatus === 'generating' ? 'animate-pulse bg-[#2b6cee]' :
                    videoStatus === 'error' ? 'bg-red-400' : 'bg-slate-500'
                  }`} />
                  <span className="text-xs font-medium text-slate-400">
                    {videoStatus === 'complete' ? 'Video Ready' :
                     videoStatus === 'generating' ? 'Processing...' :
                     videoStatus === 'error' ? 'Failed' : 'Ready to generate'}
                  </span>
                </div>
                {videoStatus === 'complete' && videoUrl && (
                  <a
                    href={videoUrl}
                    download="teaser-video.mp4"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#2b6cee] hover:text-blue-400"
                  >
                    <span className="material-symbols-outlined text-sm">download</span>
                    Save MP4
                  </a>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Right: Source Frames + Settings */}
        <section className="w-full space-y-6 lg:w-[480px] lg:shrink-0">
          {/* Title */}
          <div>
            <h2 className="text-3xl font-black tracking-tight text-slate-50">{videoExport.title}</h2>
            <p className="mt-1 text-sm text-slate-400">{videoExport.subtitle}</p>
          </div>

          {/* Source Frames 3x3 Grid */}
          <div className="rounded-xl border border-slate-700/50 bg-[#111827]/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <span className="material-symbols-outlined text-base text-[#2b6cee]">grid_view</span>
                Source Frames
              </div>
              <span className="text-[10px] text-slate-500">{videoExport.sourceFrames.length} cuts</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {videoExport.sourceFrames.map((frame) => (
                <div
                  key={frame.index}
                  className="group relative aspect-square overflow-hidden rounded-lg border border-slate-700/30 bg-slate-800/50"
                >
                  <img
                    src={frame.imageUrl}
                    alt={`Cut ${frame.index}`}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                  <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[9px] font-bold tabular-nums text-white">
                    {String(frame.index).padStart(2, '0')}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Settings */}
          <div className="rounded-xl border border-slate-700/50 bg-[#111827]/80 p-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span className="material-symbols-outlined text-base text-[#2b6cee]">tune</span>
              Video Settings
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { icon: 'music_note', label: 'Music', value: videoExport.settings.musicStyle },
                { icon: 'transition_push', label: 'Transition', value: videoExport.settings.transition },
                { icon: 'timer', label: 'Duration', value: videoExport.settings.duration },
                { icon: 'aspect_ratio', label: 'Format', value: videoExport.settings.format },
              ].map((item) => (
                <div key={item.label} className="rounded-lg border border-slate-700/30 bg-slate-800/40 p-3">
                  <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                    <span className="material-symbols-outlined text-xs">{item.icon}</span>
                    {item.label}
                  </div>
                  <p className="mt-1 text-sm font-semibold text-slate-200">{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-3">
            {videoStatus !== 'generating' && (
              <button
                type="button"
                onClick={videoStatus === 'complete' ? onDownload : handleGenerateVideo}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#2b6cee] px-6 py-4 text-base font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-500 hover:shadow-blue-500/30"
              >
                <span className="material-symbols-outlined text-xl">
                  {videoStatus === 'complete' ? 'download' : 'smart_display'}
                </span>
                {videoStatus === 'complete' ? 'Download Short-form' : 'Generate Video'}
              </button>
            )}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onBack}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-3 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-700/50"
              >
                <span className="material-symbols-outlined text-base">arrow_back</span>
                Back
              </button>
              <button
                type="button"
                onClick={onReset}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-3 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-700/50"
              >
                <span className="material-symbols-outlined text-base">restart_alt</span>
                Start Over
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
