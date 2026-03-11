import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import type { ChartData } from 'chart.js';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export function PulseChart({ pulseChartData }: { pulseChartData: ChartData<'bar'> }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
      <h3 className="font-semibold text-slate-800 mb-4">Пульс проекта</h3>
      <div style={{ height: 350 }}>
        <Bar
          data={pulseChartData}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'top' },
            },
            scales: {
              x: { stacked: true },
              y: { stacked: true },
            },
          }}
        />
      </div>
    </div>
  );
}
