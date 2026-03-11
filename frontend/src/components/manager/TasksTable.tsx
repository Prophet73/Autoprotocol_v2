import React from 'react';
import { type TaskItem } from '../../api/client';

export function TasksTable({ tasks }: { tasks: TaskItem[] }) {
  const priorityText: Record<string, { label: string; color: string }> = {
    high: { label: 'Высокий', color: 'text-red-600' },
    medium: { label: 'Средний', color: 'text-amber-600' },
    low: { label: 'Низкий', color: 'text-slate-400' },
  };

  // Sort by category (like in Excel report), then by priority within category
  const sortedTasks = [...tasks].sort((a, b) => {
    // First sort by category
    const catA = a.category || 'Без категории';
    const catB = b.category || 'Без категории';
    if (catA !== catB) {
      return catA.localeCompare(catB, 'ru');
    }
    // Then by priority within category
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.priority || 'medium'] || 1) - (order[b.priority || 'medium'] || 1);
  });

  // Group tasks by category for display
  let currentCategory = '';
  let taskNumber = 0;

  return (
    <div className="overflow-x-auto -mx-6">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-100 border-y border-slate-200">
            <th className="py-2.5 pl-6 pr-2 text-left font-medium text-slate-600 w-10">#</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '42%' }}>Задача</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '12%' }}>Приоритет</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '18%' }}>Ответственный</th>
            <th className="py-2.5 pl-3 pr-6 text-left font-medium text-slate-600" style={{ width: '12%' }}>Срок</th>
          </tr>
        </thead>
        <tbody>
          {sortedTasks.map((task, idx) => {
            const category = task.category || 'Без категории';
            const showCategoryHeader = category !== currentCategory;
            currentCategory = category;
            taskNumber++;
            const priority = priorityText[task.priority || 'medium'] || priorityText.medium;

            return (
              <React.Fragment key={`task-${idx}`}>
                {showCategoryHeader && (
                  <tr className="bg-slate-50">
                    <td colSpan={5} className="py-2 pl-6 pr-6 text-xs font-semibold text-slate-700 uppercase tracking-wide border-b border-slate-200">
                      {category}
                    </td>
                  </tr>
                )}
                <tr className="border-b border-slate-100 hover:bg-blue-50/50 transition-colors">
                  <td className="py-2.5 pl-6 pr-2 text-slate-400 text-xs">
                    {taskNumber}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    {task.description}
                  </td>
                  <td className={`py-2.5 px-3 text-xs font-medium ${priority.color}`}>
                    {priority.label}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {task.responsible || <span className="text-slate-300">—</span>}
                  </td>
                  <td className="py-2.5 pl-3 pr-6 text-slate-500 text-xs whitespace-nowrap">
                    {task.deadline || <span className="text-slate-300">—</span>}
                  </td>
                </tr>
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
