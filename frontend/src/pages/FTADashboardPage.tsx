/**
 * FTA Domain Dashboard - ДФТА
 *
 * Meeting types: audit
 */
import { FileCheck, ClipboardCheck } from 'lucide-react';
import { DomainDashboard } from '../components/dashboard/DomainDashboard';
import type { MeetingTypeConfig } from '../components/dashboard/constants';

const FTA_MEETING_TYPES: MeetingTypeConfig[] = [
  { id: 'audit', name: 'Аудит', icon: ClipboardCheck, color: 'bg-teal-100 text-teal-600', hoverBorder: 'hover:border-teal-300', hoverBg: 'hover:bg-teal-50' },
];

export function FTADashboardPage() {
  return (
    <DomainDashboard
      domainId="fta"
      title="ДФТА"
      headerIcon={FileCheck}
      accentColor="teal"
      meetingTypes={FTA_MEETING_TYPES}
    />
  );
}

export default FTADashboardPage;
