import { useState, useEffect, useCallback } from 'react';
import {
  FileText, FileSpreadsheet, Shield, BookOpen, Download, Loader2, Archive, X, ChevronLeft,
} from 'lucide-react';
import { jobsApi, type AdminJobsListResponse, type JobReportData } from '../../api/adminApi';
import { downloadJobFile, downloadJobFileAll } from '../../api/client';
import { getApiErrorMessage } from '../../utils/errorMessage';
import { useConfirm } from '../../hooks/useConfirm';

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  expired: 'bg-slate-100 text-slate-500',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'В очереди',
  processing: 'Обработка',
  completed: 'Готово',
  failed: 'Ошибка',
  expired: 'Истекло',
};

const PRIORITY_STYLES: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
};

const ARTIFACT_CONFIG: Record<string, {
  label: string;
  icon: typeof FileText;
  color: string;
  desc: string;
}> = {
  transcript: {
    label: 'Стенограмма',
    icon: FileText,
    color: 'border-red-200 bg-red-50 text-severin-red hover:bg-red-100',
    desc: 'Полный текст с таймкодами',
  },
  tasks: {
    label: 'Excel отчёт',
    icon: FileSpreadsheet,
    color: 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100',
    desc: 'Задачи и поручения',
  },
  report: {
    label: 'Word отчёт',
    icon: FileText,
    color: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
    desc: 'Протокол совещания',
  },
  risk_brief: {
    label: 'Риск-бриф',
    icon: Shield,
    color: 'border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100',
    desc: 'Матрица рисков',
  },
  summary: {
    label: 'Конспект',
    icon: BookOpen,
    color: 'border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100',
    desc: 'Тематический разбор встречи',
  },
};

const PAGE_SIZE = 25;

// ─── Artifact Content Viewer ─────────────────────────────────────────────────

