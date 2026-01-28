import { useState, useEffect } from 'react';
import { jobsApi, type AdminJobInfo } from '../../api/adminApi';

// Use AdminJobInfo directly with status union type override
type JobInfo = AdminJobInfo & {
  status: 'pending' | 'processing' | 'completed' | 'failed';
};

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'В очереди',
  processing: 'Обработка',
  completed: 'Готово',
  failed: 'Ошибка',
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const response = await jobsApi.list(100);
      setJobs(response.jobs as JobInfo[]);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCancel = async (jobId: string) => {
    if (!confirm('Остановить эту задачу?')) return;

    setCancelling(jobId);
    try {
      await jobsApi.cancel(jobId);
      await fetchJobs();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel job');
    } finally {
      setCancelling(null);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const activeJobs = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
  const completedJobs = jobs.filter(j => j.status === 'completed' || j.status === 'failed');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Очередь задач</h1>
          <p className="text-slate-500 mt-1">Мониторинг и управление обработками</p>
        </div>
        <button
          onClick={fetchJobs}
          disabled={loading}
          className="px-4 py-2 bg-severin-red hover:bg-severin-red-dark disabled:bg-slate-300 text-white rounded-lg transition flex items-center gap-2"
        >
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Обновить
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
          {error}
        </div>
      )}

      {/* Active Jobs */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <span className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></span>
            Активные задачи
            <span className="text-sm text-slate-500">({activeJobs.length})</span>
          </h2>
        </div>

        {activeJobs.length === 0 ? (
          <div className="px-6 py-8 text-center text-slate-400">
            Нет активных задач
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {activeJobs.map((job) => (
              <div key={job.job_id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[job.status]}`}>
                        {STATUS_LABELS[job.status]}
                      </span>
                      <span className="text-slate-800 font-medium truncate">{job.source_file}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-sm text-slate-500">
                      <span>{formatDate(job.created_at)}</span>
                      {job.project_code && <span>Проект: {job.project_code}</span>}
                      {job.uploader_email && <span>Загрузил: {job.uploader_email}</span>}
                    </div>
                    {job.status === 'processing' && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-slate-500">{job.current_stage || 'Обработка'}</span>
                          <span className="text-slate-800 font-medium">{job.progress_percent}%</span>
                        </div>
                        <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-severin-red transition-all duration-500"
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                        {job.message && (
                          <p className="mt-1 text-xs text-slate-400">{job.message}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleCancel(job.job_id)}
                    disabled={cancelling === job.job_id}
                    className="ml-4 px-3 py-2 bg-red-500 hover:bg-red-600 disabled:bg-slate-300 text-white text-sm rounded-lg transition flex items-center gap-1"
                  >
                    {cancelling === job.job_id ? (
                      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                    Остановить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completed Jobs */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">
            Завершённые
            <span className="text-sm text-slate-500 ml-2">({completedJobs.length})</span>
          </h2>
        </div>

        {completedJobs.length === 0 ? (
          <div className="px-6 py-8 text-center text-slate-400">
            Нет завершённых задач
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Файл</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Статус</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Проект</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Пользователь</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Дата</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {completedJobs.slice(0, 20).map((job) => (
                  <tr key={job.job_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="text-slate-800 text-sm truncate max-w-xs block">{job.source_file}</span>
                      <span className="text-slate-400 text-xs">{job.job_id.slice(0, 8)}...</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[job.status]}`}>
                        {STATUS_LABELS[job.status]}
                      </span>
                      {job.error && (
                        <p className="text-red-500 text-xs mt-1 truncate max-w-xs" title={job.error}>
                          {job.error}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-sm">{job.project_code || '—'}</td>
                    <td className="px-4 py-3 text-slate-600 text-sm">{job.uploader_email || 'Гость'}</td>
                    <td className="px-4 py-3 text-slate-500 text-sm">{formatDate(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
