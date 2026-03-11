import { useRef, useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  X,
  Download,
  FileDown,
  AlertTriangle,
} from 'lucide-react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import {
  getJobResult,
  downloadJobFile,
  downloadJobFileAll,
  type JobListItem,
  type JobResultResponse,
  type MeetingReport,
} from '../../api/client';
import { FILE_TYPE_CONFIG } from './constants';

interface CEODetailModalProps {
  job: JobListItem;
  onClose: () => void;
}

type SectionId = 'summary' | `topic-${number}` | 'tasks';

export function CEODetailModal({ job, onClose }: CEODetailModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeSection, setActiveSection] = useState<SectionId>('summary');
  useFocusTrap(modalRef);

  const { data: jobResult, isLoading } = useQuery<JobResultResponse>({
    queryKey: ['job-result', job.job_id],
    queryFn: () => getJobResult(job.job_id),
    enabled: job.status === 'completed',
    retry: false,
  });

  const outputFiles = jobResult?.output_files || {};
  const fileTypes = Object.keys(outputFiles);
  const report = jobResult?.meeting_report as MeetingReport | undefined;

  const meetingDate = report?.meeting_date
    ? new Date(report.meeting_date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
    : new Date(job.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });

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
  if (report?.executive_summary) {
    tocItems.push({ id: 'summary', label: 'Резюме' });
  }
  if (report?.topics) {
    report.topics.forEach((topic, idx) => {
      tocItems.push({
        id: `topic-${idx}`,
        label: topic.title.length > 40 ? topic.title.slice(0, 40) + '...' : topic.title,
      });
    });
  }
  if (report?.tasks && report.tasks.length > 0) {
    tocItems.push({ id: 'tasks', label: 'Поручения' });
  }

  const priorityDot = (priority?: string) => {
    if (priority === 'high') return 'bg-red-500';
    if (priority === 'medium') return 'bg-amber-400';
    return 'bg-slate-300';
  };

  const priorityLabel = (priority?: string) => {
    if (priority === 'high') return 'Высокий';
    if (priority === 'medium') return 'Средний';
    return 'Низкий';
  };

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
          <p className="text-slate-400 font-serif">Идёт обработка...</p>
        </div>
      );
    }
    if (job.status === 'failed') {
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <AlertTriangle className="w-8 h-8 text-red-400 mb-3" />
          <p className="text-red-500 font-serif">Ошибка обработки. Попробуйте загрузить файл повторно.</p>
        </div>
      );
    }
    if (job.status === 'completed' && !report && fileTypes.length === 0) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-slate-400 font-serif">Данные отчёта недоступны</p>
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
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Протокол</p>
            <h2 className="text-lg font-bold text-slate-900 leading-snug">
              {report?.meeting_topic || report?.meeting_type || job.meeting_type_name || 'НОТЕХ'}
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
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
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
        <main className="flex-1 bg-white relative flex flex-col">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-5 right-5 z-10 p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors cursor-pointer"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Mobile header (visible on small screens) */}
          <div className="md:hidden px-6 pt-5 pb-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900">{report?.meeting_type || job.meeting_type_name || 'НОТЕХ'}</p>
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
              <div className="max-w-3xl mx-auto px-8 sm:px-12 py-16">

                {/* Meeting Topic & Attendees */}
                {report?.meeting_topic && (
                  <div className="mb-8">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Тема совещания</p>
                    <h1 className="font-extrabold text-2xl text-slate-900">{report.meeting_topic}</h1>
                  </div>
                )}

                {report?.attendees && report.attendees.length > 0 && (
                  <div className="mb-12">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Участники</p>
                    <div className="flex flex-wrap gap-2">
                      {report.attendees.map((name, idx) => (
                        <span key={idx} className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-slate-100 text-slate-700">
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Executive Summary */}
                {report?.executive_summary && (
                  <section data-section="summary" className="mb-16">
                    <h1 className="font-extrabold text-3xl text-slate-900 mb-6">Резюме</h1>
                    <p className="font-serif text-lg text-slate-700 leading-relaxed whitespace-pre-line">
                      {report.executive_summary}
                    </p>
                  </section>
                )}

                {/* Topics */}
                {report?.topics && report.topics.length > 0 && (
                  <section className="mb-16">
                    <h1 className="font-extrabold text-3xl text-slate-900 mb-10">Повестка</h1>
                    <div className="space-y-12">
                      {report.topics.map((topic, idx) => (
                        <article key={topic.id ?? idx} data-section={`topic-${idx}`}>
                          {/* Topic header */}
                          <div className="flex items-baseline gap-4 mb-4">
                            <span className="text-4xl font-extrabold text-slate-200">
                              {String(idx + 1).padStart(2, '0')}
                            </span>
                            <h2 className="text-xl font-bold text-slate-900 leading-snug">
                              {topic.title}
                            </h2>
                          </div>

                          {topic.timecodes && topic.timecodes.length > 0 && (
                            <p className="text-xs text-slate-400 mb-4 ml-14">
                              {topic.timecodes.join(' \u2022 ')}
                            </p>
                          )}

                          {/* Problem / essence */}
                          {topic.problem && (
                            <p className="font-serif text-lg text-slate-600 leading-relaxed mb-6 ml-14">
                              {topic.problem}
                            </p>
                          )}

                          {/* Value points */}
                          {topic.value_points && topic.value_points.length > 0 && (
                            <div className="bg-emerald-50 border-l-4 border-emerald-400 rounded-r-lg px-6 py-4 mb-6 ml-14">
                              <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider mb-2">
                                Ценность
                              </p>
                              <ul className="space-y-1.5">
                                {topic.value_points.map((vp, vpIdx) => (
                                  <li key={vpIdx} className="text-emerald-900 text-sm flex items-start gap-2">
                                    <span className="text-emerald-400 mt-0.5 flex-shrink-0">•</span>
                                    {vp}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Discussion details */}
                          {topic.discussion_details && topic.discussion_details.length > 0 && (
                            <div className="bg-blue-50 border-l-4 border-blue-400 rounded-r-lg px-6 py-4 mb-6 ml-14">
                              <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-2">
                                Детали обсуждения
                              </p>
                              <ul className="space-y-1.5">
                                {topic.discussion_details.map((dd, ddIdx) => (
                                  <li key={ddIdx} className="text-blue-900 text-sm flex items-start gap-2">
                                    <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
                                    {dd}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Decision */}
                          {topic.decision && (
                            <div className="bg-purple-50 border-l-4 border-purple-500 rounded-r-lg px-6 py-4 mb-6 ml-14">
                              <p className="text-xs font-semibold text-purple-600 uppercase tracking-wider mb-1">
                                Решение
                              </p>
                              <p className="text-slate-800 leading-relaxed">
                                {topic.decision}
                              </p>
                            </div>
                          )}

                          {/* Risks */}
                          {topic.risks && topic.risks.length > 0 && (
                            <div className="bg-orange-50 border border-orange-100 rounded-lg px-6 py-4 ml-14">
                              <p className="text-xs font-semibold text-orange-600 uppercase tracking-wider mb-2">
                                Риски
                              </p>
                              <ul className="space-y-1.5">
                                {topic.risks.map((risk, rIdx) => (
                                  <li key={rIdx} className="text-orange-900 text-sm flex items-start gap-2">
                                    <AlertTriangle className="w-3.5 h-3.5 text-orange-400 mt-0.5 flex-shrink-0" />
                                    {risk}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  </section>
                )}

                {/* Tasks */}
                {report?.tasks && report.tasks.length > 0 && (
                  <section data-section="tasks" className="mb-16">
                    <h1 className="font-extrabold text-3xl text-slate-900 mb-8">Поручения</h1>
                    <ul className="space-y-4">
                      {report.tasks.map((task, tIdx) => (
                        <li key={tIdx} className="flex items-start gap-3">
                          <span
                            className={`w-2.5 h-2.5 rounded-full mt-2 flex-shrink-0 ${priorityDot(task.priority)}`}
                            title={priorityLabel(task.priority)}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-slate-800 leading-relaxed">{task.description}</p>
                            <div className="flex items-center gap-3 mt-1">
                              {task.responsible && (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                                  @{task.responsible}
                                </span>
                              )}
                              {task.priority && (
                                <span className={`text-xs ${
                                  task.priority === 'high' ? 'text-red-500' :
                                  task.priority === 'medium' ? 'text-amber-500' :
                                  'text-slate-400'
                                }`}>
                                  {priorityLabel(task.priority)}
                                </span>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* Documents (inline for mobile, since sidebar is hidden) */}
                <div className="md:hidden">
                  {fileTypes.length > 0 && (
                    <section className="border-t border-slate-100 pt-8">
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
