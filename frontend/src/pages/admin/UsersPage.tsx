import { useEffect, useState } from 'react';
import { usersApi, projectsApi } from '../../api/adminApi';
import type { User, CreateUserRequest, Project } from '../../api/adminApi';

interface UserModalProps {
  isOpen: boolean;
  user: User | null;
  onClose: () => void;
  onSave: (data: CreateUserRequest | Partial<User>) => void;
}

function UserModal({ isOpen, user, onClose, onSave }: UserModalProps) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'user',
    domain: '',
    is_superuser: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setFormData({
        email: user.email,
        password: '',
        full_name: user.full_name || '',
        role: user.role,
        domain: user.domain || '',
        is_superuser: user.is_superuser,
      });
    } else {
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'user',
        domain: '',
        is_superuser: false,
      });
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (user) {
        // Update - don't send password if empty
        const updateData: Partial<User> = {
          email: formData.email,
          full_name: formData.full_name || null,
          role: formData.role,
          domain: formData.domain || null,
          is_superuser: formData.is_superuser,
        };
        await onSave(updateData);
      } else {
        // Create
        await onSave(formData);
      }
      onClose();
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
          {user ? 'Редактировать пользователя' : 'Создать пользователя'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {!user && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Пароль</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Полное имя</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Роль</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="manager">Manager</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Домен</label>
            <select
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Без домена</option>
              <option value="construction">Строительство</option>
              <option value="hr">HR</option>
              <option value="it">IT</option>
              <option value="general">Общий</option>
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_superuser"
              checked={formData.is_superuser}
              onChange={(e) => setFormData({ ...formData, is_superuser: e.target.checked })}
              className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
            />
            <label htmlFor="is_superuser" className="ml-2 text-sm text-gray-300">
              Суперпользователь
            </label>
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
// Project Access Modal
// ============================================================================

interface ProjectAccessModalProps {
  isOpen: boolean;
  user: User | null;
  projects: Project[];
  onClose: () => void;
  onSave: (userId: number, projectIds: number[]) => Promise<void>;
}

function ProjectAccessModal({ isOpen, user, projects, onClose, onSave }: ProjectAccessModalProps) {
  const [selectedProjects, setSelectedProjects] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (isOpen && user) {
      loadUserProjects();
    }
  }, [isOpen, user]);

  const loadUserProjects = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const response = await usersApi.getUserProjects(user.id);
      setSelectedProjects(new Set(response.project_ids));
    } catch (err) {
      console.error('Error loading user projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleProject = (projectId: number) => {
    setSelectedProjects(prev => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedProjects(new Set(filteredProjects.map(p => p.id)));
  };

  const selectNone = () => {
    setSelectedProjects(new Set());
  };

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    try {
      await onSave(user.id, Array.from(selectedProjects));
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка сохранения доступов');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen || !user) return null;

  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.project_code.includes(search)
  );

  // Sort: selected first, then by name
  const sortedProjects = [...filteredProjects].sort((a, b) => {
    const aSelected = selectedProjects.has(a.id);
    const bSelected = selectedProjects.has(b.id);
    if (aSelected && !bSelected) return -1;
    if (!aSelected && bSelected) return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-white">Доступ к проектам</h2>
            <p className="text-gray-400 text-sm mt-1">
              {user.full_name || user.email}
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
            placeholder="Поиск по названию или коду..."
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
            Выбрано: {selectedProjects.size} из {projects.length}
          </span>
        </div>

        {/* Project list */}
        <div className="flex-1 overflow-y-auto min-h-[200px] max-h-[400px] border border-gray-700 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : sortedProjects.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              Проекты не найдены
            </div>
          ) : (
            <div className="divide-y divide-gray-700">
              {sortedProjects.map((project) => (
                <label
                  key={project.id}
                  className={`flex items-center px-4 py-3 cursor-pointer transition ${
                    selectedProjects.has(project.id)
                      ? 'bg-blue-900/30'
                      : 'hover:bg-gray-700/50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedProjects.has(project.id)}
                    onChange={() => toggleProject(project.id)}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <div className="ml-3 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium truncate">
                        {project.name}
                      </span>
                      <span className={`px-1.5 py-0.5 text-xs rounded ${
                        project.is_active
                          ? 'bg-green-900/50 text-green-400'
                          : 'bg-gray-700 text-gray-400'
                      }`}>
                        {project.project_code}
                      </span>
                    </div>
                    {project.description && (
                      <p className="text-sm text-gray-400 truncate mt-0.5">
                        {project.description}
                      </p>
                    )}
                  </div>
                  {project.manager_name && (
                    <span className="text-xs text-gray-500 ml-2">
                      РПУ: {project.manager_name}
                    </span>
                  )}
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

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Project access modal
  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [accessUser, setAccessUser] = useState<User | null>(null);

  // Filters
  const [roleFilter, setRoleFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');

  useEffect(() => {
    loadUsers();
    loadProjects();
  }, [roleFilter, domainFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await usersApi.list({
        role: roleFilter || undefined,
        domain: domainFilter || undefined,
        limit: 100,
      });
      setUsers(response.users);
      setTotal(response.total);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки пользователей');
    } finally {
      setLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const response = await projectsApi.list({ limit: 500 });
      setProjects(response.projects);
    } catch (err) {
      console.error('Error loading projects:', err);
    }
  };

  const handleCreate = () => {
    setEditingUser(null);
    setModalOpen(true);
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setModalOpen(true);
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Удалить пользователя ${user.email}?`)) return;

    try {
      await usersApi.delete(user.id);
      await loadUsers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleSave = async (data: CreateUserRequest | Partial<User>) => {
    if (editingUser) {
      await usersApi.update(editingUser.id, data);
    } else {
      await usersApi.create(data as CreateUserRequest);
    }
    await loadUsers();
  };

  const handleOpenAccessModal = (user: User) => {
    setAccessUser(user);
    setAccessModalOpen(true);
  };

  const handleSaveAccess = async (userId: number, projectIds: number[]) => {
    await usersApi.updateProjectAccess(userId, projectIds);
    // Update the count for this user
    setUserProjectCounts(prev => ({
      ...prev,
      [userId]: projectIds.length,
    }));
  };

  // Count projects for each user (for display)
  const [userProjectCounts, setUserProjectCounts] = useState<Record<number, number>>({});

  useEffect(() => {
    // Load project counts for all users
    const loadProjectCounts = async () => {
      const counts: Record<number, number> = {};
      for (const user of users) {
        try {
          const response = await usersApi.getUserProjects(user.id);
          counts[user.id] = response.project_ids.length;
        } catch {
          counts[user.id] = 0;
        }
      }
      setUserProjectCounts(counts);
    };

    if (users.length > 0 && users.length <= 50) {
      loadProjectCounts();
    }
  }, [users]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Пользователи</h1>
          <p className="text-gray-400 mt-1">Управление пользователями и доступами ({total})</p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center justify-center"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Создать
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Все роли</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
          <option value="manager">Manager</option>
          <option value="viewer">Viewer</option>
          <option value="superuser">Superuser</option>
        </select>

        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Все домены</option>
          <option value="construction">Строительство</option>
          <option value="hr">HR</option>
          <option value="it">IT</option>
          <option value="general">Общий</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <p>Пользователи не найдены</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Пользователь
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Роль
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Домен
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Проекты
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Статус
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Создан
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Действия
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center">
                          <span className="text-white font-medium">
                            {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-white">
                            {user.full_name || 'Без имени'}
                          </div>
                          <div className="text-sm text-gray-400">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        user.is_superuser ? 'bg-purple-900 text-purple-300' :
                        user.role === 'admin' ? 'bg-blue-900 text-blue-300' :
                        user.role === 'manager' ? 'bg-green-900 text-green-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {user.is_superuser ? 'Superuser' : user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {user.domain || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleOpenAccessModal(user)}
                        className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded bg-gray-700 text-gray-300 hover:bg-gray-600 transition"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        {userProjectCounts[user.id] !== undefined ? (
                          <span>{userProjectCounts[user.id]}</span>
                        ) : (
                          <span className="w-4 h-3 bg-gray-600 rounded animate-pulse"></span>
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        user.is_active ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {user.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                      {new Date(user.created_at).toLocaleDateString('ru-RU')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleOpenAccessModal(user)}
                        className="text-green-400 hover:text-green-300 mr-3"
                        title="Настроить доступ к проектам"
                      >
                        Доступы
                      </button>
                      <button
                        onClick={() => handleEdit(user)}
                        className="text-blue-400 hover:text-blue-300 mr-3"
                      >
                        Изменить
                      </button>
                      <button
                        onClick={() => handleDelete(user)}
                        className="text-red-400 hover:text-red-300"
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* User Modal */}
      <UserModal
        isOpen={modalOpen}
        user={editingUser}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
      />

      {/* Project Access Modal */}
      <ProjectAccessModal
        isOpen={accessModalOpen}
        user={accessUser}
        projects={projects}
        onClose={() => {
          setAccessModalOpen(false);
          setAccessUser(null);
        }}
        onSave={handleSaveAccess}
      />
    </div>
  );
}
