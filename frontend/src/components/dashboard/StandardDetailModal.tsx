import { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  Loader2,
  ChevronLeft,
  Download,
  Clock,
  Archive,
} from 'lucide-react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import {
  getJobResult,
  downloadJobFile,
  downloadJobFileAll,
  type JobListItem,
  type JobResultResponse,
} from '../../api/client';
import { STATUS_LABELS, FILE_TYPE_CONFIG, ACCENT_COLOR_MAP, type AccentColor } from './constants';

interface StandardDetailModalProps {
  job: JobListItem;
  onClose: () => void;
  accentColor: AccentColor;
}

function formatTime(seconds: number) {
  if (seconds < 60) return `${Math.round(seconds)} сек`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins} мин ${secs} сек`;
}

export function StandardDetailModal({ job, onClose, accentColor }: StandardDetailModalProps) {
  const colors = ACCENT_COLOR_MAP[accentColor];
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef);

  const { data: jobResult, isLoading } = useQuery<JobResultResponse>({
    queryKey: ['job-result', job.job_id],
    queryFn: () => getJobResult(job.job_id),
    enabled: job.status === 'completed',
    retry: false,
  });

  const outputFiles = jobResult?.output_files || {};
  const fileTypes = Object.keys(outputFiles);

  return (
    <div className="fixed inset-0 bg-black/50 z-50">
      <div ref={modalRef} className="h-full flex flex-col bg-slate-100">
        <div className="px-6 py-3 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 rounded-lg transition-colors shadow-sm"
            >
              <ChevronLeft className="w-5 h-5" />
              <span className="font-medium">Назад к календарю</span>
            </button>
            <div className="h-6 w-px bg-slate-200" />
            <h2 className="text-lg font-semibold text-slate-800">Сводка по совещанию</h2>
            <span className="text-sm text-slate-500 truncate max-w-md">{job.source_file}</span>
            <span className={`px-2.5 py-0.5 rounded text-sm font-medium ${
              job.status === 'completed' ? 'bg-green-100 text-green-800' :
              job.status === 'processing' ? 'bg-amber-100 text-amber-800' :
              job.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-slate-100 text-slate-700'
            }`}>
              {STATUS_LABELS[job.status] || job.status}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {fileTypes.length > 1 && (
              <button
                onClick={() => downloadJobFileAll(job.job_id)}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
              >
                <Archive className="w-4 h-4" />
                Скачать всё (ZIP)
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              <section className="bg-white rounded-lg border border-slate-200 p-6">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                  Информация о записи
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {job.meeting_type_name && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Тип встречи</p>
                      <p className="text-sm font-medium text-slate-800">{job.meeting_type_name}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Дата загрузки</p>
                    <p className="text-sm font-medium text-slate-800">
                      {new Date(job.created_at).toLocaleString('ru-RU')}
                    </p>
                  </div>
                  {jobResult?.processing_time_seconds ? (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Время обработки</p>
                      <p className="text-sm font-medium text-slate-800 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {formatTime(jobResult.processing_time_seconds)}
                      </p>
                    </div>
                  ) : null}
                  {jobResult?.language_distribution && Object.keys(jobResult.language_distribution).length > 0 ? (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Языки</p>
                      <div className="flex gap-1.5 flex-wrap">
                        {(() => {
                          const entries = Object.entries(jobResult.language_distribution);
                          const total = entries.reduce((sum, [, count]) => sum + count, 0);
                          return entries.map(([lang, count]) => (
                            <span key={lang} className="px-2 py-0.5 bg-slate-100 text-slate-700 text-xs rounded">
                              {lang.toUpperCase()} {total > 0 ? `${Math.round((count / total) * 100)}%` : ''}
                            </span>
                          ));
                        })()}
                      </div>
                    </div>
                  ) : null}
                </div>
              </section>

              {fileTypes.length > 0 && (
                <section className="bg-white rounded-lg border border-slate-200 p-6">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                    Документы
                    <span className="ml-2 font-normal">({fileTypes.length})</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {fileTypes.map((fileType) => {
                      const config = FILE_TYPE_CONFIG[fileType];
                      const Icon = config?.icon || FileText;
                      const label = config?.label || fileType;
                      const description = config?.description ?? '';
                      return (
                        <button
                          key={fileType}
                          onClick={() => downloadJobFile(job.job_id, fileType)}
                          className={`flex items-center gap-4 p-4 border border-slate-200 rounded-lg ${colors.hoverBorder} ${colors.hoverBg} transition-all text-left cursor-pointer group`}
                        >
                          <div className={`w-10 h-10 ${colors.iconBg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                            <Icon className={`w-5 h-5 ${colors.iconText}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800">{label}</p>
                            {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
                          </div>
                          <Download className={`w-4 h-4 text-slate-400 ${colors.groupHoverText} flex-shrink-0`} />
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}

              {job.status === 'completed' && !isLoading && fileTypes.length === 0 && (
                <section className="bg-white rounded-lg border border-slate-200 p-12 text-center">
                  <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-8 h-8 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-medium text-slate-700 mb-2">Документы недоступны</h3>
                  <p className="text-slate-500 max-w-md mx-auto">
                    Файлы отчётов не найдены. Возможно, задача была обработана без генерации документов.
                  </p>
                </section>
              )}

              {job.status === 'processing' && (
                <section className="bg-white rounded-lg border border-slate-200 p-12 text-center">
                  <Loader2 className={`w-12 h-12 ${colors.processingSpinner} animate-spin mx-auto mb-4`} />
                  <h3 className="text-lg font-medium text-slate-700 mb-2">Идёт обработка</h3>
                  <p className="text-slate-500 max-w-md mx-auto">
                    Запись обрабатывается. Документы будут доступны после завершения.
                  </p>
                </section>
              )}

              {job.status === 'failed' && (
                <section className="bg-red-50 rounded-lg border border-red-200 p-12 text-center">
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-8 h-8 text-red-400" />
                  </div>
                  <h3 className="text-lg font-medium text-red-700 mb-2">Ошибка обработки</h3>
                  <p className="text-red-600 max-w-md mx-auto">
                    При обработке записи произошла ошибка. Попробуйте загрузить файл повторно.
                  </p>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
