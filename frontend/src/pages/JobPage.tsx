import { useParams, Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileVideo,
  FileAudio,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  StopCircle,
  RotateCcw,
  Download
} from 'lucide-react';
import { useJobStatus, useJobResult } from '../hooks/useJob';
import { ProgressBar } from '../components/ProgressBar';
import { DownloadCard } from '../components/DownloadCard';
import { cancelJob } from '../api/client';
import type { JobStatusResponse } from '../api/client';

export function JobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const { data: status, isLoading: statusLoading, error: statusError, refetch } = useJobStatus(jobId);
  const { data: result } = useJobResult(jobId, status?.status === 'completed');

  const cancelMutation = useMutation({
    mutationFn: () => cancelJob(jobId!),
    onSuccess: () => {
      refetch();
    },
  });

  if (!jobId) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-slate-500">Job ID не указан</p>
      </div>
    );
  }

  if (statusError) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8 text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Ошибка загрузки</h2>
          <p className="text-slate-500 mb-6">Не удалось получить информацию о задаче</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Вернуться на главную
          </Link>
        </div>
      </div>
    );
  }

  const showInitialLoading = statusLoading && !status;
  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed';
  const isProcessing = status?.status === 'processing' || status?.status === 'pending' || showInitialLoading;
  const fileName = result?.source_file || status?.message?.split('/').pop() || 'Файл';
  const isVideo = fileName.match(/\.(mp4|mov|avi|mkv)$/i);
  const loadingStatus: JobStatusResponse = {
    job_id: jobId ?? '',
    status: 'pending',
    current_stage: 'initializing',
    progress_percent: 0,
    message: 'Получаем статус задачи...',
    created_at: new Date().toISOString(),
  };
  const progressStatus = status ?? (showInitialLoading ? loadingStatus : undefined);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back button */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Новая обработка
      </Link>

      {/* Main card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-red-100 rounded-xl">
              {isVideo ? (
                <FileVideo className="w-8 h-8 text-severin-red" />
              ) : (
                <FileAudio className="w-8 h-8 text-severin-red" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-semibold text-slate-900 truncate">
                {fileName}
              </h1>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                {status?.created_at && (
                  <span>
                    {new Date(status.created_at).toLocaleString('ru-RU')}
                  </span>
                )}
                {result?.processing_time_seconds && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {Math.round(result.processing_time_seconds)}с
                  </span>
                )}
              </div>
            </div>

            {/* Status badge */}
            <div className="flex-shrink-0">
              {showInitialLoading && (
                <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 text-slate-600 rounded-full text-sm font-medium">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Подключение...
                </span>
              )}
              {isCompleted && (
                <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  Готово
                </span>
              )}
              {isFailed && (
                <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-100 text-red-700 rounded-full text-sm font-medium">
                  <XCircle className="w-4 h-4" />
                  Ошибка
                </span>
              )}
              {isProcessing && !showInitialLoading && (
                <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-100 text-severin-red rounded-full text-sm font-medium">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Обработка
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Progress section */}
        {isProcessing && progressStatus && (
          <div className="p-6 bg-red-50 border-b border-slate-100">
            <ProgressBar
              percent={progressStatus.progress_percent}
              stage={progressStatus.current_stage || undefined}
              message={progressStatus.message || undefined}
              status={progressStatus.status}
            />

            {/* Cancel button */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-red-200 text-red-600 rounded-xl hover:bg-red-50 hover:border-red-300 transition-all font-medium shadow-sm"
              >
                {cancelMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Останавливаем...
                  </>
                ) : (
                  <>
                    <StopCircle className="w-4 h-4" />
                    Остановить обработку
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Error section */}
        {isFailed && status?.error && (
          <div className="p-6 bg-red-50 border-b border-red-100">
            <div className="flex items-start gap-3">
              <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-800 mb-1">Ошибка обработки</h3>
                <p className="text-red-600 text-sm">{status.error}</p>
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={() => navigate('/')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors text-sm font-medium"
              >
                <RotateCcw className="w-4 h-4" />
                Попробовать снова
              </button>
            </div>
          </div>
        )}

        {/* Download section */}
        {isCompleted && result?.output_files && (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Download className="w-5 h-5 text-severin-red" />
              Результаты обработки
            </h2>
            <DownloadCard jobId={jobId} outputFiles={result.output_files} />
          </div>
        )}

        {/* Stats section */}
        {isCompleted && result && (
          <div className="p-6 bg-slate-50 border-t border-slate-100">
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-slate-800">
                  {result.segment_count}
                </p>
                <p className="text-sm text-slate-500 mt-1">Сегментов</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-slate-800">
                  {Object.keys(result.language_distribution).join(', ').toUpperCase() || '-'}
                </p>
                <p className="text-sm text-slate-500 mt-1">Языки</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-slate-800">
                  {Math.round(result.processing_time_seconds)}с
                </p>
                <p className="text-sm text-slate-500 mt-1">Время</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-6 flex justify-center gap-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-severin-red text-white rounded-xl hover:bg-severin-red-dark transition-colors font-medium shadow-lg shadow-severin-red/25"
        >
          Обработать ещё файл
        </Link>
        <Link
          to="/history"
          className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors font-medium"
        >
          История обработок
        </Link>
      </div>
    </div>
  );
}
