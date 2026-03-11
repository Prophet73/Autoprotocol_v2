import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Target,
  User,
  Clock,
} from 'lucide-react';
import { type ProjectRisk } from '../../api/client';
import { categoryLabels, driverTypeLabels } from './constants';

export function RiskCard({ risk }: { risk: ProjectRisk }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Score and severity - muted colors
  const score = risk.probability * risk.impact;
  const getSeverityColor = () => {
    if (score >= 15) return { bg: 'bg-slate-50', border: 'border-l-red-400', badge: 'bg-red-100 text-red-700' };
    if (score >= 9) return { bg: 'bg-slate-50', border: 'border-l-amber-400', badge: 'bg-amber-100 text-amber-700' };
    return { bg: 'bg-slate-50', border: 'border-l-slate-300', badge: 'bg-slate-100 text-slate-600' };
  };
  const colors = getSeverityColor();

  const hasDrivers = risk.drivers && risk.drivers.length > 0;
  // Show AI recommendation whenever it exists (even if there's a decision)
  const hasMitigation = !!risk.mitigation;

  return (
    <div className={`rounded-lg border border-slate-200 ${colors.border} border-l-4 ${colors.bg} overflow-hidden`}>
      {/* Risk Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge}`}>
                {risk.id}
              </span>
              <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-500">
                {categoryLabels[risk.category] || risk.category}
              </span>
              <span className="text-xs text-slate-400">
                {score} баллов
              </span>
            </div>
            <h4 className="font-medium text-slate-800 mb-1">{risk.title}</h4>
            <p className="text-sm text-slate-600">{risk.description}</p>
          </div>
        </div>

        {/* Consequences */}
        {risk.consequences && (
          <div className="mt-3 p-3 bg-white rounded border border-slate-100">
            <span className="text-xs text-slate-400 uppercase">Последствия:</span>
            <p className="text-sm text-slate-600 mt-1">{risk.consequences}</p>
          </div>
        )}

        {/* Decision from meeting - ALWAYS VISIBLE */}
        {risk.decision && (
          <div className="mt-3 p-3 bg-emerald-50 rounded border border-emerald-100">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-emerald-600 uppercase">Решение:</span>
            </div>
            <p className="text-sm text-slate-700">{risk.decision}</p>
          </div>
        )}

        {/* Responsible and Deadline */}
        {(risk.responsible || risk.deadline) && (
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {risk.responsible && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <User className="w-3.5 h-3.5" />
                <span>{risk.responsible}</span>
              </div>
            )}
            {risk.deadline && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>{risk.deadline}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Accordion for detailed analysis */}
      {(hasDrivers || hasMitigation) && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-4 py-2.5 bg-slate-700 hover:bg-slate-800 border-t border-slate-600 flex items-center justify-center gap-2 text-sm text-white font-medium transition-colors cursor-pointer"
          >
            <Target className="w-4 h-4" />
            <span>{isExpanded ? 'Скрыть анализ ИИ' : 'Показать анализ ИИ'}</span>
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {isExpanded && (
            <div className="px-4 pb-4 pt-3 space-y-3 bg-white">
              {/* AI Mitigation recommendation */}
              {hasMitigation && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-5 h-5 text-blue-600" />
                    <span className="text-sm font-semibold text-blue-800">Рекомендация ИИ</span>
                  </div>
                  <p className="text-slate-700">{risk.mitigation}</p>
                </div>
              )}

              {/* Drivers (root causes, aggravators, blockers) */}
              {hasDrivers && (
                <div className="space-y-2">
                  {risk.drivers.map((driver, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded border border-slate-100">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-slate-400">{driver.id}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          driver.type === 'root_cause' ? 'bg-slate-200 text-slate-600' :
                          driver.type === 'aggravator' ? 'bg-slate-200 text-slate-600' :
                          'bg-slate-200 text-slate-600'
                        }`}>
                          {driverTypeLabels[driver.type] || driver.type}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-slate-700">{driver.title}</p>
                      <p className="text-sm text-slate-500 mt-1">{driver.description}</p>
                      {driver.evidence && (
                        <p className="text-xs text-slate-400 mt-2 italic">"{driver.evidence}"</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
