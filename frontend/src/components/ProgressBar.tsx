import clsx from 'clsx';

interface ProgressBarProps {
  percent: number;
  stage?: string;
  message?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

const stageLabels: Record<string, string> = {
  audio: 'Извлечение аудио',
  audio_extraction: 'Извлечение аудио',
  vad: 'Определение голоса',
  vad_analysis: 'Определение голоса',
  transcribe: 'Транскрибация',
  transcription: 'Транскрибация',
  diarize: 'Идентификация спикеров',
  diarization: 'Идентификация спикеров',
  translate: 'Перевод',
  translation: 'Перевод',
  emotion: 'Анализ эмоций',
  emotion_analysis: 'Анализ эмоций',
  report: 'Генерация отчётов',
  report_generation: 'Генерация отчётов',
  artifacts: 'Создание документов',
  domain_artifacts: 'Создание документов',
};

const stageIcons: Record<string, string> = {
  audio_extraction: '🎵',
  vad_analysis: '🔊',
  transcription: '📝',
  diarization: '👥',
  translation: '🌐',
  emotion_analysis: '😊',
  report_generation: '📄',
  domain_artifacts: '📑',
};

export function ProgressBar({ percent, stage, message, status }: ProgressBarProps) {
  const stageLabel = stage ? stageLabels[stage] || stage : '';
  const stageIcon = stage ? stageIcons[stage] || '⚙️' : '';

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="relative">
        <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full transition-all duration-500 ease-out rounded-full',
              status === 'completed' && 'bg-[#E52713]',
              status === 'failed' && 'bg-gradient-to-r from-red-500 to-rose-500',
              status === 'processing' && 'bg-[#E52713]',
              status === 'pending' && 'bg-slate-400'
            )}
            style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
          />
        </div>

        {/* Percentage badge */}
        <div className="absolute -top-1 right-0 transform translate-x-1/2">
          <span className={clsx(
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-bold',
            status === 'completed' && 'bg-red-100 text-[#E52713]',
            status === 'failed' && 'bg-red-100 text-red-700',
            status === 'processing' && 'bg-red-100 text-[#E52713]',
            status === 'pending' && 'bg-slate-100 text-slate-600'
          )}>
            {percent}%
          </span>
        </div>
      </div>

      {/* Stage and message */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {status === 'processing' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg">
              <span className="text-lg">{stageIcon}</span>
              <span className="font-medium text-[#E52713]">{stageLabel}</span>
            </div>
          )}
          {status === 'completed' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg">
              <span className="text-lg">✅</span>
              <span className="font-medium text-[#E52713]">Завершено</span>
            </div>
          )}
          {status === 'failed' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg">
              <span className="text-lg">❌</span>
              <span className="font-medium text-red-700">Ошибка</span>
            </div>
          )}
          {status === 'pending' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 rounded-lg">
              <span className="text-lg">⏳</span>
              <span className="font-medium text-amber-700">В очереди</span>
            </div>
          )}
        </div>

        {message && (
          <span className="text-sm text-slate-500 truncate max-w-xs">{message}</span>
        )}
      </div>
    </div>
  );
}
