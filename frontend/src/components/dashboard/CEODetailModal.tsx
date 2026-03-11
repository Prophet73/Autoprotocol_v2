import { useRef, useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  X,
  Download,
  FileDown,
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  Building2,
  AlignLeft,
  Users,
  CheckSquare,
} from 'lucide-react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import {
  getJobResult,
  downloadJobFile,
  downloadJobFileAll,
  type JobListItem,
  type JobResultResponse,
  type DomainReportJSON,
  type NotechQuestion,
} from '../../api/client';
import { FILE_TYPE_CONFIG } from './constants';

interface CEODetailModalProps {
  job: JobListItem;
  onClose: () => void;
}

type SectionId = 'summary' | `topic-${number}` | 'tasks';

/* ── Decision status inference ── */
function getDecisionStatus(q: NotechQuestion): 'resolved' | 'conflict' | 'unresolved' {
  if (!q.decision) return 'conflict';
  const lower = q.decision.toLowerCase();
  if (
    lower.includes('не найдено') ||
    lower.includes('не принято') ||
    lower.includes('не достигнут')
  ) {
    return 'conflict';
  }
  return 'resolved';
}

const DECISION_CONFIG = {
  resolved: {
    bg: 'bg-green-50',
    border: 'border-l-green-500',
    titleColor: 'text-green-600',
    label: 'Принятое решение',
    Icon: CheckCircle2,
  },
  unresolved: {
    bg: 'bg-yellow-50',
    border: 'border-l-yellow-500',
    titleColor: 'text-yellow-600',
    label: 'Требует решения',
    Icon: CircleAlert,
  },
  conflict: {
    bg: 'bg-red-50',
    border: 'border-l-red-500',
    titleColor: 'text-red-600',
    label: 'Решение не найдено',
    Icon: CircleAlert,
  },
} as const;

