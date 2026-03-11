import clsx from 'clsx';

interface ProgressBarProps {
  percent: number;
  stage?: string;
  message?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  updatedAt?: string;
  createdAt?: string;
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
  domain_generators: 'Создание документов',
  domain_report: 'Сохранение в базу',
  text_extraction: 'Извлечение текста',
  llm_generation: 'Генерация отчётов',
  llm_generators: 'Генерация отчётов',
  retry_reports: 'Повторная генерация',
  email_notification: 'Отправка уведомления',
  initializing: 'Инициализация',
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
  domain_generators: '📑',
  domain_report: '💾',
  text_extraction: '🧾',
  llm_generation: '✨',
  llm_generators: '✨',
  retry_reports: '🔄',
  email_notification: '📧',
};

export function ProgressBar({ percent, stage, message, status, updatedAt, createdAt }: ProgressBarProps) {
  const stageLabel = stage ? stageLabels[stage] || stage : '';
  const stageIcon = stage ? stageIcons[stage] || '⚙️' : '';
  const showStage = !!stage && (status === 'processing' || status === 'pending');
  const stageBadgeClass = status === 'pending' ? 'bg-amber-50' : 'bg-red-50';
  const stageTextClass = status === 'pending' ? 'text-amber-700' : 'text-severin-red';

  // Staleness detection — recalculated every render (polling every 2s, cheap)
  let staleInfo: string | null = null;
  if (status === 'pending' || status === 'processing') {
    const ref = updatedAt || createdAt;
    if (ref) {
      // Server timestamps are UTC but may lack timezone suffix — force UTC parsing
      const utcRef = ref.endsWith('Z') || ref.includes('+') ? ref : ref + 'Z';
      const elapsed = (Date.now() - new Date(utcRef).getTime()) / 60_000;
      const threshold = status === 'pending' ? 2 : 5;
      if (elapsed >= threshold) {
        staleInfo = `Задача не обновлялась ${Math.floor(elapsed)} мин`;
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="relative">
        <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full transition-all duration-500 ease-out rounded-full',
              status === 'completed' && 'bg-severin-red',
              status === 'failed' && 'bg-gradient-to-r from-red-500 to-rose-500',
              status === 'processing' && 'bg-severin-red',
              status === 'pending' && 'bg-slate-400'
            )}
            style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
          />
        </div>

        {/* Percentage badge */}
        <div className="absolute -top-1 right-0 transform translate-x-1/2">
          <span className={clsx(
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-bold',
            status === 'completed' && 'bg-red-100 text-severin-red',
            status === 'failed' && 'bg-red-100 text-red-700',
            status === 'processing' && 'bg-red-100 text-severin-red',
            status === 'pending' && 'bg-slate-100 text-slate-600'
          )}>
            {percent}%
          </span>
        </div>
      </div>

      {/* Stage and message */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {showStage && (
            <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-lg', stageBadgeClass)}>
              <span className="text-lg">{stageIcon}</span>
              <span className={clsx('font-medium', stageTextClass)}>{stageLabel}</span>
            </div>
          )}
          {status === 'completed' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg">
              <span className="text-lg">✅</span>
              <span className="font-medium text-severin-red">Завершено</span>
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

      {/* Staleness warning */}
      {staleInfo && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
          </span>
          <span className="text-sm font-medium text-amber-700">{staleInfo}</span>
        </div>
      )}
    </div>
  );
}
