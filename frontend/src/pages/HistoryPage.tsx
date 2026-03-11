import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle2, XCircle, Loader2, RefreshCw, FileAudio, FileVideo, ChevronRight, AlertTriangle } from 'lucide-react';
import { getJobs } from '../api/client';

const statusConfig = {
  completed: {
    icon: CheckCircle2,
    label: 'Готово',
    bg: 'bg-green-50',
    text: 'text-green-600',
    badge: 'bg-green-100 text-green-700',
  },
  completed_warnings: {
    icon: AlertTriangle,
    label: 'С предупреждениями',
    bg: 'bg-amber-50',
    text: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-700',
  },
  processing: {
    icon: Loader2,
    label: 'Обработка',
    bg: 'bg-blue-50',
    text: 'text-blue-600',
    badge: 'bg-blue-100 text-blue-700',
  },
  pending: {
    icon: Clock,
    label: 'В очереди',
    bg: 'bg-amber-50',
    text: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-700',
  },
  failed: {
    icon: XCircle,
    label: 'Ошибка',
    bg: 'bg-red-50',
    text: 'text-red-600',
    badge: 'bg-red-100 text-red-700',
  },
};

export function HistoryPage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => getJobs(50),
    refetchInterval: (query) => {
      // Only poll when there are active (pending/processing) jobs
      const jobs = query.state.data?.jobs;
      const hasActiveJobs = jobs?.some(j => j.status === 'pending' || j.status === 'processing');
      return hasActiveJobs ? 10000 : false;
    },
  });

  const jobs = data?.jobs || [];

  const isVideoFile = (filename: string) => /\.(mp4|mov|avi|mkv)$/i.test(filename);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">История обработок</h1>
          <p className="text-slate-500 mt-1">
            {jobs.length > 0 ? `${jobs.length} обработок` : 'Нет обработок'}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-2.5 text-slate-500 hover:text-severin-red hover:bg-red-50 rounded-xl transition-all"
          title="Обновить"
        >
          <RefreshCw className={`w-5 h-5 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-200 p-12 text-center">
          <Loader2 className="w-10 h-10 text-severin-red mx-auto mb-4 animate-spin" />
          <p className="text-slate-500">Загрузка истории...</p>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-red-200 p-12 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-slate-800 mb-2">Ошибка загрузки</h3>
          <p className="text-slate-500 mb-6">Не удалось загрузить историю обработок</p>
          <button
            onClick={() => refetch()}
            className="px-6 py-2.5 bg-severin-red text-white rounded-xl hover:bg-severin-red-dark transition-colors font-medium"
          >
            Попробовать снова
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && jobs.length === 0 && (
        <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-200 p-12 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Clock className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-800 mb-2">Нет обработок</h3>
          <p className="text-slate-500 mb-6">Загрузите первый файл для обработки</p>
          <Link
            to="/"
            className="inline-block px-6 py-2.5 bg-severin-red text-white rounded-xl hover:bg-severin-red-dark transition-colors font-medium"
          >
            Загрузить файл
          </Link>
        </div>
      )}

      {/* 24h retention notice */}
      {!isLoading && !isError && jobs.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 mb-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-700">
          <Clock className="w-4 h-4 flex-shrink-0" />
          <span>Файлы хранятся 24 часа после обработки</span>
        </div>
      )}

      {/* Jobs list */}
      {!isLoading && !isError && jobs.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-200 overflow-hidden">
          <div className="divide-y divide-slate-100">
            {jobs.map((job) => {
              const configKey = (job.status === 'completed' && job.has_warnings) ? 'completed_warnings' : job.status;
              const config = statusConfig[configKey] || statusConfig.pending;
              const Icon = config.icon;
              const isVideo = isVideoFile(job.source_file);

              return (
                <Link
                  key={job.job_id}
                  to={`/job/${job.job_id}`}
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors group"
                >
                  {/* File icon */}
                  <div className={`p-3 rounded-xl ${config.bg}`}>
                    {isVideo ? (
                      <FileVideo className={`w-5 h-5 ${config.text}`} />
                    ) : (
                      <FileAudio className={`w-5 h-5 ${config.text}`} />
                    )}
                  </div>

                  {/* File info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 truncate group-hover:text-severin-red transition-colors">
                      {job.source_file}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                      <span>{new Date(job.created_at).toLocaleString('ru-RU')}</span>
                      {job.status === 'processing' && (
                        <span className="text-blue-600 font-medium">{job.progress_percent}%</span>
                      )}
                    </div>
                  </div>

                  {/* Status badge */}
                  <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${config.badge} flex items-center gap-1.5`}>
                    <Icon className={`w-3.5 h-3.5 ${job.status === 'processing' ? 'animate-spin' : ''}`} />
                    {config.label}
                  </span>

                  {/* Arrow */}
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-400 transition-colors" />
                </Link>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
