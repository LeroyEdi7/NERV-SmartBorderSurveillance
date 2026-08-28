import { Footprints, AlertTriangle, UserX, Car, Link } from 'lucide-react';
import './AlertsFeed.css';
import { SEVERITY_COLOR } from '../data/scenario';

const EVENT_ICONS = {
  person_detected:            { icon: <Footprints size={12} />, bg: '#34d9b4' },
  intrusion:                  { icon: <AlertTriangle size={12} />,  bg: '#e14b3c' },
  watchlist_match:            { icon: <UserX size={12} />, bg: '#e8a13d' },
  vehicle_person_association: { icon: <Car size={12} />, bg: '#4e9fe8' },
  cross_camera_match:         { icon: <Link size={12} />, bg: '#a87ce8' },
};

const SEVERITY_LABEL = { HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW', INFO: 'INFO' };

export default function AlertsFeed({ events, onViewAll, onSelectAlert }) {
  return (
    <div className="alerts-feed">
      {/* Header */}
      <div className="alerts-feed__head">
        <span className="alerts-feed__head-title">ACTIVE ALERTS</span>
        <button
          className="alerts-feed__view-all"
          onClick={() => onViewAll?.()}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
        >
          View All
        </button>
      </div>

      {/* List */}
      <div className="alerts-feed__list">
        {events.length === 0 && (
          <div className="alerts-feed__empty">Monitoring — no alerts</div>
        )}

        {events.map((ev) => {
          const meta  = EVENT_ICONS[ev.event_type] ?? { icon: '●', bg: '#52666d' };
          const color = SEVERITY_COLOR[ev.severity] ?? 'var(--text-dim)';
          return (
            <div
              key={ev.event_id}
              className="alerts-feed__item"
              style={{ '--accent': color, '--icon-bg': meta.bg, cursor: 'pointer' }}
              onClick={() => onSelectAlert ? onSelectAlert(ev) : onViewAll?.()}
            >
              {/* Icon badge */}
              <span className="alerts-feed__icon-wrap">
                <span className="alerts-feed__icon">{meta.icon}</span>
              </span>

              {/* Body */}
              <div className="alerts-feed__body">
                <div className="alerts-feed__item-top">
                  <span className="alerts-feed__label">{ev.label}</span>
                  <span className="alerts-feed__severity">{SEVERITY_LABEL[ev.severity] ?? ev.severity}</span>
                </div>
                <div className="alerts-feed__item-meta">
                  <span className="alerts-feed__cam">{ev.camera_id}</span>
                  <span className="alerts-feed__sep">•</span>
                  <span className="alerts-feed__time">{ev.timestamp}</span>
                  {ev.entity?.entity_id && (
                    <>
                      <span className="alerts-feed__sep">•</span>
                      <span className="alerts-feed__entity">{ev.entity.entity_id}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Thumbnail placeholder */}
              <div className="alerts-feed__thumb" aria-hidden="true">
                <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect width="36" height="36" fill="#161f24"/>
                  <circle cx="18" cy="14" r="6" fill="#223038"/>
                  <path d="M4 34c0-7.732 6.268-12 14-12s14 4.268 14 12" fill="#223038"/>
                </svg>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
