/**
 * Business Domain Dashboard - Бизнес
 *
 * Meeting types: negotiation, strategic_planning, work_meeting, presentation, client_meeting
 */
import { Briefcase, Handshake, Target, Users, Presentation, UserCheck } from 'lucide-react';
import { DomainDashboard } from '../components/dashboard/DomainDashboard';
import type { MeetingTypeConfig } from '../components/dashboard/constants';

const BUSINESS_MEETING_TYPES: MeetingTypeConfig[] = [
  { id: 'negotiation', name: 'Переговоры', icon: Handshake, color: 'bg-indigo-100 text-indigo-600', hoverBorder: 'hover:border-indigo-300', hoverBg: 'hover:bg-indigo-50' },
  { id: 'strategic_planning', name: 'Стратегическое планирование', icon: Target, color: 'bg-violet-100 text-violet-600', hoverBorder: 'hover:border-violet-300', hoverBg: 'hover:bg-violet-50' },
  { id: 'work_meeting', name: 'Рабочее совещание', icon: Users, color: 'bg-blue-100 text-blue-600', hoverBorder: 'hover:border-blue-300', hoverBg: 'hover:bg-blue-50' },
  { id: 'presentation', name: 'Презентация', icon: Presentation, color: 'bg-amber-100 text-amber-600', hoverBorder: 'hover:border-amber-300', hoverBg: 'hover:bg-amber-50' },
  { id: 'client_meeting', name: 'Встреча с клиентом', icon: UserCheck, color: 'bg-green-100 text-green-600', hoverBorder: 'hover:border-green-300', hoverBg: 'hover:bg-green-50' },
];

export function BusinessDashboardPage() {
  return (
    <DomainDashboard
      domainId="business"
      title="Бизнес"
      headerIcon={Briefcase}
      accentColor="indigo"
      meetingTypes={BUSINESS_MEETING_TYPES}
      meetingGridCols={5}
    />
  );
}

export default BusinessDashboardPage;
