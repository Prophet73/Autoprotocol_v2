/**
 * CEO Domain Dashboard — Руководитель
 *
 * Meeting types: notech (НОТЕХ — рабочие совещания ассоциации НОТЕХ)
 */
import { Landmark } from 'lucide-react';
import { DomainDashboard } from '../components/dashboard/DomainDashboard';
import { CEODetailModal } from '../components/dashboard/CEODetailModal';
import type { MeetingTypeConfig } from '../components/dashboard/constants';

const CEO_MEETING_TYPES: MeetingTypeConfig[] = [
  { id: 'notech', name: 'НОТЕХ', icon: Landmark, color: 'bg-purple-100 text-purple-600', hoverBorder: 'hover:border-purple-300', hoverBg: 'hover:bg-purple-50' },
];

export function CEODashboardPage() {
  return (
    <DomainDashboard
      domainId="ceo"
      title="Дашборд руководителя"
      headerIcon={Landmark}
      accentColor="purple"
      meetingTypes={CEO_MEETING_TYPES}
      meetingGridCols={3}
      calendarEventTitle="НОТЕХ"
      DetailModal={CEODetailModal}
    />
  );
}

export default CEODashboardPage;
