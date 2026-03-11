import { useState, useEffect, useRef } from 'react';
import {
  X, Users, Building2, ChevronDown, ChevronRight, Check, Loader2,
  Plus, UserPlus, Pencil, Trash2,
} from 'lucide-react';
import { useFocusTrap } from '../hooks/useFocusTrap';
import {
  getProjectContractors,
  getStandardRoles,
  createProjectContractor,
  addPersonToOrganization,
  updatePerson,
  deletePerson,
  updateOrganization,
  deleteContractor,
  type Contractor,
  type StandardRole,
  type Person,
} from '../api/client';

interface ParticipantModalProps {
  projectCode: string;
  selectedPersonIds: number[];
  onChange: (personIds: number[]) => void;
  onClose: () => void;
}

export function ParticipantModal({
  projectCode,
  selectedPersonIds,
  onChange,
  onClose,
}: ParticipantModalProps) {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [roles, setRoles] = useState<StandardRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedOrgs, setExpandedOrgs] = useState<Set<number>>(new Set());

  // Local copy of selected IDs (commit on close)
  const [localSelected, setLocalSelected] = useState<number[]>(selectedPersonIds);

  // Add organization form
  const [showAddOrgForm, setShowAddOrgForm] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgRole, setNewOrgRole] = useState('');
  const [isAddingOrg, setIsAddingOrg] = useState(false);

  // Add person form (per org)
  const [addingPersonToOrgId, setAddingPersonToOrgId] = useState<number | null>(null);
  const [newPersonName, setNewPersonName] = useState('');
  const [newPersonPosition, setNewPersonPosition] = useState('');
  const [isAddingPerson, setIsAddingPerson] = useState(false);

  // Inline edit state
  const [editingPersonId, setEditingPersonId] = useState<number | null>(null);
  const [editPersonName, setEditPersonName] = useState('');
  const [editPersonPosition, setEditPersonPosition] = useState('');
  const [isSavingPerson, setIsSavingPerson] = useState(false);

  const [editingOrgId, setEditingOrgId] = useState<number | null>(null);
  const [editOrgName, setEditOrgName] = useState('');
  const [isSavingOrg, setIsSavingOrg] = useState(false);

  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef);

  // Load data
  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      getProjectContractors(projectCode),
      getStandardRoles(),
    ])
      .then(([contractorsData, rolesData]) => {
        setContractors(contractorsData);
        setRoles(rolesData);
        setExpandedOrgs(new Set(contractorsData.map((c) => c.organization_id)));
      })
      .catch(() => setContractors([]))
      .finally(() => setIsLoading(false));
  }, [projectCode]);

  // Close on backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
      handleDone();
    }
  };

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleDone();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [localSelected]);

  const handleDone = () => {
    onChange(localSelected);
    onClose();
  };

  // Toggle helpers
  const toggleOrg = (orgId: number) => {
    const next = new Set(expandedOrgs);
    next.has(orgId) ? next.delete(orgId) : next.add(orgId);
    setExpandedOrgs(next);
  };

  const togglePerson = (personId: number) => {
    setLocalSelected((prev) =>
      prev.includes(personId) ? prev.filter((id) => id !== personId) : [...prev, personId]
    );
  };

  const toggleAllInOrg = (contractor: Contractor) => {
    const orgIds = contractor.persons.map((p) => p.id);
    const allSelected = orgIds.every((id) => localSelected.includes(id));
    if (allSelected) {
      setLocalSelected((prev) => prev.filter((id) => !orgIds.includes(id)));
    } else {
      setLocalSelected((prev) => {
        const next = [...prev];
        orgIds.forEach((id) => { if (!next.includes(id)) next.push(id); });
        return next;
      });
    }
  };

  // Add organization
  const handleAddOrganization = async () => {
    if (!newOrgName.trim() || !newOrgRole) return;
    setIsAddingOrg(true);
    try {
      const newContractor = await createProjectContractor(projectCode, {
        organization_name: newOrgName.trim(),
        role: newOrgRole,
      });
      setContractors((prev) => [...prev, newContractor]);
      setExpandedOrgs((prev) => new Set([...prev, newContractor.organization_id]));
      setNewOrgName('');
      setNewOrgRole('');
      setShowAddOrgForm(false);
    } catch (error) {
      console.error('Failed to add organization:', error);
    } finally {
      setIsAddingOrg(false);
    }
  };

  // Add person
  const handleAddPerson = async (organizationId: number) => {
    if (!newPersonName.trim()) return;
    setIsAddingPerson(true);
    try {
      const newPerson = await addPersonToOrganization(organizationId, {
        full_name: newPersonName.trim(),
        position: newPersonPosition.trim() || undefined,
      });
      setContractors((prev) =>
        prev.map((c) =>
          c.organization_id === organizationId
            ? { ...c, persons: [...c.persons, newPerson] }
            : c
        )
      );
      setLocalSelected((prev) => [...prev, newPerson.id]);
      setNewPersonName('');
      setNewPersonPosition('');
      setAddingPersonToOrgId(null);
    } catch (error) {
      console.error('Failed to add person:', error);
    } finally {
      setIsAddingPerson(false);
    }
  };

  // Edit person
  const startEditPerson = (person: Person) => {
    setEditingPersonId(person.id);
    setEditPersonName(person.full_name);
    setEditPersonPosition(person.position || '');
  };

  const saveEditPerson = async () => {
    if (!editingPersonId || !editPersonName.trim()) return;
    setIsSavingPerson(true);
    try {
      const updated = await updatePerson(editingPersonId, {
        full_name: editPersonName.trim(),
        position: editPersonPosition.trim(),
      });
      setContractors((prev) =>
        prev.map((c) => ({
          ...c,
          persons: c.persons.map((p) =>
            p.id === editingPersonId ? { ...p, full_name: updated.full_name, position: updated.position } : p
          ),
        }))
      );
      setEditingPersonId(null);
    } catch (error) {
      console.error('Failed to update person:', error);
      alert('Ошибка сохранения');
    } finally {
      setIsSavingPerson(false);
    }
  };

  // Delete person
  const handleDeletePerson = async (personId: number) => {
    try {
      await deletePerson(personId);
      setContractors((prev) =>
        prev.map((c) => ({
          ...c,
          persons: c.persons.filter((p) => p.id !== personId),
        }))
      );
      setLocalSelected((prev) => prev.filter((id) => id !== personId));
    } catch (error) {
      console.error('Failed to delete person:', error);
    }
  };

  // Edit organization
  const startEditOrg = (orgId: number, currentName: string) => {
    setEditingOrgId(orgId);
    setEditOrgName(currentName);
  };

  const saveEditOrg = async () => {
    if (!editingOrgId || !editOrgName.trim()) return;
    setIsSavingOrg(true);
    try {
      await updateOrganization(editingOrgId, { name: editOrgName.trim() });
      setContractors((prev) =>
        prev.map((c) =>
          c.organization_id === editingOrgId
            ? { ...c, organization_name: editOrgName.trim() }
            : c
        )
      );
      setEditingOrgId(null);
    } catch (error) {
      console.error('Failed to update organization:', error);
      alert('Ошибка сохранения');
    } finally {
      setIsSavingOrg(false);
    }
  };

  // Delete contractor
  const handleDeleteContractor = async (contractorId: number, orgPersonIds: number[]) => {
    try {
      await deleteContractor(projectCode, contractorId);
      setContractors((prev) => prev.filter((c) => c.id !== contractorId));
      setLocalSelected((prev) => prev.filter((id) => !orgPersonIds.includes(id)));
    } catch (error) {
      console.error('Failed to delete contractor:', error);
    }
  };

  // Summary text
  const selectedSummary = () => {
    const parts: string[] = [];
    for (const c of contractors) {
      const count = c.persons.filter((p) => localSelected.includes(p.id)).length;
      if (count > 0) parts.push(`${c.organization_name} (${count})`);
    }
    return parts.join(', ') || 'Никто не выбран';
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-red-50/30">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-severin-red" />
            <h2 className="text-lg font-semibold text-slate-800">Управление участниками</h2>
            {localSelected.length > 0 && (
              <span className="bg-severin-red text-white px-2 py-0.5 rounded-full text-xs font-medium">
                {localSelected.length}
              </span>
            )}
          </div>
          <button onClick={handleDone} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
              <span className="ml-2 text-slate-500">Загрузка участников...</span>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Contractors list */}
              {contractors.map((contractor) => {
                const isExpanded = expandedOrgs.has(contractor.organization_id);
                const orgPersonIds = contractor.persons.map((p) => p.id);
                const selectedCount = orgPersonIds.filter((id) => localSelected.includes(id)).length;
                const allSelected = selectedCount === orgPersonIds.length && orgPersonIds.length > 0;

                return (
                  <div key={contractor.id} className="border border-slate-200 rounded-lg overflow-hidden">
                    {/* Organization header */}
                    <div className="flex items-center gap-2 px-3 py-2.5 bg-slate-50 hover:bg-slate-100">
                      <button type="button" onClick={() => toggleOrg(contractor.organization_id)} className="flex-shrink-0">
                        {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                      </button>

                      {/* Org checkbox */}
                      <div
                        className={`w-4 h-4 rounded border flex items-center justify-center cursor-pointer flex-shrink-0 ${
                          allSelected ? 'bg-severin-red border-severin-red' :
                          selectedCount > 0 ? 'bg-severin-red/30 border-severin-red' :
                          'border-slate-300'
                        }`}
                        onClick={() => toggleAllInOrg(contractor)}
                      >
                        {allSelected && <Check className="w-3 h-3 text-white" />}
                      </div>

                      {/* Org name (editable) */}
                      {editingOrgId === contractor.organization_id ? (
                        <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            value={editOrgName}
                            onChange={(e) => setEditOrgName(e.target.value)}
                            className="flex-1 px-2 py-0.5 text-sm border border-severin-red rounded focus:outline-none"
                            autoFocus
                            onKeyDown={(e) => { if (e.key === 'Enter') saveEditOrg(); if (e.key === 'Escape') setEditingOrgId(null); }}
                          />
                          <button onClick={saveEditOrg} disabled={isSavingOrg} className="text-severin-red hover:text-severin-red-dark">
                            {isSavingOrg ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => setEditingOrgId(null)} className="text-slate-400 hover:text-slate-600">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span
                          className="font-medium text-sm flex-1 cursor-pointer"
                          onClick={() => toggleOrg(contractor.organization_id)}
                        >
                          {contractor.organization_name}
                        </span>
                      )}

                      <span className="text-xs text-slate-500 bg-slate-200 px-2 py-0.5 rounded flex-shrink-0">
                        {contractor.role_label}
                      </span>

                      {selectedCount > 0 && (
                        <span className="text-xs text-severin-red flex-shrink-0">
                          {selectedCount}/{contractor.persons.length}
                        </span>
                      )}

                      {/* Org action buttons */}
                      {editingOrgId !== contractor.organization_id && (
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); startEditOrg(contractor.organization_id, contractor.organization_name); }}
                            className="text-slate-400 hover:text-slate-600 p-0.5"
                            title="Переименовать"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); handleDeleteContractor(contractor.id, orgPersonIds); }}
                            className="text-slate-400 hover:text-red-500 p-0.5"
                            title="Удалить из проекта"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Persons list */}
                    {isExpanded && (
                      <div className="bg-white divide-y divide-slate-50">
                        {contractor.persons.map((person) => {
                          const isSelected = localSelected.includes(person.id);
                          const isEditing = editingPersonId === person.id;

                          if (isEditing) {
                            return (
                              <div key={person.id} className="flex items-center gap-2 px-3 py-2 pl-10 bg-amber-50">
                                <input
                                  type="text"
                                  value={editPersonName}
                                  onChange={(e) => setEditPersonName(e.target.value)}
                                  placeholder="ФИО"
                                  className="flex-1 px-2 py-1 text-sm border border-amber-300 rounded focus:outline-none focus:ring-1 focus:ring-severin-red"
                                  autoFocus
                                  onKeyDown={(e) => { if (e.key === 'Enter') saveEditPerson(); if (e.key === 'Escape') setEditingPersonId(null); }}
                                />
                                <input
                                  type="text"
                                  value={editPersonPosition}
                                  onChange={(e) => setEditPersonPosition(e.target.value)}
                                  placeholder="Должность"
                                  className="w-36 px-2 py-1 text-sm border border-amber-300 rounded focus:outline-none focus:ring-1 focus:ring-severin-red"
                                  onKeyDown={(e) => { if (e.key === 'Enter') saveEditPerson(); if (e.key === 'Escape') setEditingPersonId(null); }}
                                />
                                <button onClick={saveEditPerson} disabled={isSavingPerson} className="text-severin-red hover:text-severin-red-dark">
                                  {isSavingPerson ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                                </button>
                                <button onClick={() => setEditingPersonId(null)} className="text-slate-400 hover:text-slate-600">
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            );
                          }

                          return (
                            <div
                              key={person.id}
                              className="flex items-center gap-3 px-3 py-1.5 pl-10 hover:bg-slate-50 group"
                            >
                              <div
                                className={`w-4 h-4 rounded border flex items-center justify-center cursor-pointer flex-shrink-0 ${
                                  isSelected ? 'bg-severin-red border-severin-red' : 'border-slate-300'
                                }`}
                                onClick={() => togglePerson(person.id)}
                              >
                                {isSelected && <Check className="w-3 h-3 text-white" />}
                              </div>
                              <span
                                className="text-sm flex-1 cursor-pointer"
                                onClick={() => togglePerson(person.id)}
                              >
                                {person.full_name}
                              </span>
                              {person.position && (
                                <span className="text-xs text-slate-400 flex-shrink-0">{person.position}</span>
                              )}
                              {/* Edit/delete buttons - visible on hover */}
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                <button
                                  type="button"
                                  onClick={(e) => { e.stopPropagation(); startEditPerson(person); }}
                                  className="text-slate-400 hover:text-slate-600 p-0.5"
                                  title="Редактировать"
                                >
                                  <Pencil className="w-3 h-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => { e.stopPropagation(); handleDeletePerson(person.id); }}
                                  className="text-slate-400 hover:text-red-500 p-0.5"
                                  title="Удалить"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          );
                        })}

                        {/* Add person form */}
                        {addingPersonToOrgId === contractor.organization_id ? (
                          <div className="px-3 py-2 pl-10 bg-blue-50">
                            <div className="flex items-center gap-2 mb-2">
                              <UserPlus className="w-4 h-4 text-blue-600" />
                              <span className="text-xs text-blue-600 font-medium">Новый участник</span>
                              <button
                                type="button"
                                onClick={() => { setAddingPersonToOrgId(null); setNewPersonName(''); setNewPersonPosition(''); }}
                                className="ml-auto text-slate-400 hover:text-slate-600"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                            <div className="flex gap-2">
                              <input
                                type="text"
                                placeholder="ФИО"
                                value={newPersonName}
                                onChange={(e) => setNewPersonName(e.target.value)}
                                className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-severin-red"
                                autoFocus
                                onKeyDown={(e) => { if (e.key === 'Enter') handleAddPerson(contractor.organization_id); }}
                              />
                              <input
                                type="text"
                                placeholder="Должность"
                                value={newPersonPosition}
                                onChange={(e) => setNewPersonPosition(e.target.value)}
                                className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-severin-red"
                                onKeyDown={(e) => { if (e.key === 'Enter') handleAddPerson(contractor.organization_id); }}
                              />
                              <button
                                type="button"
                                onClick={() => handleAddPerson(contractor.organization_id)}
                                disabled={!newPersonName.trim() || isAddingPerson}
                                className="px-2 py-1 text-xs bg-severin-red text-white rounded hover:bg-severin-red-dark disabled:bg-slate-300"
                              >
                                {isAddingPerson ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setAddingPersonToOrgId(contractor.organization_id)}
                            className="w-full px-3 py-1.5 pl-10 text-left text-xs text-severin-red hover:bg-red-50 flex items-center gap-1"
                          >
                            <Plus className="w-3 h-3" />
                            Добавить участника
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Empty state */}
              {contractors.length === 0 && !showAddOrgForm && (
                <div className="text-slate-500 text-sm py-8 text-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
                  <Users className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                  <p>Участники не настроены</p>
                  <button
                    type="button"
                    onClick={() => setShowAddOrgForm(true)}
                    className="mt-2 text-severin-red hover:text-severin-red-dark text-sm font-medium"
                  >
                    + Добавить организацию
                  </button>
                </div>
              )}

              {/* Add organization form */}
              {showAddOrgForm && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                      <Building2 className="w-4 h-4" />
                      Новая организация
                    </div>
                    <button
                      type="button"
                      onClick={() => { setShowAddOrgForm(false); setNewOrgName(''); setNewOrgRole(''); }}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="Название организации"
                    value={newOrgName}
                    onChange={(e) => setNewOrgName(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
                    autoFocus
                  />
                  <select
                    value={newOrgRole}
                    onChange={(e) => setNewOrgRole(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
                  >
                    <option value="">Выберите роль...</option>
                    {roles.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddOrganization}
                    disabled={!newOrgName.trim() || !newOrgRole || isAddingOrg}
                    className="w-full py-1.5 text-sm bg-severin-red text-white rounded hover:bg-severin-red-dark disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isAddingOrg ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Добавить
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="text-sm text-slate-500 truncate max-w-md">
            {selectedSummary()}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {!showAddOrgForm && (
              <button
                type="button"
                onClick={() => setShowAddOrgForm(true)}
                className="px-3 py-1.5 text-sm text-severin-red border border-severin-red rounded-lg hover:bg-red-50 flex items-center gap-1"
              >
                <Building2 className="w-3.5 h-3.5" />
                Добавить организацию
              </button>
            )}
            <button
              type="button"
              onClick={handleDone}
              className="px-5 py-1.5 text-sm bg-severin-red text-white rounded-lg hover:bg-severin-red-dark font-medium"
            >
              Готово
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
