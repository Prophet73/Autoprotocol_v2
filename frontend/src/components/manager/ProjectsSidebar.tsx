import {
  Search,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
} from 'lucide-react';
import { type ProjectHealth } from '../../api/client';
import { healthColors } from './constants';

function ProjectItem({
  project,
  isSelected,
  collapsed,
  onClick,
}: {
  project: ProjectHealth;
  isSelected: boolean;
  collapsed: boolean;
  onClick: () => void;
}) {
  const colors = healthColors[project.health];

  if (collapsed) {
    return (
      <button
        onClick={onClick}
        className={`w-full p-2 rounded-lg transition-all ${
          isSelected ? 'bg-red-50 ring-2 ring-severin-red' : 'hover:bg-slate-100'
        }`}
        title={project.name}
      >
        <div className={`w-3 h-3 rounded-full ${colors.bg} mx-auto`} />
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className={`w-full p-3 rounded-lg text-left transition-all ${
        isSelected
          ? 'bg-red-50 ring-2 ring-severin-red'
          : 'hover:bg-slate-100'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${colors.bg} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-800 truncate">{project.name}</p>
          <p className="text-xs text-slate-500">{project.project_code}</p>
        </div>
      </div>
      {project.open_issues > 0 && (
        <div className="mt-2 text-xs text-amber-600">
          {project.open_issues} открытых проблем
        </div>
      )}
    </button>
  );
}

export function ProjectsSidebar({
  projects,
  selectedProjectId,
  onSelectProject,
  projectSearch,
  onSearchChange,
  collapsed,
  onToggleCollapse,
}: {
  projects: ProjectHealth[];
  selectedProjectId: number | null;
  onSelectProject: (id: number | null) => void;
  projectSearch: string;
  onSearchChange: (value: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  return (
    <div className="bg-white border-r border-slate-200 flex flex-col overflow-hidden" data-tour="dashboard-projects">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        {!collapsed && (
          <h2 className="font-semibold text-slate-800">Мои проекты</h2>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="p-3 border-b border-slate-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Поиск..."
              value={projectSearch}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-severin-red/20 focus:border-severin-red"
            />
          </div>
        </div>
      )}

      {/* All Projects Button */}
      <button
        onClick={() => onSelectProject(null)}
        className={`m-3 p-3 rounded-lg text-left transition-all ${
          selectedProjectId === null
            ? 'bg-severin-red text-white'
            : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
        }`}
      >
        {collapsed ? (
          <LayoutDashboard className="w-5 h-5 mx-auto" />
        ) : (
          <div className="flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5" />
            <span className="font-medium">Все проекты</span>
          </div>
        )}
      </button>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {projects.map((project) => (
          <ProjectItem
            key={project.id}
            project={project}
            isSelected={selectedProjectId === project.id}
            collapsed={collapsed}
            onClick={() => onSelectProject(project.id)}
          />
        ))}
      </div>
    </div>
  );
}
