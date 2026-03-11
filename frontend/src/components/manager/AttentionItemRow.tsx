import { Flame, AlertTriangle } from 'lucide-react';
import { type AttentionItem } from '../../api/client';

export function AttentionItemRow({
  item,
  onStatusChange,
  onViewDetails,
}: {
  item: AttentionItem;
  onStatusChange: (status: 'new' | 'done') => void;
  onViewDetails: () => void;
}) {
  const isCritical = item.severity === 'critical';
  const isDone = item.status === 'done';

  return (
    <div className={`p-4 flex items-start gap-3 transition-colors ${
      isDone ? 'bg-slate-50 opacity-60' : 'hover:bg-slate-50'
    }`}>
      <div className={`mt-1 ${
        isDone ? 'text-slate-400' : isCritical ? 'text-red-500' : 'text-amber-500'
      }`}>
        {isCritical ? <Flame className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
      </div>
      <div className="flex-1 min-w-0">
        <button
          onClick={onViewDetails}
          className={`text-left font-medium transition-colors ${
            isDone
              ? 'text-slate-400 line-through'
              : 'text-slate-800 hover:text-severin-red'
          }`}
        >
          {item.problem_text}
        </button>
        <p className={`text-sm truncate mt-1 ${isDone ? 'text-slate-400' : 'text-slate-500'}`}>
          {item.project_name} • {item.source_file}
        </p>
      </div>
      <input
        type="checkbox"
        checked={isDone}
        onChange={(e) => onStatusChange(e.target.checked ? 'done' : 'new')}
        className="w-5 h-5 rounded border-slate-300 text-severin-red focus:ring-severin-red"
      />
    </div>
  );
}
