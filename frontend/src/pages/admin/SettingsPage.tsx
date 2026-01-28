import { useEffect, useState } from 'react';
import { settingsApi } from '../../api/adminApi';
import type { SystemSetting } from '../../api/adminApi';

interface SettingModalProps {
  isOpen: boolean;
  setting: SystemSetting | null;
  onClose: () => void;
  onSave: (key: string, value: string, description?: string) => void;
}

function SettingModal({ isOpen, setting, onClose, onSave }: SettingModalProps) {
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (setting) {
      setKey(setting.key);
      setValue(setting.value);
      setDescription(setting.description || '');
    } else {
      setKey('');
      setValue('');
      setDescription('');
    }
  }, [setting]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(key, value, description || undefined);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-white rounded-lg p-6 w-full max-w-md shadow-xl border border-slate-200 mx-4">
        <h2 className="text-xl font-bold text-slate-800 mb-6">
          {setting ? 'Редактировать настройку' : 'Создать настройку'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Ключ</label>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              required
              disabled={!!setting}
              placeholder="например: max_file_size_mb"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red disabled:opacity-50"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Значение</label>
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              rows={3}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Описание</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Опциональное описание"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-severin-red"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-300 text-slate-800 rounded-lg transition"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-severin-red hover:bg-severin-red-dark disabled:bg-blue-800 text-slate-800 rounded-lg transition"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSetting, setEditingSetting] = useState<SystemSetting | null>(null);
  const [initializing, setInitializing] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await settingsApi.list();
      setSettings(response.settings);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки настроек');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingSetting(null);
    setModalOpen(true);
  };

  const handleEdit = (setting: SystemSetting) => {
    setEditingSetting(setting);
    setModalOpen(true);
  };

  const handleDelete = async (setting: SystemSetting) => {
    if (!confirm(`Удалить настройку "${setting.key}"?`)) return;

    try {
      await settingsApi.delete(setting.key);
      await loadSettings();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleSave = async (key: string, value: string, description?: string) => {
    if (editingSetting) {
      await settingsApi.update(key, value, description);
    } else {
      await settingsApi.create(key, value, description);
    }
    await loadSettings();
  };

  const handleInitialize = async () => {
    if (!confirm('Инициализировать настройки по умолчанию? Существующие значения не будут перезаписаны.')) return;

    try {
      setInitializing(true);
      const result = await settingsApi.initialize();
      alert(`Создано настроек: ${result.created}`);
      await loadSettings();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка инициализации');
    } finally {
      setInitializing(false);
    }
  };

  // Group settings by category
  const groupedSettings = settings.reduce((acc, setting) => {
    const category = setting.key.split('_')[0];
    if (!acc[category]) acc[category] = [];
    acc[category].push(setting);
    return acc;
  }, {} as Record<string, SystemSetting[]>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Настройки системы</h1>
          <p className="text-slate-500 mt-1">Конфигурация SeverinAutoprotocol ({settings.length})</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleInitialize}
            disabled={initializing}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-300 disabled:bg-slate-50 text-slate-800 rounded-lg transition flex items-center"
          >
            {initializing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Инициализация...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Инициализировать
              </>
            )}
          </button>
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-severin-red hover:bg-severin-red-dark text-slate-800 rounded-lg transition flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Создать
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Settings */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : settings.length === 0 ? (
        <div className="bg-white rounded-lg p-12 text-center shadow-sm border border-slate-200">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="text-slate-500 mb-4">Настройки не найдены</p>
          <button
            onClick={handleInitialize}
            className="px-4 py-2 bg-severin-red hover:bg-severin-red-dark text-slate-800 rounded-lg transition"
          >
            Инициализировать настройки по умолчанию
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedSettings).map(([category, categorySettings]) => (
            <div key={category} className="bg-white rounded-lg overflow-hidden shadow-sm border border-slate-200">
              <div className="bg-slate-50 px-6 py-3">
                <h3 className="text-sm font-medium text-slate-600 uppercase">{category}</h3>
              </div>
              <div className="divide-y divide-slate-200">
                {categorySettings.map((setting) => (
                  <div key={setting.key} className="px-6 py-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center">
                          <code className="text-sm font-mono text-severin-red">{setting.key}</code>
                        </div>
                        {setting.description && (
                          <p className="text-sm text-slate-500 mt-1">{setting.description}</p>
                        )}
                        <div className="mt-2 p-2 bg-slate-100 rounded font-mono text-sm text-slate-600 break-all">
                          {setting.value}
                        </div>
                        <p className="text-xs text-slate-400 mt-2">
                          Обновлено: {new Date(setting.updated_at).toLocaleString('ru-RU')}
                          {setting.updated_by && ` пользователем ${setting.updated_by}`}
                        </p>
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleEdit(setting)}
                          className="p-2 text-slate-500 hover:text-severin-red hover:bg-slate-50 rounded transition"
                          title="Редактировать"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(setting)}
                          className="p-2 text-slate-500 hover:text-red-600 hover:bg-slate-50 rounded transition"
                          title="Удалить"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <SettingModal
        isOpen={modalOpen}
        setting={editingSetting}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
