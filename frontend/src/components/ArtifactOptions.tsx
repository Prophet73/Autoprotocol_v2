import { FileText, Table, FileSpreadsheet, Brain, Check } from 'lucide-react';

export interface ArtifactState {
  transcript: boolean;
  tasks: boolean;
  report: boolean;
  analysis: boolean;
}

interface ArtifactOptionsProps {
  value: ArtifactState;
  onChange: (value: ArtifactState) => void;
}

const artifacts = [
  {
    id: 'tasks' as const,
    label: 'Excel отчёт',
    description: 'Задачи и поручения',
    icon: FileSpreadsheet,
  },
  {
    id: 'report' as const,
    label: 'Word протокол',
    description: 'Саммари, эмоции, задачи',
    icon: Table,
  },
  {
    id: 'transcript' as const,
    label: 'Транскрибация',
    description: 'Полный текст с таймкодами',
    icon: FileText,
  },
  {
    id: 'analysis' as const,
    label: 'ИИ Анализ',
    description: 'Глубокий анализ',
    icon: Brain,
  },
];

export function ArtifactOptions({ value, onChange }: ArtifactOptionsProps) {
  const handleToggle = (id: keyof ArtifactState) => {
    onChange({ ...value, [id]: !value[id] });
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {artifacts.map((artifact) => {
        const Icon = artifact.icon;
        const isChecked = value[artifact.id];

        return (
          <button
            key={artifact.id}
            type="button"
            onClick={() => handleToggle(artifact.id)}
            className={`
              flex items-center gap-3 py-2.5 px-3 rounded-lg border-2 text-left transition-all
              ${isChecked
                ? 'border-emerald-400 bg-emerald-50'
                : 'border-slate-200 hover:border-slate-300 bg-white'
              }
            `}
          >
            <div className={`
              w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0
              ${isChecked ? 'bg-emerald-100' : 'bg-slate-100'}
            `}>
              <Icon className={`w-4 h-4 ${isChecked ? 'text-emerald-600' : 'text-slate-400'}`} />
            </div>

            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${isChecked ? 'text-emerald-900' : 'text-slate-700'}`}>
                {artifact.label}
              </p>
              <p className="text-xs text-slate-500 truncate">{artifact.description}</p>
            </div>

            <div className={`
              w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              ${isChecked ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300'}
            `}>
              {isChecked && <Check className="w-3 h-3 text-white" />}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export const defaultArtifactState: ArtifactState = {
  transcript: false,
  tasks: true,
  report: true,
  analysis: false,
};
