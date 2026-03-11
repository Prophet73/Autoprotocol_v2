import { useState } from 'react';
import {
  ChevronLeft,
  Download,
  FileText,
  Loader2,
} from 'lucide-react';
import {
  downloadAnalyticsReport,
  type AnalyticsDetail,
} from '../../api/client';
import { type SectionId, statusLabels, atmosphereLabels, atmosphereColors } from './constants';
import { RiskCard } from './RiskCard';
import { TasksTable } from './TasksTable';

export function AnalyticsModal({
  analyticsId,
  detail,
  isLoading,
  onClose,
  canSeeFullRiskBrief = true,
}: {
  analyticsId: number;
  detail?: AnalyticsDetail;
  isLoading: boolean;
  onClose: () => void;
  canSeeFullRiskBrief?: boolean;
}) {
  const [activeSection, setActiveSection] = useState<SectionId>('summary');
  const riskBrief = detail?.risk_brief_json;
  const basicReport = detail?.basic_report_json;
  const hasRiskBriefData = riskBrief && riskBrief.risks && riskBrief.risks.length > 0;
  const hasTasks = basicReport?.tasks && basicReport.tasks.length > 0;

  // Viewer sees limited data (no risks, no atmosphere, no risk_brief download)
  const showRisks = canSeeFullRiskBrief && hasRiskBriefData;
  const showAtmosphere = canSeeFullRiskBrief && riskBrief?.atmosphere;

  // Check for participants
  const hasParticipants = detail?.participants && detail.participants.length > 0;

  // Build sections list
  const sections: Array<{ id: SectionId; label: string; count?: number; show: boolean }> = [
    { id: 'participants', label: 'Участники', count: detail?.participants?.reduce((acc, g) => acc + g.persons.length, 0), show: !!hasParticipants },
    { id: 'summary', label: 'О совещании', show: !!riskBrief?.executive_summary },
    { id: 'atmosphere', label: 'Атмосфера', show: !!showAtmosphere },
    { id: 'concerns', label: 'Незакрытые вопросы', count: riskBrief?.concerns?.length, show: !!(riskBrief?.concerns && riskBrief.concerns.length > 0) },
    { id: 'risks', label: 'Риски', count: riskBrief?.risks?.length, show: !!showRisks },
    { id: 'tasks', label: 'Задачи', count: basicReport?.tasks?.length, show: !!hasTasks },
  ];

  const visibleSections = sections.filter(s => s.show);

  // Status badge - muted colors
  const getStatusBadge = (status: string) => {
    if (status === 'critical') return 'bg-red-100 text-red-800';
    if (status === 'attention') return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-800';
  };

  const scrollToSection = (sectionId: SectionId) => {
    setActiveSection(sectionId);
    const el = document.getElementById(`section-${sectionId}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 animate-in fade-in duration-200">
      <div className="h-full flex flex-col bg-slate-100">
        {/* Header */}
        <div className="px-6 py-3 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            {/* Back button - prominent and easy to find */}
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 rounded-lg transition-colors shadow-sm"
            >
              <ChevronLeft className="w-5 h-5" />
              <span className="font-medium">Назад к календарю</span>
            </button>
            <div className="h-6 w-px bg-slate-200" />
            <h2 className="text-lg font-semibold text-slate-800">Сводка по совещанию</h2>
            {detail?.filename && (
              <span className="text-sm text-slate-500">• {detail.filename}</span>
            )}
            {riskBrief?.overall_status && (
              <span className={`px-2.5 py-0.5 rounded text-sm font-medium ${getStatusBadge(riskBrief.overall_status)}`}>
                {statusLabels[riskBrief.overall_status] || riskBrief.overall_status}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Download buttons with clear labels */}
            {detail?.has_risk_brief && canSeeFullRiskBrief && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
                title="Скачать риск-бриф в формате PDF"
              >
                <Download className="w-4 h-4" />
                Риск-бриф (PDF)
              </button>
            )}
            {detail?.has_tasks && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'tasks')}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
                title="Скачать список задач в формате Excel"
              >
                <Download className="w-4 h-4" />
                Задачи (XLSX)
              </button>
            )}
            {detail?.has_summary && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'summary')}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
                title="Скачать конспект совещания"
              >
                <Download className="w-4 h-4" />
                Конспект (DOCX)
              </button>
            )}
          </div>
        </div>

        {/* Main content with sidebar */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar navigation */}
          {visibleSections.length > 1 && (
            <div className="w-56 bg-white border-r border-slate-200 flex-shrink-0 py-4">
              <nav className="space-y-1 px-3">
                {visibleSections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between ${
                      activeSection === section.id
                        ? 'bg-slate-100 text-slate-900 font-medium'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <span>{section.label}</span>
                    {section.count !== undefined && (
                      <span className="text-xs text-slate-400">{section.count}</span>
                    )}
                  </button>
                ))}
              </nav>
            </div>
          )}

          {/* Content area */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
              </div>
            ) : (hasRiskBriefData || hasTasks || riskBrief || hasParticipants) ? (
              <div className="space-y-6">

                {/* Участники совещания */}
                {hasParticipants && (
                  <section id="section-participants" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Участники совещания
                      <span className="ml-2 font-normal">
                        ({detail!.participants!.reduce((acc, g) => acc + g.persons.length, 0)})
                      </span>
                    </h3>
                    <div className="space-y-4">
                      {detail!.participants!.map((group, idx) => (
                        <div key={idx}>
                          <p className="text-sm font-medium text-slate-600 mb-1">{group.org_name}</p>
                          <div className="flex flex-wrap gap-2">
                            {group.persons.map((person, pIdx) => (
                              <span key={pIdx} className="px-2 py-1 bg-slate-100 text-slate-700 text-sm rounded">
                                {person}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* О совещании */}
                {riskBrief?.executive_summary && (
                  <section id="section-summary" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      О совещании
                    </h3>
                    <p className="text-slate-700 leading-relaxed text-[15px]">
                      {riskBrief.executive_summary}
                    </p>
                  </section>
                )}

                {/* Атмосфера */}
                {showAtmosphere && (
                  <section id="section-atmosphere" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Атмосфера
                    </h3>
                    <div className="flex items-baseline gap-3">
                      <span className={`text-xl font-semibold ${atmosphereColors[riskBrief!.atmosphere] || 'text-slate-700'}`}>
                        {atmosphereLabels[riskBrief!.atmosphere] || riskBrief!.atmosphere}
                      </span>
                      {riskBrief!.atmosphere_comment && (
                        <span className="text-slate-500">— {riskBrief!.atmosphere_comment}</span>
                      )}
                    </div>
                  </section>
                )}

                {/* Незакрытые вопросы */}
                {riskBrief?.concerns && riskBrief.concerns.length > 0 && (
                  <section id="section-concerns" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Незакрытые вопросы
                      <span className="ml-2 font-normal">({riskBrief.concerns.length})</span>
                    </h3>
                    <ul className="space-y-3">
                      {riskBrief.concerns.map((concern, idx) => (
                        <li key={concern.id || idx} className="flex items-start gap-3 pb-3 border-b border-slate-100 last:border-0 last:pb-0">
                          <span className="text-xs font-mono text-slate-400 mt-0.5 w-8 flex-shrink-0">
                            {concern.id || `Q${idx + 1}`}
                          </span>
                          <p className="text-slate-700 text-[15px]">{concern.title}</p>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* Риски */}
                {showRisks && (
                  <section id="section-risks" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Риски
                      <span className="ml-2 font-normal">({riskBrief!.risks.length})</span>
                    </h3>
                    <div className="space-y-4">
                      {riskBrief!.risks.map((risk, idx) => (
                        <RiskCard key={risk.id || idx} risk={risk} />
                      ))}
                    </div>
                  </section>
                )}

                {/* Задачи */}
                {hasTasks && (
                  <section id="section-tasks" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Задачи
                      <span className="ml-2 font-normal">({basicReport!.tasks!.length})</span>
                    </h3>
                    <TasksTable tasks={basicReport!.tasks!} />
                  </section>
                )}
              </div>
            ) : (
              // Fallback
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-slate-700 mb-2">
                  Сводка недоступна
                </h3>
                <p className="text-slate-500 mb-6 max-w-md mx-auto">
                  {detail?.has_risk_brief
                    ? 'Скачайте PDF для просмотра.'
                    : 'Аналитика не была сгенерирована.'}
                </p>
                {detail?.has_risk_brief && (
                  <button
                    onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                    className="px-5 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors flex items-center gap-2 font-medium mx-auto cursor-pointer"
                  >
                    <Download className="w-4 h-4" />
                    Скачать PDF
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
