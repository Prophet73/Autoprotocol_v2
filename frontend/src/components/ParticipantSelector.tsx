import { useState, useEffect } from 'react';
import { Users, ChevronDown, ChevronRight, Check, Loader2, Plus, X, Building2, UserPlus } from 'lucide-react';
import {
  getProjectContractors,
  getStandardRoles,
  createProjectContractor,
  addPersonToOrganization,
  type Contractor,
  type StandardRole,
} from '../api/client';

interface ParticipantSelectorProps {
  projectCode: string;
  selectedPersonIds: number[];
  onChange: (personIds: number[]) => void;
}

export function ParticipantSelector({
  projectCode,
  selectedPersonIds,
  onChange,
}: ParticipantSelectorProps) {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [roles, setRoles] = useState<StandardRole[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedOrgs, setExpandedOrgs] = useState<Set<number>>(new Set());

  // Section collapsed state
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Forms state
  const [showAddOrgForm, setShowAddOrgForm] = useState(false);
  const [addingPersonToOrgId, setAddingPersonToOrgId] = useState<number | null>(null);

  // New organization form
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgRole, setNewOrgRole] = useState('');
  const [isAddingOrg, setIsAddingOrg] = useState(false);

  // New person form
  const [newPersonName, setNewPersonName] = useState('');
  const [newPersonPosition, setNewPersonPosition] = useState('');
  const [isAddingPerson, setIsAddingPerson] = useState(false);

  // Load contractors and roles when project code changes
  useEffect(() => {
    if (projectCode.length === 4) {
      setIsLoading(true);
      Promise.all([
        getProjectContractors(projectCode),
        getStandardRoles(),
      ])
        .then(([contractorsData, rolesData]) => {
          setContractors(contractorsData);
          setRoles(rolesData);
          // Auto-expand all organizations
          setExpandedOrgs(new Set(contractorsData.map((c) => c.organization_id)));
        })
        .catch(() => {
          setContractors([]);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setContractors([]);
    }
  }, [projectCode]);

  const toggleOrg = (orgId: number) => {
    const newExpanded = new Set(expandedOrgs);
    if (newExpanded.has(orgId)) {
      newExpanded.delete(orgId);
    } else {
      newExpanded.add(orgId);
    }
    setExpandedOrgs(newExpanded);
  };

  const togglePerson = (personId: number) => {
    const newSelected = selectedPersonIds.includes(personId)
      ? selectedPersonIds.filter((id) => id !== personId)
      : [...selectedPersonIds, personId];
    onChange(newSelected);
  };

  const toggleAllInOrg = (contractor: Contractor) => {
    const orgPersonIds = contractor.persons.map((p) => p.id);
    const allSelected = orgPersonIds.every((id) => selectedPersonIds.includes(id));

    if (allSelected) {
      // Deselect all in org
      onChange(selectedPersonIds.filter((id) => !orgPersonIds.includes(id)));
    } else {
      // Select all in org
      const newSelected = [...selectedPersonIds];
      orgPersonIds.forEach((id) => {
        if (!newSelected.includes(id)) {
          newSelected.push(id);
        }
      });
      onChange(newSelected);
    }
  };

  const handleAddOrganization = async () => {
    if (!newOrgName.trim() || !newOrgRole) return;

    setIsAddingOrg(true);
    try {
      const newContractor = await createProjectContractor(projectCode, {
        organization_name: newOrgName.trim(),
        role: newOrgRole,
      });
      setContractors([...contractors, newContractor]);
      setExpandedOrgs(new Set([...expandedOrgs, newContractor.organization_id]));
      setNewOrgName('');
      setNewOrgRole('');
      setShowAddOrgForm(false);
    } catch (error) {
      console.error('Failed to add organization:', error);
    } finally {
      setIsAddingOrg(false);
    }
  };

  const handleAddPerson = async (organizationId: number) => {
    if (!newPersonName.trim()) return;

    setIsAddingPerson(true);
    try {
      const newPerson = await addPersonToOrganization(organizationId, {
        full_name: newPersonName.trim(),
        position: newPersonPosition.trim() || undefined,
      });

      // Update contractors list with new person
      setContractors(
        contractors.map((c) => {
          if (c.organization_id === organizationId) {
            return {
              ...c,
              persons: [...c.persons, newPerson],
            };
          }
          return c;
        })
      );

      // Auto-select the new person
      onChange([...selectedPersonIds, newPerson.id]);

      setNewPersonName('');
      setNewPersonPosition('');
      setAddingPersonToOrgId(null);
    } catch (error) {
      console.error('Failed to add person:', error);
    } finally {
      setIsAddingPerson(false);
    }
  };

  if (!projectCode || projectCode.length < 4) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm py-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        Загрузка участников...
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Collapsible header */}
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
          <Users className="w-4 h-4" />
          <span>Участники совещания</span>
          {selectedPersonIds.length > 0 && (
            <span className="bg-severin-red text-white px-2 py-0.5 rounded-full text-xs">
              {selectedPersonIds.length}
            </span>
          )}
          {isCollapsed && contractors.length > 0 && (
            <span className="text-xs text-slate-400">
              ({contractors.length} орг.)
            </span>
          )}
        </button>
        {!isCollapsed && !showAddOrgForm && (
          <button
            type="button"
            onClick={() => setShowAddOrgForm(true)}
            className="flex items-center gap-1 text-xs text-severin-red hover:text-severin-red-dark"
          >
            <Plus className="w-3 h-3" />
            Добавить организацию
          </button>
        )}
      </div>

      {/* Collapsed state - show nothing below header */}
      {isCollapsed ? null : (
        <>

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
              onClick={() => {
                setShowAddOrgForm(false);
                setNewOrgName('');
                setNewOrgRole('');
              }}
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
            {isAddingOrg ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Добавить
          </button>
        </div>
      )}

      {/* Contractors list or empty state */}
      {contractors.length === 0 && !showAddOrgForm ? (
        <div className="text-slate-500 text-sm py-4 text-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
          <Users className="w-6 h-6 mx-auto mb-2 text-slate-400" />
          <p>Участники не настроены</p>
          <button
            type="button"
            onClick={() => setShowAddOrgForm(true)}
            className="mt-2 text-severin-red hover:text-severin-red-dark text-sm font-medium"
          >
            + Добавить организацию
          </button>
        </div>
      ) : contractors.length > 0 ? (
        <div className="border border-slate-200 rounded-lg overflow-hidden max-h-64 overflow-y-auto">
          {contractors.map((contractor) => {
            const isExpanded = expandedOrgs.has(contractor.organization_id);
            const orgPersonIds = contractor.persons.map((p) => p.id);
            const selectedCount = orgPersonIds.filter((id) =>
              selectedPersonIds.includes(id)
            ).length;
            const allSelected = selectedCount === orgPersonIds.length && orgPersonIds.length > 0;

            return (
              <div key={contractor.id} className="border-b border-slate-100 last:border-b-0">
                {/* Organization header */}
                <div
                  className="flex items-center gap-2 px-3 py-2 bg-slate-50 cursor-pointer hover:bg-slate-100"
                  onClick={() => toggleOrg(contractor.organization_id)}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}

                  <div
                    className={`w-4 h-4 rounded border flex items-center justify-center cursor-pointer ${
                      allSelected
                        ? 'bg-severin-red border-severin-red'
                        : selectedCount > 0
                        ? 'bg-severin-red/30 border-severin-red'
                        : 'border-slate-300'
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAllInOrg(contractor);
                    }}
                  >
                    {allSelected && <Check className="w-3 h-3 text-white" />}
                  </div>

                  <span className="font-medium text-sm flex-1">
                    {contractor.organization_name}
                  </span>
                  <span className="text-xs text-slate-500 bg-slate-200 px-2 py-0.5 rounded">
                    {contractor.role_label}
                  </span>
                  {selectedCount > 0 && (
                    <span className="text-xs text-severin-red">
                      {selectedCount}/{contractor.persons.length}
                    </span>
                  )}
                </div>

                {/* Persons list */}
                {isExpanded && (
                  <div className="bg-white">
                    {contractor.persons.map((person) => {
                      const isSelected = selectedPersonIds.includes(person.id);
                      return (
                        <div
                          key={person.id}
                          className="flex items-center gap-3 px-3 py-1.5 pl-10 hover:bg-slate-50 cursor-pointer"
                          onClick={() => togglePerson(person.id)}
                        >
                          <div
                            className={`w-4 h-4 rounded border flex items-center justify-center ${
                              isSelected
                                ? 'bg-severin-red border-severin-red'
                                : 'border-slate-300'
                            }`}
                          >
                            {isSelected && <Check className="w-3 h-3 text-white" />}
                          </div>
                          <span className="text-sm flex-1">{person.full_name}</span>
                          {person.position && (
                            <span className="text-xs text-slate-400">
                              {person.position}
                            </span>
                          )}
                        </div>
                      );
                    })}

                    {/* Add person form */}
                    {addingPersonToOrgId === contractor.organization_id ? (
                      <div className="px-3 py-2 pl-10 bg-blue-50 border-t border-slate-100">
                        <div className="flex items-center gap-2 mb-2">
                          <UserPlus className="w-4 h-4 text-blue-600" />
                          <span className="text-xs text-blue-600 font-medium">Новый участник</span>
                          <button
                            type="button"
                            onClick={() => {
                              setAddingPersonToOrgId(null);
                              setNewPersonName('');
                              setNewPersonPosition('');
                            }}
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
                            onClick={(e) => e.stopPropagation()}
                          />
                          <input
                            type="text"
                            placeholder="Должность"
                            value={newPersonPosition}
                            onChange={(e) => setNewPersonPosition(e.target.value)}
                            className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-severin-red"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAddPerson(contractor.organization_id);
                            }}
                            disabled={!newPersonName.trim() || isAddingPerson}
                            className="px-2 py-1 text-xs bg-severin-red text-white rounded hover:bg-severin-red-dark disabled:bg-slate-300"
                          >
                            {isAddingPerson ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Check className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setAddingPersonToOrgId(contractor.organization_id);
                        }}
                        className="w-full px-3 py-1.5 pl-10 text-left text-xs text-severin-red hover:bg-red-50 border-t border-slate-100 flex items-center gap-1"
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
        </div>
      ) : null}
      </>
      )}
    </div>
  );
}
