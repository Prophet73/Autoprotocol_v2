// Health status colors
export const healthColors = {
  critical: { bg: 'bg-red-500', text: 'text-red-600', light: 'bg-red-50' },
  attention: { bg: 'bg-amber-500', text: 'text-amber-600', light: 'bg-amber-50' },
  stable: { bg: 'bg-green-500', text: 'text-green-600', light: 'bg-green-50' },
};

// Section type for navigation
export type SectionId = 'participants' | 'summary' | 'atmosphere' | 'concerns' | 'risks' | 'tasks';

// Status labels
export const statusLabels: Record<string, string> = {
  critical: 'Критический',
  attention: 'Требует внимания',
  stable: 'Стабильный',
};

// Atmosphere labels
export const atmosphereLabels: Record<string, string> = {
  tense: 'Напряжённая',
  working: 'Рабочее напряжение',
  calm: 'Спокойная',
  constructive: 'Конструктивная',
  positive: 'Позитивная',
  conflict: 'Конфликтная',
};

// Atmosphere colors
export const atmosphereColors: Record<string, string> = {
  tense: 'text-red-600',
  conflict: 'text-red-600',
  working: 'text-amber-600',
  calm: 'text-emerald-600',
  constructive: 'text-emerald-600',
  positive: 'text-emerald-600',
};

// Risk category labels
export const categoryLabels: Record<string, string> = {
  external: 'Внешние',
  preinvest: 'Прединвестиционные',
  design: 'Проектные',
  production: 'Строительные',
  management: 'Управленческие',
  operational: 'Эксплуатационные',
  safety: 'Безопасность',
};

// Risk driver type labels
export const driverTypeLabels: Record<string, string> = {
  root_cause: 'Первопричина',
  aggravator: 'Усугубляющий фактор',
  blocker: 'Блокирующий фактор',
};
