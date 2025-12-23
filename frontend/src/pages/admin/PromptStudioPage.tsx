import { useEffect, useState, useCallback } from 'react';
import { promptsApi } from '../../api/adminApi';
import type { PromptTemplate, CreatePromptTemplateRequest, UpdatePromptTemplateRequest, DomainInfo } from '../../api/adminApi';

type TabId = 'general' | 'prompts' | 'schema';

interface FormData {
  name: string;
  slug: string;
  domain: string;
  description: string;
  system_prompt: string;
  user_prompt_template: string;
  response_schema: string;
  is_active: boolean;
  is_default: boolean;
}

const emptyForm: FormData = {
  name: '',
  slug: '',
  domain: 'universal',
  description: '',
  system_prompt: '',
  user_prompt_template: '',
  response_schema: '',
  is_active: true,
  is_default: false,
};

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .substring(0, 100);
}

export default function PromptStudioPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const [form, setForm] = useState<FormData>(emptyForm);
  const [schemaError, setSchemaError] = useState('');
  const [schemaValid, setSchemaValid] = useState<boolean | null>(null);
  const [filterDomain, setFilterDomain] = useState<string>('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [templatesRes, domainsRes] = await Promise.all([
        promptsApi.list({ domain: filterDomain || undefined }),
        promptsApi.getDomains(),
      ]);
      setTemplates(templatesRes.templates);
      setDomains(domainsRes.domains);
      setError('');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка загрузки';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [filterDomain]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectTemplate = async (id: number) => {
    try {
      const template = await promptsApi.get(id);
      setSelectedId(id);
      setIsCreating(false);
      setForm({
        name: template.name,
        slug: template.slug,
        domain: template.domain,
        description: template.description || '',
        system_prompt: template.system_prompt,
        user_prompt_template: template.user_prompt_template,
        response_schema: template.response_schema ? JSON.stringify(template.response_schema, null, 2) : '',
        is_active: template.is_active,
        is_default: template.is_default,
      });
      setSchemaError('');
      setSchemaValid(null);
      setActiveTab('general');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка загрузки шаблона';
      setError(errorMessage);
    }
  };

  const handleCreate = () => {
    setSelectedId(null);
    setIsCreating(true);
    setForm(emptyForm);
    setSchemaError('');
    setSchemaValid(null);
    setActiveTab('general');
  };

  const handleNameChange = (name: string) => {
    setForm(prev => ({
      ...prev,
      name,
      slug: isCreating ? slugify(name) : prev.slug,
    }));
  };

  const validateJsonSchema = (schemaStr: string): { valid: boolean; error?: string; parsed?: Record<string, unknown> } => {
    if (!schemaStr.trim()) {
      return { valid: true };
    }
    try {
      const parsed = JSON.parse(schemaStr);
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return { valid: false, error: 'Схема должна быть объектом' };
      }
      return { valid: true, parsed };
    } catch (e) {
      return { valid: false, error: `Невалидный JSON: ${(e as Error).message}` };
    }
  };

  const handleValidateSchema = async () => {
    const result = validateJsonSchema(form.response_schema);
    if (!result.valid) {
      setSchemaError(result.error || 'Ошибка валидации');
      setSchemaValid(false);
      return;
    }
    if (!result.parsed) {
      setSchemaError('');
      setSchemaValid(true);
      return;
    }
    try {
      const response = await promptsApi.validateSchema(result.parsed);
      if (response.valid && response.supported_by_gemini) {
        setSchemaValid(true);
        setSchemaError(response.warnings.length > 0 ? `Предупреждения: ${response.warnings.join(', ')}` : '');
      } else {
        setSchemaValid(false);
        setSchemaError(response.errors.join(', ') || 'Схема несовместима с Gemini');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка валидации';
      setSchemaError(errorMessage);
      setSchemaValid(false);
    }
  };

  const handleSave = async () => {
    // Validate required fields
    if (!form.name.trim()) {
      setError('Введите название');
      setActiveTab('general');
      return;
    }
    if (!form.slug.trim()) {
      setError('Введите slug');
      setActiveTab('general');
      return;
    }
    if (!form.system_prompt.trim()) {
      setError('Введите системный промпт');
      setActiveTab('prompts');
      return;
    }
    if (!form.user_prompt_template.trim()) {
      setError('Введите пользовательский промпт');
      setActiveTab('prompts');
      return;
    }

    // Validate schema if present
    let parsedSchema: Record<string, unknown> | undefined;
    if (form.response_schema.trim()) {
      const result = validateJsonSchema(form.response_schema);
      if (!result.valid) {
        setSchemaError(result.error || 'Ошибка');
        setActiveTab('schema');
        return;
      }
      parsedSchema = result.parsed;
    }

    setSaving(true);
    setError('');

    try {
      if (isCreating) {
        const data: CreatePromptTemplateRequest = {
          name: form.name,
          slug: form.slug,
          domain: form.domain,
          description: form.description || undefined,
          system_prompt: form.system_prompt,
          user_prompt_template: form.user_prompt_template,
          response_schema: parsedSchema,
          is_default: form.is_default,
        };
        const created = await promptsApi.create(data);
        await loadData();
        setSelectedId(created.id);
        setIsCreating(false);
      } else if (selectedId) {
        const data: UpdatePromptTemplateRequest = {
          name: form.name,
          description: form.description || undefined,
          system_prompt: form.system_prompt,
          user_prompt_template: form.user_prompt_template,
          response_schema: parsedSchema,
          is_active: form.is_active,
          is_default: form.is_default,
        };
        await promptsApi.update(selectedId, data);
        await loadData();
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка сохранения';
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId || !confirm('Удалить этот шаблон?')) return;

    try {
      await promptsApi.delete(selectedId);
      setSelectedId(null);
      setIsCreating(false);
      setForm(emptyForm);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ошибка удаления';
      setError(errorMessage);
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'general', label: 'Основное' },
    { id: 'prompts', label: 'Промпты' },
    { id: 'schema', label: 'Output Schema' },
  ];

  return (
    <div className="h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Prompt Studio</h1>
          <p className="text-gray-400 text-sm">Шаблоны промптов для генерации отчётов</p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="flex gap-4 h-[calc(100%-4rem)]">
        {/* Left sidebar - Template list */}
        <div className="w-72 flex-shrink-0 bg-gray-800 rounded-lg flex flex-col">
          {/* Filter & Create */}
          <div className="p-3 border-b border-gray-700 space-y-2">
            <select
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Все домены</option>
              {domains.map(d => (
                <option key={d.name} value={d.name}>{d.name} ({d.template_count})</option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded transition flex items-center justify-center"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Новый шаблон
            </button>
          </div>

          {/* Template list */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              </div>
            ) : templates.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                Шаблоны не найдены
              </div>
            ) : (
              <div className="py-1">
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => handleSelectTemplate(t.id)}
                    className={`w-full text-left px-3 py-2 border-l-2 transition ${
                      selectedId === t.id
                        ? 'bg-gray-700 border-blue-500 text-white'
                        : 'border-transparent text-gray-300 hover:bg-gray-700/50 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm truncate">{t.name}</span>
                      {!t.is_active && (
                        <span className="text-xs text-gray-500 ml-1">off</span>
                      )}
                    </div>
                    <div className="flex items-center mt-1 space-x-2">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-600 text-gray-300">{t.domain}</span>
                      {t.is_default && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-blue-600/30 text-blue-400">default</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right - Editor */}
        <div className="flex-1 bg-gray-800 rounded-lg flex flex-col min-w-0">
          {!selectedId && !isCreating ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>Выберите шаблон или создайте новый</p>
              </div>
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex border-b border-gray-700">
                {tabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-3 text-sm font-medium transition border-b-2 -mb-px ${
                      activeTab === tab.id
                        ? 'text-blue-400 border-blue-400'
                        : 'text-gray-400 border-transparent hover:text-gray-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
                <div className="flex-1" />
                {selectedId && (
                  <button
                    onClick={handleDelete}
                    className="px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/30 transition"
                  >
                    Удалить
                  </button>
                )}
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'general' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">Название *</label>
                        <input
                          type="text"
                          value={form.name}
                          onChange={(e) => handleNameChange(e.target.value)}
                          placeholder="Например: Протокол совещания"
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">Slug *</label>
                        <input
                          type="text"
                          value={form.slug}
                          onChange={(e) => setForm(prev => ({ ...prev, slug: e.target.value }))}
                          placeholder="meeting-protocol"
                          disabled={!isCreating}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 font-mono"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">Домен *</label>
                        <select
                          value={form.domain}
                          onChange={(e) => setForm(prev => ({ ...prev, domain: e.target.value }))}
                          disabled={!isCreating}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                        >
                          <option value="universal">universal</option>
                          <option value="construction">construction</option>
                          <option value="hr">hr</option>
                        </select>
                      </div>
                      <div className="flex items-end space-x-4">
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={form.is_active}
                            onChange={(e) => setForm(prev => ({ ...prev, is_active: e.target.checked }))}
                            className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-300">Активен</span>
                        </label>
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={form.is_default}
                            onChange={(e) => setForm(prev => ({ ...prev, is_default: e.target.checked }))}
                            className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-300">По умолчанию</span>
                        </label>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Описание</label>
                      <textarea
                        value={form.description}
                        onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Опциональное описание шаблона..."
                        rows={2}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'prompts' && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">System Prompt *</label>
                      <p className="text-xs text-gray-500 mb-2">Инструкции для AI модели о её роли и задачах</p>
                      <textarea
                        value={form.system_prompt}
                        onChange={(e) => setForm(prev => ({ ...prev, system_prompt: e.target.value }))}
                        placeholder="Ты — профессиональный секретарь-протоколист..."
                        rows={8}
                        className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">User Prompt Template *</label>
                      <p className="text-xs text-gray-500 mb-2">
                        Шаблон запроса. Переменные: {'{{transcript}}'}, {'{{speakers}}'}, {'{{metadata}}'}
                      </p>
                      <textarea
                        value={form.user_prompt_template}
                        onChange={(e) => setForm(prev => ({ ...prev, user_prompt_template: e.target.value }))}
                        placeholder="Проанализируй следующую транскрипцию и создай протокол совещания:&#10;&#10;{{transcript}}"
                        rows={10}
                        className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'schema' && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-sm font-medium text-gray-300">Response Schema (JSON)</label>
                        <button
                          onClick={handleValidateSchema}
                          className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition"
                        >
                          Проверить
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">
                        JSON Schema для структурированного вывода Gemini. Оставьте пустым для свободного текста.
                      </p>
                      <textarea
                        value={form.response_schema}
                        onChange={(e) => {
                          setForm(prev => ({ ...prev, response_schema: e.target.value }));
                          setSchemaError('');
                          setSchemaValid(null);
                        }}
                        placeholder='{"type": "object", "properties": {...}, "required": [...]}'
                        rows={16}
                        className={`w-full px-3 py-2 bg-gray-900 border rounded text-white text-sm focus:outline-none focus:ring-1 font-mono ${
                          schemaValid === true ? 'border-green-500 focus:ring-green-500' :
                          schemaValid === false ? 'border-red-500 focus:ring-red-500' :
                          'border-gray-600 focus:ring-blue-500'
                        }`}
                      />
                      {schemaError && (
                        <p className={`text-xs mt-1 ${schemaValid === true ? 'text-yellow-400' : 'text-red-400'}`}>
                          {schemaError}
                        </p>
                      )}
                      {schemaValid === true && !schemaError && (
                        <p className="text-xs mt-1 text-green-400">Схема валидна и совместима с Gemini</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-gray-700 p-4 flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setSelectedId(null);
                    setIsCreating(false);
                    setForm(emptyForm);
                  }}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded transition"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white text-sm rounded transition flex items-center"
                >
                  {saving && (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  )}
                  {isCreating ? 'Создать' : 'Сохранить'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
