import { FileText, Table, FileSpreadsheet, Check, Shield } from 'lucide-react';

export interface ArtifactState {
  transcript: boolean;
  tasks: boolean;
  report: boolean;
  riskBrief: boolean;
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
    id: 'riskBrief' as const,
    label: 'Риск-бриф (PDF)',
    description: 'Матрица рисков (для клиента)',
    icon: Shield,
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
                ? 'border-severin-red bg-red-50'
                : 'border-slate-200 hover:border-slate-300 bg-white'
              }
            `}
          >
            <div className={`
              w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0
              ${isChecked ? 'bg-red-100' : 'bg-slate-100'}
            `}>
              <Icon className={`w-4 h-4 ${isChecked ? 'text-severin-red' : 'text-slate-400'}`} />
            </div>

            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${isChecked ? 'text-slate-900' : 'text-slate-700'}`}>
                {artifact.label}
              </p>
              <p className="text-xs text-slate-500 truncate">{artifact.description}</p>
            </div>

            <div className={`
              w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              ${isChecked ? 'bg-severin-red border-severin-red' : 'border-slate-300'}
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
  riskBrief: false,
};
