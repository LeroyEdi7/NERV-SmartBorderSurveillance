import { useEffect, useState } from 'react';
import { Moon, User, ChevronDown } from 'lucide-react';
import './StatusBar.css';

export default function StatusBar({ cameraCount, activeView = 'dashboard', onNavigate }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const hh = String(time.getHours()).padStart(2, '0');
  const mm = String(time.getMinutes()).padStart(2, '0');
  const ss = String(time.getSeconds()).padStart(2, '0');
  const dateStr = time.toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric'
  });

  return (
    <header className="status-bar">
      {/* Brand & Nav Tabs */}
      <div className="status-bar__brand">
        <span className="status-bar__mark" aria-hidden="true" />
        <span className="status-bar__title">Live Monitoring</span>

        {onNavigate && (
          <nav className="status-bar__nav-tabs">
            <button
              className={`status-bar__nav-btn ${activeView === 'dashboard' ? 'status-bar__nav-btn--active' : ''}`}
              onClick={() => onNavigate('dashboard')}
            >
              Live Dashboard
            </button>
            <button
              className={`status-bar__nav-btn ${activeView === 'alerts' ? 'status-bar__nav-btn--active' : ''}`}
              onClick={() => onNavigate('alerts')}
            >
              Active Alerts
            </button>
            <button
              className={`status-bar__nav-btn ${activeView === 'tracks' ? 'status-bar__nav-btn--active' : ''}`}
              onClick={() => onNavigate('tracks')}
            >
              Global Tracks
            </button>
          </nav>
        )}
      </div>

      {/* Center: system status + clock + date */}
      <div className="status-bar__center">
        <span className="status-bar__online-pill">
          <span className="status-bar__dot status-bar__dot--live" />
          System Online
        </span>
        <span className="status-bar__clock">{hh}:{mm}:{ss}</span>
        <span className="status-bar__date">{dateStr}</span>
      </div>

      {/* Right: theme toggle + operator */}
      <div className="status-bar__right">
        <button className="status-bar__icon-btn" aria-label="Toggle theme">
          <Moon size={13} />
        </button>
        <div className="status-bar__operator">
          <span className="status-bar__avatar" aria-hidden="true">
            <User size={13} />
          </span>
          <div className="status-bar__operator-info">
            <span className="status-bar__operator-name">Operator</span>
            <span className="status-bar__operator-role">Admin</span>
          </div>
          <span className="status-bar__chevron" aria-hidden="true">
            <ChevronDown size={12} />
          </span>
        </div>
      </div>
    </header>
  );
}
