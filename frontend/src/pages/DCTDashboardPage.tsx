/**
 * DCT Domain Dashboard - Департамент Цифровой Трансформации
 *
 * Meeting types: brainstorm, production, negotiation, lecture
 */
import { Monitor, Lightbulb, Factory, Handshake, GraduationCap } from 'lucide-react';
import { DomainDashboard } from '../components/dashboard/DomainDashboard';
import type { MeetingTypeConfig } from '../components/dashboard/constants';

const DCT_MEETING_TYPES: MeetingTypeConfig[] = [
  { id: 'brainstorm', name: 'Мозговой штурм', icon: Lightbulb, color: 'bg-yellow-100 text-yellow-600', hoverBorder: 'hover:border-yellow-300', hoverBg: 'hover:bg-yellow-50' },
  { id: 'production', name: 'Производственное совещание', icon: Factory, color: 'bg-blue-100 text-blue-600', hoverBorder: 'hover:border-blue-300', hoverBg: 'hover:bg-blue-50' },
  { id: 'negotiation', name: 'Переговоры с контрагентом', icon: Handshake, color: 'bg-green-100 text-green-600', hoverBorder: 'hover:border-green-300', hoverBg: 'hover:bg-green-50' },
  { id: 'lecture', name: 'Лекция/Вебинар', icon: GraduationCap, color: 'bg-purple-100 text-purple-600', hoverBorder: 'hover:border-purple-300', hoverBg: 'hover:bg-purple-50' },
];

export function DCTDashboardPage() {
  return (
    <DomainDashboard
      domainId="dct"
      title="Цифровая трансформация"
      headerIcon={Monitor}
      accentColor="blue"
      meetingTypes={DCT_MEETING_TYPES}
    />
  );
}

export default DCTDashboardPage;