function ArtifactContentView({
  artifactType,
  report,
}: {
  artifactType: string;
  report: JobReportData;
}) {
  const br = report.basic_report;

  if (artifactType === 'transcript' && report.transcript_text) {
    return (
      <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
        {report.transcript_text}
      </pre>
    );
  }

  if (artifactType === 'report') {
    // Construction: structured JSON from basic_report
    if (br) {
      return (
        <div className="space-y-6 max-w-4xl">
          {br.meeting_type && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Тип совещания</h4>
              <p className="text-slate-800">{br.meeting_type}</p>
            </div>
          )}
          {br.meeting_summary && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Краткое содержание</h4>
              <p className="text-slate-700 whitespace-pre-wrap leading-relaxed">{br.meeting_summary}</p>
            </div>
          )}
          {br.expert_analysis && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Экспертный анализ</h4>
              <p className="text-slate-700 whitespace-pre-wrap leading-relaxed">{br.expert_analysis}</p>
            </div>
          )}
        </div>
      );
    }
    // Other domains: plain text from DOCX
    if (report.report_text) {
      return (
        <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed max-w-4xl">
          {report.report_text}
        </pre>
      );
    }
  }

  if (artifactType === 'tasks') {
    // Construction: structured tasks from basic_report JSON
    if (br?.tasks && br.tasks.length > 0) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">#</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Задача</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Ответственный</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Срок</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Категория</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Приоритет</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Примечание</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {br.tasks.map((task, i) => (
              <tr key={i} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                <td className="px-3 py-2 text-slate-800 max-w-md">
                  <p>{task.description}</p>
                  {task.evidence && (
                    <p className="text-xs text-slate-400 mt-1 italic">&ldquo;{task.evidence}&rdquo;</p>
                  )}
                </td>
                <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{task.responsible}</td>
                <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{task.deadline || '—'}</td>
                <td className="px-3 py-2">
                  <span className="px-1.5 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">{task.category}</span>
                </td>
                <td className="px-3 py-2">
                  <span className={`px-1.5 py-0.5 text-xs rounded ${PRIORITY_STYLES[task.priority] || 'bg-slate-100 text-slate-600'}`}>
                    {task.priority}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-500 text-xs max-w-xs">{task.notes || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    }
    // Other domains: table from XLSX rows
    if (report.tasks_data && report.tasks_data.length > 0) {
      const headers = Object.keys(report.tasks_data[0]);
      return (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">#</th>
                {headers.map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.tasks_data.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                  {headers.map((h) => (
                    <td key={h} className="px-3 py-2 text-slate-700 text-sm">{row[h] || '—'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  }

  if (artifactType === 'risk_brief' && report.risk_brief) {
    const rb = report.risk_brief as Record<string, string | Array<Record<string, string>>>;
    const execSummary = typeof rb.executive_summary === 'string' ? rb.executive_summary : '';
    const status = typeof rb.overall_status === 'string' ? rb.overall_status : '';
    const atmosphere = typeof rb.atmosphere === 'string' ? rb.atmosphere : '';
    const risks = Array.isArray(rb.risks) ? rb.risks : [];
    const concerns = Array.isArray(rb.concerns) ? rb.concerns : [];

    return (
      <div className="space-y-6 max-w-4xl">
        {execSummary && (
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Резюме</h4>
            <p className="text-slate-700 whitespace-pre-wrap leading-relaxed">{execSummary}</p>
          </div>
        )}
        {status && (
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Общий статус</h4>
            <p className="text-slate-700">{status}</p>
          </div>
        )}
        {atmosphere && (
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Атмосфера</h4>
            <p className="text-slate-700">{atmosphere}</p>
          </div>
        )}
        {risks.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Риски ({risks.length})</h4>
            <div className="space-y-2">
              {risks.map((risk, i) => (
                <div key={i} className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <p className="text-sm text-slate-800 font-medium">{String(risk.description || risk.title || `Риск ${i + 1}`)}</p>
                  {risk.mitigation && <p className="text-xs text-slate-500 mt-1">Митигация: {String(risk.mitigation)}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
        {concerns.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Незакрытые вопросы ({concerns.length})</h4>
            <ul className="space-y-1">
              {concerns.map((c, i) => (
                <li key={i} className="text-sm text-slate-700 flex gap-2">
                  <span className="text-slate-400">{i + 1}.</span>
                  <span>{String(c.description || c.text || c)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return <p className="text-slate-400 text-center py-8">Нет данных для просмотра</p>;
}

// ─── Report Modal (2-level: cards → viewer) ──────────────────────────────────

function ReportModal({
  open,
  onClose,
  jobId,
  artifacts,
  report,
  loading,
  error,
}: {
  open: boolean;
  onClose: () => void;
  jobId: string;
  artifacts: Record<string, string>;
  report: JobReportData | null;
  loading: boolean;
  error: string | null;
}) {
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  if (!open) return null;

  const artifactTypes = Object.keys(artifacts).filter(t => t !== 'analysis');

  const handleDownload = async (fileType: string) => {
    setDownloading(fileType);
    try {
      await downloadJobFile(jobId, fileType);
    } catch {
      // silent — user sees the file was triggered
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadAll = async () => {
    setDownloading('all');
    try {
      await downloadJobFileAll(jobId);
    } catch {
      // silent
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-[92vw] h-[88vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-3">
            {selectedArtifact ? (
              <button
                onClick={() => setSelectedArtifact(null)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-white hover:bg-slate-700 rounded-lg transition text-sm"
              >
                <ChevronLeft className="w-4 h-4" />
                Назад
              </button>
            ) : null}
            <h3 className="text-lg font-semibold text-slate-800">
              {selectedArtifact
                ? ARTIFACT_CONFIG[selectedArtifact]?.label || selectedArtifact
                : 'Артефакты задачи'
              }
            </h3>
            <span className="text-xs text-slate-400">{jobId.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-2">
            {selectedArtifact && (
              <button
                onClick={() => handleDownload(selectedArtifact)}
                disabled={downloading !== null}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-lg border border-slate-200 transition disabled:opacity-50"
              >
                {downloading === selectedArtifact ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Скачать
              </button>
            )}
            <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg transition">
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
            </div>
          ) : error ? (
            <div className="text-red-500 text-center py-8">{error}</div>
          ) : !selectedArtifact ? (
            /* ─── Level 1: Artifact Cards ─── */
            <div className="grid gap-3 sm:grid-cols-2 max-w-3xl mx-auto">
              {/* Download All */}
              <button
                onClick={handleDownloadAll}
                disabled={downloading !== null}
                className="flex items-center gap-4 p-4 rounded-xl border-2 border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 transition-all sm:col-span-2 disabled:opacity-50"
              >
                <div className="p-2 bg-white rounded-lg shadow-sm">
                  {downloading === 'all' ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <Archive className="w-6 h-6" />
                  )}
                </div>
                <div className="flex-1 min-w-0 text-left">
                  <p className="font-semibold">Скачать все файлы</p>
                  <p className="text-sm opacity-70">Архив со всеми результатами</p>
                </div>
                <Download className="w-5 h-5 opacity-50" />
              </button>

              {/* Artifact cards */}
              {artifactTypes.map((type) => {
                const config = ARTIFACT_CONFIG[type] || {
                  label: type,
                  icon: FileText,
                  color: 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100',
                  desc: 'Файл',
                };
                const Icon = config.icon;
                return (
                  <button
                    key={type}
                    onClick={() => setSelectedArtifact(type)}
                    className={`flex items-center gap-4 p-4 rounded-xl border-2 transition-all cursor-pointer ${config.color}`}
                  >
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                      <Icon className="w-6 h-6" />
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                      <p className="font-semibold">{config.label}</p>
                      <p className="text-sm opacity-70">{config.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            /* ─── Level 2: Artifact Content ─── */
            report ? (
              <ArtifactContentView artifactType={selectedArtifact} report={report} />
            ) : (
              <p className="text-slate-400 text-center py-8">Нет данных</p>
            )
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function JobsPage() {
  const { confirm, alert, ConfirmDialog } = useConfirm();
  const [data, setData] = useState<AdminJobsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [filterEmail, setFilterEmail] = useState('');
  const [page, setPage] = useState(1);

  // Report modal
  const [modalOpen, setModalOpen] = useState(false);
  const [modalJobId, setModalJobId] = useState('');
  const [modalArtifacts, setModalArtifacts] = useState<Record<string, string>>({});
  const [modalReport, setModalReport] = useState<JobReportData | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string | number> = { limit: PAGE_SIZE, page };
      if (filterStatus) params.status = filterStatus;
      if (filterDomain) params.domain = filterDomain;
      if (filterEmail) params.user_email = filterEmail;

      const response = await jobsApi.list(params);
      setData(response);
      setError(null);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка загрузки задач'));
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, filterDomain, filterEmail]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 15000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  useEffect(() => { setPage(1); }, [filterStatus, filterDomain, filterEmail]);

  const handleCancel = async (jobId: string) => {
    if (!(await confirm('Остановить эту задачу?', { variant: 'danger' }))) return;
    setCancelling(jobId);
    try {
      await jobsApi.cancel(jobId);
      await fetchJobs();
    } catch (err) {
      await alert(getApiErrorMessage(err, 'Не удалось остановить задачу'));
    } finally {
      setCancelling(null);
    }
  };

  const handlePurge = async (jobId: string, fileName: string | null) => {
    if (!(await confirm(
      `Полностью удалить задачу${fileName ? ` "${fileName}"` : ''}?\nБудут удалены: запись в БД, файлы загрузки и результаты.`,
      { variant: 'danger' }
    ))) return;
    setDeleting(jobId);
    try {
      await jobsApi.purge(jobId);
      await fetchJobs();
    } catch (err) {
      await alert(getApiErrorMessage(err, 'Не удалось удалить задачу'));
    } finally {
      setDeleting(null);
    }
  };

  const handleOpenReport = async (jobId: string, artifacts: Record<string, string>) => {
    setModalJobId(jobId);
    setModalArtifacts(artifacts);
    setModalOpen(true);
    setModalLoading(true);
    setModalReport(null);
    setModalError(null);

    try {
      const reportData = await jobsApi.getReport(jobId);
      setModalReport(reportData);
    } catch (err) {
      setModalError(getApiErrorMessage(err, 'Не удалось загрузить данные отчёта'));
    } finally {
      setModalLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—';
    if (seconds < 60) return `${Math.round(seconds)}с`;
    return `${Math.floor(seconds / 60)}м ${Math.round(seconds % 60)}с`;
  };

  const jobs = data?.jobs || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const activeJobs = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
  const otherJobs = jobs.filter(j => j.status !== 'processing' && j.status !== 'pending');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Очередь задач</h1>
          <p className="text-slate-500 mt-1">Всего: {total} задач</p>
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

      {/* Filters */}
      <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Статус</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Все</option>
            <option value="completed">Готово</option>
            <option value="failed">Ошибка</option>
            <option value="processing">Обработка</option>
            <option value="pending">В очереди</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Домен</label>
          <select
            value={filterDomain}
            onChange={(e) => setFilterDomain(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Все</option>
            <option value="construction">Construction</option>
            <option value="ceo">CEO</option>
            <option value="dct">DCT</option>
            <option value="hr">HR</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Email пользователя</label>
          <input
            value={filterEmail}
            onChange={(e) => setFilterEmail(e.target.value)}
            placeholder="Поиск..."
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm w-48"
          />
        </div>
        {(filterStatus || filterDomain || filterEmail) && (
          <button
            onClick={() => { setFilterStatus(''); setFilterDomain(''); setFilterEmail(''); }}
            className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700"
          >
            Сбросить
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">{error}</div>
      )}

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2">
            <span className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
            <h2 className="text-lg font-semibold text-slate-800">
              Активные задачи ({activeJobs.length})
            </h2>
          </div>
          <div className="divide-y divide-slate-100">
            {activeJobs.map((job) => (
              <div key={job.job_id} className="px-6 py-4 flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[job.status]}`}>
                      {STATUS_LABELS[job.status]}
                    </span>
                    <span className="text-slate-800 font-medium truncate">{job.source_file}</span>
                    {job.domain && (
                      <span className="px-1.5 py-0.5 text-xs bg-slate-100 text-slate-500 rounded">{job.domain}</span>
                    )}
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-sm text-slate-500">
                    <span>{formatDate(job.created_at)}</span>
                    {job.uploader_email && <span>{job.uploader_email}</span>}
                  </div>
                  {job.status === 'processing' && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-slate-500">{job.current_stage || 'Обработка'}</span>
                        <span className="text-slate-800 font-medium">{job.progress_percent}%</span>
                      </div>
                      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div className="h-full bg-severin-red transition-all duration-500" style={{ width: `${job.progress_percent}%` }} />
                      </div>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleCancel(job.job_id)}
                  disabled={cancelling === job.job_id}
                  className="ml-4 px-3 py-2 bg-red-500 hover:bg-red-600 disabled:bg-slate-300 text-white text-sm rounded-lg transition"
                >
                  {cancelling === job.job_id ? '...' : 'Остановить'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Jobs Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">
            Задачи
            <span className="text-sm text-slate-500 ml-2">({total})</span>
          </h2>
        </div>

        {otherJobs.length === 0 && !loading ? (
          <div className="px-6 py-8 text-center text-slate-400">Нет задач</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Файл</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Статус</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Домен</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Пользователь</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Дата</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Время</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Отчёт</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {otherJobs.map((job) => {
                  const hasArtifacts = job.artifacts && Object.keys(job.artifacts).length > 0;
                  return (
                    <tr key={job.job_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <span className="text-slate-800 text-sm truncate max-w-xs block">{job.source_file}</span>
                        <span className="text-slate-400 text-xs">{job.job_id.slice(0, 8)}...</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[job.status] || ''}`}>
                          {STATUS_LABELS[job.status] || job.status}
                        </span>
                        {job.error && (
                          <p className="text-red-500 text-xs mt-1 truncate max-w-xs" title={job.error}>{job.error}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-sm">{job.domain || '—'}</td>
                      <td className="px-4 py-3 text-slate-600 text-sm">{job.uploader_email || '—'}</td>
                      <td className="px-4 py-3 text-slate-500 text-sm whitespace-nowrap">{formatDate(job.created_at)}</td>
                      <td className="px-4 py-3 text-slate-500 text-sm">{formatDuration(job.processing_time_seconds)}</td>
                      <td className="px-4 py-3 text-center">
                        {hasArtifacts ? (
                          <button
                            onClick={() => handleOpenReport(job.job_id, job.artifacts)}
                            className="px-3 py-1 text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg transition"
                          >
                            Просмотр
                          </button>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handlePurge(job.job_id, job.source_file)}
                          disabled={deleting === job.job_id}
                          className="px-2 py-1 text-xs text-red-600 hover:text-white hover:bg-red-500 border border-red-300 hover:border-red-500 rounded transition disabled:opacity-50"
                          title="Удалить задачу и все файлы"
                        >
                          {deleting === job.job_id ? '...' : 'Удалить'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-slate-200 flex items-center justify-between">
            <span className="text-sm text-slate-500">
              Страница {page} из {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-30"
              >
                Назад
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 text-sm border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-30"
              >
                Далее
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Report Modal */}
      <ReportModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); }}
        jobId={modalJobId}
        artifacts={modalArtifacts}
        report={modalReport}
        loading={modalLoading}
        error={modalError}
      />

      {ConfirmDialog}
    </div>
  );
}
