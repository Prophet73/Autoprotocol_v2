import { useEffect, useState } from 'react';
import { projectsApi, usersApi } from '../../api/adminApi';
import type { Project, CreateProjectRequest, User } from '../../api/adminApi';

interface ProjectModalProps {
  isOpen: boolean;
  project: Project | null;
  users: User[];
  onClose: () => void;
  onSave: (data: CreateProjectRequest | Partial<Project>) => void;
}

function ProjectModal({ isOpen, project, users, onClose, onSave }: ProjectModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    project_code: '',
    description: '',
    manager_id: null as number | null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      if (project) {
        setFormData({
          name: project.name,
          project_code: project.project_code || '',
          description: project.description || '',
          manager_id: project.manager_id,
        });
      } else {
        setFormData({
          name: '',
          project_code: '',
          description: '',
          manager_id: null,
        });
      }
      setError('');
    }
  }, [project, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);

    const payload = {
      name: formData.name,
      project_code: formData.project_code || undefined,
      description: formData.description || undefined,
      manager_id: formData.manager_id || undefined,
    };

    try {
      await onSave(payload);
      onClose();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка сохранения';
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-bold text-white mb-6">
          {project ? 'Редактировать проект' : 'Создать проект'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-900/50 border border-red-500 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Код проекта</label>
              <input
                type="text"
                value={formData.project_code}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 4);
                  setFormData({ ...formData, project_code: value });
                }}
                placeholder="0000"
                maxLength={4}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">4 цифры, авто если пусто</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Название</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder="Название проекта"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Описание</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              placeholder="Опциональное описание"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              РПУ (Руководитель проекта)
            </label>
            <select
              value={formData.manager_id || ''}
              onChange={(e) => setFormData({
                ...formData,
                manager_id: e.target.value ? Number(e.target.value) : null
              })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Не назначен</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name || user.email} ({user.role})
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-lg transition"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================================
// User Access Modal (manage users who have access to a project)
// ============================================================================

interface UserAccessModalProps {
  isOpen: boolean;
  project: Project | null;
  allUsers: User[];
  onClose: () => void;
  onSave: (projectId: number, userIds: number[]) => Promise<void>;
}

