import { useEffect, useState } from 'react';
import { settingsApi } from '../../api/adminApi';
import { getApiErrorMessage } from '../../utils/errorMessage';
import { useConfirm } from '../../hooks/useConfirm';
import type { SystemSetting } from '../../api/adminApi';

const CATEGORY_META: Record<string, { label: string; icon: string; order: number }> = {
  llm: { label: 'Модели ИИ', icon: '🤖', order: 0 },
  limits: { label: 'Лимиты', icon: '📏', order: 1 },
  retention: { label: 'Хранение данных', icon: '🗄️', order: 2 },
  custom: { label: 'Пользовательские', icon: '⚙️', order: 3 },
  other: { label: 'Прочее', icon: '📋', order: 4 },
};

function SettingInput({
  setting,
  value,
  onChange,
}: {
  setting: SystemSetting;
  value: string;
  onChange: (v: string) => void;
}) {
  if (setting.input_type === 'select' && setting.options) {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition"
      >
        {setting.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
        {/* If current value is not in options (custom), still show it */}
        {!setting.options.includes(value) && (
          <option value={value}>{value} (custom)</option>
        )}
      </select>
    );
  }

  if (setting.input_type === 'number') {
    return (
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        min={0}
        className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition"
      />
    );
  }

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition"
    />
  );
}

function SettingCard({
  setting,
  onSaved,
  onReset,
  onDelete,
}: {
  setting: SystemSetting;
  onSaved: () => void;
  onReset: (key: string) => void;
  onDelete: (key: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(setting.value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValue(setting.value);
    setEditing(false);
  }, [setting.value]);

  const hasChanges = value !== setting.value;
  const isCustom = setting.category === 'custom';

  const handleSave = async () => {
    if (!hasChanges) return;
    setSaving(true);
    setError(null);
    try {
      await settingsApi.update(setting.key, value);
      onSaved();
      setEditing(false);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setValue(setting.value);
    setEditing(false);
    setError(null);
  };

  return (
    <div className="px-5 py-4 hover:bg-slate-50/50 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 mb-1">
            <code className="text-sm font-mono font-semibold text-slate-700">{setting.key}</code>
            {setting.is_default ? (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500">
                default
              </span>
            ) : (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                изменено
              </span>
            )}
          </div>

          {/* Description */}
          {setting.description && (
            <p className="text-sm text-slate-500 mb-3">{setting.description}</p>
          )}

          {/* Value display / edit */}
          {editing ? (
            <div className="space-y-2">
              <SettingInput setting={setting} value={value} onChange={setValue} />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving || !hasChanges}
                  className="px-3 py-1.5 text-sm bg-severin-red hover:bg-severin-red-dark disabled:opacity-50 text-white rounded-lg transition"
                >
                  {saving ? 'Сохранение...' : 'Сохранить'}
                </button>
                <button
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : (
            <div
              onClick={() => setEditing(true)}
              className="inline-block px-3 py-1.5 bg-slate-100 rounded-lg font-mono text-sm text-slate-700 cursor-pointer hover:bg-slate-200 transition"
              title="Нажмите для редактирования"
            >
              {setting.value}
            </div>
          )}

          {/* Meta info */}
          {setting.updated_at && (
            <p className="text-xs text-slate-400 mt-2">
              Обновлено: {new Date(setting.updated_at).toLocaleString('ru-RU')}
              {setting.updated_by && <> · {setting.updated_by}</>}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="p-2 text-slate-400 hover:text-severin-red hover:bg-slate-100 rounded-lg transition"
              title="Редактировать"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          {!setting.is_default && setting.default_value != null && (
            <button
              onClick={() => onReset(setting.key)}
              className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
              title={`Сбросить к дефолту (${setting.default_value})`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          )}
          {isCustom && (
            <button
              onClick={() => onDelete(setting.key)}
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
              title="Удалить"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { confirm, alert, ConfirmDialog } = useConfirm();
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await settingsApi.list();
      setSettings(response.settings);
      setError('');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка загрузки настроек'));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (key: string) => {
    const setting = settings.find((s) => s.key === key);
    if (!setting) return;
    if (!(await confirm(
      `Сбросить "${key}" к значению по умолчанию (${setting.default_value})?`
    ))) return;

    try {
      await settingsApi.reset(key);
      await loadSettings();
    } catch (err) {
      await alert(getApiErrorMessage(err, 'Ошибка сброса'));
    }
  };

  const handleDelete = async (key: string) => {
    if (!(await confirm(`Удалить настройку "${key}"?`, { variant: 'danger' }))) return;

    try {
      await settingsApi.delete(key);
      await loadSettings();
    } catch (err) {
      await alert(getApiErrorMessage(err, 'Ошибка удаления'));
    }
  };

  // Group by category
  const grouped = settings.reduce((acc, s) => {
    const cat = s.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(s);
    return acc;
  }, {} as Record<string, SystemSetting[]>);

  const sortedCategories = Object.keys(grouped).sort(
    (a, b) => (CATEGORY_META[a]?.order ?? 99) - (CATEGORY_META[b]?.order ?? 99)
  );

  const customizedCount = settings.filter((s) => !s.is_default).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Настройки системы</h1>
          <p className="text-slate-500 mt-1">
            {settings.length} настроек
            {customizedCount > 0 && (
              <> · <span className="text-amber-600">{customizedCount} изменено</span></>
            )}
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-slate-300 border-t-severin-red"></div>
        </div>
      ) : (
        <div className="space-y-5">
          {sortedCategories.map((category) => {
            const meta = CATEGORY_META[category] || { label: category, icon: '📋', order: 99 };
            const items = grouped[category];

            return (
              <div key={category} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                {/* Category header */}
                <div className="px-5 py-3 bg-slate-50 border-b border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-600 flex items-center gap-2">
                    <span>{meta.icon}</span>
                    {meta.label}
                    <span className="text-xs font-normal text-slate-400">({items.length})</span>
                  </h3>
                </div>

                {/* Settings */}
                <div className="divide-y divide-slate-100">
                  {items.map((setting) => (
                    <SettingCard
                      key={setting.key}
                      setting={setting}
                      onSaved={loadSettings}
                      onReset={handleReset}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {ConfirmDialog}
    </div>
  );
}
