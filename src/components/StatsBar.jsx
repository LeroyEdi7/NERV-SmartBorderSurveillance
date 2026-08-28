import { AlertTriangle, Car, Footprints, ShieldCheck } from 'lucide-react';
import './StatsBar.css';

const STATS = [
  {
    id:    'high-alerts',
    icon:  <AlertTriangle size={16} />,
    label: 'High Alerts',
    value: 6,
    color: '#e14b3c',
  },
  {
    id:    'vehicles',
    icon:  <Car size={16} />,
    label: 'Vehicles Detected',
    value: 42,
    color: '#4e9fe8',
  },
  {
    id:    'people',
    icon:  <Footprints size={16} />,
    label: 'People Detected',
    value: 89,
    color: '#34d9b4',
  },
  {
    id:    'uptime',
    icon:  <ShieldCheck size={16} />,
    label: 'System Uptime',
    value: '99.8%',
    color: '#34d9b4',
    isPercent: true,
  },
];

export default function StatsBar() {
  return (
    <div className="stats-bar" role="region" aria-label="System statistics">
      {STATS.map((stat) => (
        <div key={stat.id} className="stats-bar__card" id={`stat-${stat.id}`}>
          {/* Icon + value */}
          <div className="stats-bar__main">
            <span className="stats-bar__icon" aria-hidden="true">{stat.icon}</span>
            <span className="stats-bar__value" style={{ color: stat.color }}>
              {stat.value}
            </span>
          </div>

          {/* Label */}
          <span className="stats-bar__label">{stat.label}</span>
        </div>
      ))}
    </div>
  );
}