/* ── Highlight dates like "до 15.01.2026" in action items ── */
function renderActionText(text: string) {
  const parts = text.split(/(до \d{1,2}\.\d{2}\.\d{4})/gi);
  return parts.map((part, i) =>
    /до \d{1,2}\.\d{2}\.\d{4}/i.test(part) ? (
      <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-xs font-semibold whitespace-nowrap ml-1">
        {part}
      </span>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function CEODetailModal({ job, onClose }: CEODetailModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeSection, setActiveSection] = useState<SectionId>('summary');
  useFocusTrap(modalRef);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const { data: jobResult, isLoading } = useQuery<JobResultResponse>({
    queryKey: ['job-result', job.job_id],
    queryFn: () => getJobResult(job.job_id),
    enabled: job.status === 'completed',
    retry: false,
  });

  const outputFiles = jobResult?.output_files || {};
  const fileTypes = Object.keys(outputFiles);
  const report = jobResult?.meeting_report as DomainReportJSON | undefined;
  const questions = report?.questions || [];
  const actionItems = report?.action_items || [];

  const meetingDate = new Date(job.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });

  // Scroll spy
  const handleScroll = useCallback(() => {
    const container = scrollRef.current;
    if (!container) return;

    const sections = container.querySelectorAll<HTMLElement>('[data-section]');
    let current: SectionId = 'summary';

    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      if (rect.top - containerRect.top <= 120) {
        current = section.dataset.section as SectionId;
      }
    }
    setActiveSection(current);
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollToSection = (id: SectionId) => {
    const container = scrollRef.current;
    if (!container) return;
    const el = container.querySelector(`[data-section="${id}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Build ToC items
  const tocItems: { id: SectionId; label: string }[] = [];
  if (report?.summary) {
    tocItems.push({ id: 'summary', label: 'Резюме' });
  }
  if (questions.length > 0) {
    questions.forEach((q, idx) => {
      tocItems.push({
        id: `topic-${idx}`,
        label: q.title || `Вопрос ${idx + 1}`,
      });
    });
  }
  if (actionItems.length > 0) {
    tocItems.push({ id: 'tasks', label: 'Поручения и задачи' });
  }

  // Non-report states (loading, processing, failed, empty)
  const renderCenteredState = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 text-slate-300 animate-spin" />
        </div>
      );
    }
    if (job.status === 'processing') {
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <Loader2 className="w-8 h-8 text-slate-300 animate-spin mb-3" />
          <p className="text-slate-400">Идёт обработка...</p>
        </div>
      );
    }
    if (job.status === 'failed') {
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <AlertTriangle className="w-8 h-8 text-red-400 mb-3" />
          <p className="text-red-500">Ошибка обработки. Попробуйте загрузить файл повторно.</p>
        </div>
      );
    }
    if (job.status === 'completed' && !report && fileTypes.length === 0 && !isLoading) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-slate-400">Данные отчёта недоступны</p>
        </div>
      );
    }
    return null;
  };

  const centeredState = renderCenteredState();
  const hasReport = report && !centeredState;

  return (
    <div className="fixed inset-0 z-50 flex bg-black/40">
      <div ref={modalRef} className="flex w-full h-full">

        {/* Left Sidebar */}
        <aside className="hidden md:flex flex-col w-80 bg-slate-50 border-r border-slate-200 flex-shrink-0">
          {/* Document info */}
          <div className="px-6 pt-8 pb-4">
            <div className="inline-flex items-center gap-1.5 bg-purple-100 text-purple-800 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide mb-3">
              <Building2 className="w-3.5 h-3.5" />
              CEO / Протокол НОТЕХ
            </div>
            <h2 className="text-lg font-bold text-slate-900 leading-snug">
              {report?.meeting_topic || job.meeting_type_name || 'НОТЕХ'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">{meetingDate}</p>
            <p className="text-xs text-slate-400 mt-1 truncate" title={job.source_file}>
              {job.source_file}
            </p>
          </div>

          {/* Table of Contents */}
          {hasReport && tocItems.length > 0 && (
            <nav className="flex-1 overflow-y-auto px-3 py-2">
              <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">
                Содержание
              </p>
              <ul className="space-y-0.5">
                {tocItems.map((item) => (
                  <li key={item.id}>
                    <button
                      onClick={() => scrollToSection(item.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm leading-snug transition-colors cursor-pointer ${
                        activeSection === item.id
                          ? 'bg-white text-slate-900 font-medium shadow-sm'
                          : 'text-slate-500 hover:text-slate-700 hover:bg-white/60'
                      }`}
                    >
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          )}

          {/* Download buttons */}
          {fileTypes.length > 0 && (
            <div className="px-4 pb-6 pt-2 space-y-2 border-t border-slate-200 mt-auto">
              {fileTypes.includes('report') && (
                <button
                  onClick={() => downloadJobFile(job.job_id, 'report')}
                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <FileDown className="w-4 h-4 text-slate-400" />
                  Скачать DOCX
                </button>
              )}
              <button
                onClick={() => downloadJobFileAll(job.job_id)}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <Download className="w-4 h-4 text-slate-400" />
                Скачать всё (ZIP)
              </button>
            </div>
          )}
        </aside>

        {/* Right Main Area */}
        <main className="flex-1 bg-slate-50 relative flex flex-col">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-10 flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-500 hover:text-slate-800 hover:border-slate-300 hover:shadow-sm rounded-lg transition-all cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-4 h-4" />
            <span className="text-sm font-medium hidden sm:inline">Закрыть</span>
          </button>

          {/* Mobile header */}
          <div className="md:hidden px-6 pt-5 pb-3 border-b border-slate-200 bg-white flex items-center justify-between">
            <div>
              <div className="inline-flex items-center gap-1.5 bg-purple-100 text-purple-800 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide mb-1">
                <Building2 className="w-3 h-3" />
                CEO / НОТЕХ
              </div>
              <p className="font-semibold text-slate-900">{report?.meeting_topic || job.meeting_type_name || 'НОТЕХ'}</p>
              <p className="text-xs text-slate-400">{meetingDate}</p>
            </div>
            {fileTypes.length > 0 && (
              <button
                onClick={() => downloadJobFileAll(job.job_id)}
                className="p-2 text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <Download className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Scrollable content */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            {centeredState ? (
              centeredState
            ) : (
              <div className="max-w-4xl mx-auto px-6 sm:px-10 py-10">

                {/* ─── Header ─── */}
                {report?.meeting_topic && (
                  <header className="mb-8">
                    <h1 className="text-2xl font-extrabold text-slate-900 leading-tight">
                      {report.meeting_topic}
                    </h1>
                    <p className="text-sm text-slate-500 mt-2">
                      Дата: <span className="font-semibold text-slate-700">{meetingDate}</span>
                    </p>
                  </header>
                )}

                {/* ─── Summary & Attendees Card ─── */}
                {(report?.summary || (report?.attendees && report.attendees.length > 0)) && (
                  <div
                    data-section="summary"
                    className="bg-white rounded-2xl border border-slate-200 shadow-sm mb-8 overflow-hidden"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-200">
                      {/* Summary */}
                      {report?.summary && (
                        <div className="p-6">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                            <AlignLeft className="w-4 h-4" />
                            Краткое саммари
                          </div>
                          <p className="text-base text-slate-700 leading-relaxed whitespace-pre-line">
                            {report.summary}
                          </p>
                        </div>
                      )}

                      {/* Attendees */}
                      {report?.attendees && report.attendees.length > 0 && (
                        <div className="p-6">
                          <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                            <Users className="w-4 h-4" />
                            Участники
                          </div>
                          <div className="flex flex-col gap-2">
                            {report.attendees.map((name, idx) => (
                              <div
                                key={idx}
                                className="bg-slate-50 text-slate-600 px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-200"
                              >
                                {name}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* ─── Questions ─── */}
                {questions.length > 0 && (
                  <section className="mb-10">
                    <h2 className="text-xl font-bold text-slate-900 mb-5">Вопросы повестки</h2>

                    <div className="space-y-6">
                      {questions.map((q, idx) => {
                        const status = getDecisionStatus(q);
                        const cfg = DECISION_CONFIG[status];
                        const isConflict = status === 'conflict';

                        return (
                          <div
                            key={idx}
                            data-section={`topic-${idx}`}
                            className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
                          >
                            {/* Question header */}
                            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-start gap-4">
                              <div
                                className={`w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-base flex-shrink-0 mt-0.5 ${
                                  isConflict ? 'bg-red-500' : 'bg-purple-700'
                                }`}
                              >
                                {idx + 1}
                              </div>
                              <h3 className="text-lg font-bold text-slate-900 leading-snug">
                                {q.title}
                              </h3>
                            </div>

                            {/* Question body */}
                            <div className="p-6">
                              {/* Description */}
                              {q.description && (
                                <p className="text-sm text-slate-500 leading-relaxed mb-5">
                                  {q.description}
                                </p>
                              )}

                              {/* Decision box */}
                              {q.decision && (
                                <div
                                  className={`p-4 rounded-xl border-l-4 mb-6 ${cfg.bg} ${cfg.border}`}
                                >
                                  <div className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-1.5 ${cfg.titleColor}`}>
                                    <cfg.Icon className="w-4 h-4" />
                                    {cfg.label}
                                  </div>
                                  <p className="text-sm font-semibold text-slate-800 leading-relaxed">
                                    {q.decision}
                                  </p>
                                </div>
                              )}

                              {/* Two-column grid: left = value + details, right = risks */}
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div>
                                  {/* Value points */}
                                  {q.value_points && q.value_points.length > 0 && (
                                    <div className="mb-5">
                                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                        Ценность решения
                                      </p>
                                      <ul className="space-y-1.5">
                                        {q.value_points.map((vp, vpIdx) => (
                                          <li key={vpIdx} className="text-sm text-slate-500 flex items-start gap-2">
                                            <span className="text-purple-500 font-bold mt-px flex-shrink-0">&bull;</span>
                                            {vp}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {/* Discussion details */}
                                  {q.discussion_details && q.discussion_details.length > 0 && (
                                    <div>
                                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                        Детали обсуждения
                                      </p>
                                      <ul className="space-y-1.5">
                                        {q.discussion_details.map((dd, ddIdx) => (
                                          <li key={ddIdx} className="text-sm text-slate-500 flex items-start gap-2">
                                            <span className="text-purple-500 font-bold mt-px flex-shrink-0">&bull;</span>
                                            {dd}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>

                                {/* Risks */}
                                {q.risks && q.risks.length > 0 && (
                                  <div className="bg-slate-50 border border-red-200 rounded-xl p-4">
                                    <p className="text-xs font-bold text-red-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                      <AlertTriangle className="w-3.5 h-3.5" />
                                      Риски и возражения
                                    </p>
                                    <ul className="space-y-1.5">
                                      {q.risks.map((risk, rIdx) => (
                                        <li key={rIdx} className="text-sm text-slate-500 flex items-start gap-2">
                                          <span className="text-red-400 font-bold mt-px flex-shrink-0">&bull;</span>
                                          {risk}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}

                {/* ─── Action Items ─── */}
                {actionItems.length > 0 && (
                  <section data-section="tasks" className="mb-10">
                    <h2 className="text-xl font-bold text-slate-900 mb-5">Поручения и задачи по итогам</h2>

                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-200">
                      {actionItems.map((item, tIdx) => (
                        <div
                          key={tIdx}
                          className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50 transition-colors"
                        >
                          <div className="w-6 h-6 rounded-md bg-purple-100 text-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <CheckSquare className="w-3.5 h-3.5" />
                          </div>
                          <p className="text-sm text-slate-700 leading-relaxed flex-1">
                            {renderActionText(item)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Documents (mobile only) */}
                <div className="md:hidden">
                  {fileTypes.length > 0 && (
                    <section className="border-t border-slate-200 pt-8">
                      <h2 className="text-lg font-bold text-slate-900 mb-4">Документы</h2>
                      <div className="flex flex-wrap gap-2">
                        {fileTypes.map((fileType) => {
                          const config = FILE_TYPE_CONFIG[fileType];
                          const label = config?.label || fileType;
                          return (
                            <button
                              key={fileType}
                              onClick={() => downloadJobFile(job.job_id, fileType)}
                              className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors text-sm text-slate-700 cursor-pointer"
                            >
                              <Download className="w-3.5 h-3.5 text-slate-400" />
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </section>
                  )}
                </div>

              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