function UserAccessModal({ isOpen, project, allUsers, onClose, onSave }: UserAccessModalProps) {
  const [selectedUsers, setSelectedUsers] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (isOpen && project) {
      loadProjectUsers();
    }
  }, [isOpen, project]);

  const loadProjectUsers = async () => {
    if (!project) return;
    setLoading(true);
    try {
      const response = await usersApi.getProjectUsers(project.id);
      setSelectedUsers(new Set(response.user_ids));
    } catch (err) {
      console.error('Error loading project users:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleUser = (userId: number) => {
    setSelectedUsers(prev => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedUsers(new Set(filteredUsers.map(u => u.id)));
  };

  const selectNone = () => {
    setSelectedUsers(new Set());
  };

  const handleSave = async () => {
    if (!project) return;
    setSaving(true);
    try {
      await onSave(project.id, Array.from(selectedUsers));
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка сохранения доступов');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen || !project) return null;

  const filteredUsers = allUsers.filter(u =>
    (u.full_name?.toLowerCase().includes(search.toLowerCase()) || false) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  // Sort: selected first, then by name
  const sortedUsers = [...filteredUsers].sort((a, b) => {
    const aSelected = selectedUsers.has(a.id);
    const bSelected = selectedUsers.has(b.id);
    if (aSelected && !bSelected) return -1;
    if (!aSelected && bSelected) return 1;
    return (a.full_name || a.email).localeCompare(b.full_name || b.email);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-white">Доступ пользователей</h2>
            <p className="text-gray-400 text-sm mt-1">
              {project.name} ({project.project_code})
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Поиск по имени или email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={selectAll}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Выбрать все
          </button>
          <button
            onClick={selectNone}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Снять все
          </button>
          <span className="text-sm text-gray-400 ml-auto">
            Выбрано: {selectedUsers.size} из {allUsers.length}
          </span>
        </div>

        {/* User list */}
        <div className="flex-1 overflow-y-auto min-h-[200px] max-h-[400px] border border-gray-700 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : sortedUsers.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              Пользователи не найдены
            </div>
          ) : (
            <div className="divide-y divide-gray-700">
              {sortedUsers.map((user) => (
                <label
                  key={user.id}
                  className={`flex items-center px-4 py-3 cursor-pointer transition ${
                    selectedUsers.has(user.id)
                      ? 'bg-blue-900/30'
                      : 'hover:bg-gray-700/50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedUsers.has(user.id)}
                    onChange={() => toggleUser(user.id)}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <div className="ml-3 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium truncate">
                        {user.full_name || 'Без имени'}
                      </span>
                      <span className={`px-1.5 py-0.5 text-xs rounded ${
                        user.is_superuser ? 'bg-purple-900/50 text-purple-400' :
                        user.role === 'admin' ? 'bg-blue-900/50 text-blue-400' :
                        user.role === 'manager' ? 'bg-green-900/50 text-green-400' :
                        'bg-gray-700 text-gray-400'
                      }`}>
                        {user.is_superuser ? 'Super' : user.role}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 truncate">
                      {user.email}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 mt-4 pt-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition"
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-lg transition"
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [showArchived, setShowArchived] = useState(false);

  // User access modal
  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [accessProject, setAccessProject] = useState<Project | null>(null);

  // Project user counts
  const [projectUserCounts, setProjectUserCounts] = useState<Record<number, number>>({});

  useEffect(() => {
    loadProjects();
    loadUsers();
  }, [showArchived]);

  const loadUsers = async () => {
    try {
      // Load all active users as potential managers
      const response = await usersApi.list({ limit: 500 });
      setUsers(response.users);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await projectsApi.list({
        is_active: showArchived ? undefined : true,
        limit: 100,
      });
      setProjects(response.projects);
      setTotal(response.total);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки проектов');
    } finally {
      setLoading(false);
    }
  };

  // Load user counts for projects
  useEffect(() => {
    const loadUserCounts = async () => {
      const counts: Record<number, number> = {};
      for (const project of projects) {
        try {
          const response = await usersApi.getProjectUsers(project.id);
          counts[project.id] = response.user_ids.length;
        } catch {
          counts[project.id] = 0;
        }
      }
      setProjectUserCounts(counts);
    };

    if (projects.length > 0 && projects.length <= 50) {
      loadUserCounts();
    }
  }, [projects]);

  const handleCreate = () => {
    setEditingProject(null);
    setModalOpen(true);
  };

  const handleEdit = (project: Project) => {
    setEditingProject(project);
    setModalOpen(true);
  };

  const handleArchive = async (project: Project) => {
    if (!confirm(`Архивировать проект "${project.name}"?`)) return;

    try {
      await projectsApi.archive(project.id);
      await loadProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка архивирования');
    }
  };

  const handleDelete = async (project: Project) => {
    if (!confirm(`Удалить проект "${project.name}"? Это действие необратимо.`)) return;

    try {
      await projectsApi.delete(project.id);
      await loadProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleSave = async (data: CreateProjectRequest | Partial<Project>) => {
    if (editingProject) {
      await projectsApi.update(editingProject.id, data);
    } else {
      await projectsApi.create(data as CreateProjectRequest);
    }
    await loadProjects();
  };

  const handleOpenAccessModal = (project: Project) => {
    setAccessProject(project);
    setAccessModalOpen(true);
  };

  const handleSaveUserAccess = async (projectId: number, userIds: number[]) => {
    // Get current users
    const current = await usersApi.getProjectUsers(projectId);
    const currentSet = new Set(current.user_ids);
    const newSet = new Set(userIds);

    // Revoke access from users no longer in the list
    for (const userId of current.user_ids) {
      if (!newSet.has(userId)) {
        await usersApi.revokeProjectAccess(userId, projectId);
      }
    }

    // Grant access to new users
    for (const userId of userIds) {
      if (!currentSet.has(userId)) {
        await usersApi.grantProjectAccess(userId, projectId);
      }
    }

    // Update count
    setProjectUserCounts(prev => ({
      ...prev,
      [projectId]: userIds.length,
    }));
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Проекты</h1>
          <p className="text-gray-400 mt-1">Управление строительными проектами ({total})</p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center justify-center"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Создать проект
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
          />
          <span className="ml-2 text-gray-300">Показать архивные</span>
        </label>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Projects Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-gray-800 rounded-lg p-12 text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <p className="text-gray-400 mb-4">Проекты не найдены</p>
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
          >
            Создать первый проект
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className={`bg-gray-800 rounded-lg p-6 ${
                !project.is_active ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white">{project.name}</h3>
                  <div className="flex items-center mt-1">
                    <code className="text-sm font-mono text-blue-400 bg-gray-700 px-2 py-0.5 rounded">
                      {project.project_code}
                    </code>
                    <button
                      onClick={() => copyCode(project.project_code)}
                      className="ml-2 text-gray-400 hover:text-white transition"
                      title="Копировать код"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                  project.is_active ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'
                }`}>
                  {project.is_active ? 'Активен' : 'Архив'}
                </span>
              </div>

              {project.description && (
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{project.description}</p>
              )}

              <div className="flex items-center justify-between text-sm text-gray-500 mb-2">
                <span>Отчётов: {project.report_count}</span>
                <span>{new Date(project.created_at).toLocaleDateString('ru-RU')}</span>
              </div>

              {/* User access count */}
              <div className="flex items-center justify-between text-sm mb-4">
                {project.manager_name && (
                  <span className="text-gray-400">
                    РПУ: {project.manager_name}
                  </span>
                )}
                <button
                  onClick={() => handleOpenAccessModal(project)}
                  className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded bg-gray-700 text-gray-300 hover:bg-gray-600 transition ml-auto"
                  title="Настроить доступы пользователей"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                  {projectUserCounts[project.id] !== undefined ? (
                    <span>{projectUserCounts[project.id]} чел.</span>
                  ) : (
                    <span className="w-6 h-3 bg-gray-600 rounded animate-pulse"></span>
                  )}
                </button>
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t border-gray-700">
                <button
                  onClick={() => handleOpenAccessModal(project)}
                  className="px-3 py-1.5 text-sm text-green-400 hover:text-green-300 hover:bg-gray-700 rounded transition"
                >
                  Доступы
                </button>
                <button
                  onClick={() => handleEdit(project)}
                  className="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition"
                >
                  Изменить
                </button>
                {project.is_active ? (
                  <button
                    onClick={() => handleArchive(project)}
                    className="px-3 py-1.5 text-sm text-yellow-400 hover:text-yellow-300 hover:bg-gray-700 rounded transition"
                  >
                    Архив
                  </button>
                ) : (
                  <button
                    onClick={() => handleDelete(project)}
                    className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-gray-700 rounded transition"
                  >
                    Удалить
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Project Modal */}
      <ProjectModal
        isOpen={modalOpen}
        project={editingProject}
        users={users}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
      />

      {/* User Access Modal */}
      <UserAccessModal
        isOpen={accessModalOpen}
        project={accessProject}
        allUsers={users}
        onClose={() => {
          setAccessModalOpen(false);
          setAccessProject(null);
        }}
        onSave={handleSaveUserAccess}
      />
    </div>
  );
}
