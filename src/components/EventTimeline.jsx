import { Footprints, AlertTriangle, UserX, Car, Link } from 'lucide-react';
import './EventTimeline.css';
import { SEVERITY_COLOR } from '../data/scenario';

// Icon per event type
function EventIcon({ type, severity }) {
  const color = SEVERITY_COLOR[severity] ?? 'var(--text-dim)';
  const icons = {
    person_detected:            <Footprints size={11} />,
    intrusion:                  <AlertTriangle size={11} />,
    watchlist_match:            <UserX size={11} />,
    vehicle_person_association: <Car size={11} />,
    cross_camera_match:         <Link size={11} />,
  };
  return (
    <span className="etl__icon" style={{ '--c': color }}>
      {icons[type] ?? '●'}
    </span>
  );
}

// Severity pill
function SeverityDot({ severity }) {
  const color = SEVERITY_COLOR[severity] ?? 'var(--text-dim)';
  const labels = { HIGH: 'HIGH', MEDIUM: 'MED', LOW: 'LOW' };
  return (
    <span className="etl__sev" style={{ '--c': color }}>
      {labels[severity] ?? severity}
    </span>
  );
}

// Sublabel per event type
const SUBLABELS = {
  person_detected:            (ev) => `YOLO detection • ID: ${ev.entity?.entity_id}`,
  intrusion:                  ()   => 'Virtual fence breach • Severity: HIGH',
  watchlist_match:            ()   => 'Potential match found • Confidence: 78%',
  vehicle_person_association: ()   => 'ANPR: MH04AB1234 • ID: V-003',
  cross_camera_match:         ()   => 'Vehicle V-003 matched from BOP-01',
};

export default function EventTimeline({ events }) {
  return (
    <div className="etl">
      {/* Header */}
      <div className="etl__head">
        <span className="etl__head-label">EVENT TIMELINE</span>
        <span className="etl__head-count">{events.length} events</span>
      </div>

      {/* Scrollable list */}
      <div className="etl__list">
        {events.length === 0 && (
          <div className="etl__empty">Monitoring — no events yet</div>
        )}

        {events.map((ev) => {
          const sublabel = SUBLABELS[ev.event_type]?.(ev) ?? ev.label;
          return (
            <div key={ev.event_id} className="etl__item">
              {/* Left: timestamp + camera */}
              <div className="etl__left">
                <span className="etl__time">{ev.timestamp}</span>
                <span className="etl__cam">{ev.camera_id}</span>
              </div>

              {/* Center: icon + vertical connector */}
              <div className="etl__mid">
                <EventIcon type={ev.event_type} severity={ev.severity} />
                <span className="etl__connector" />
              </div>

              {/* Right: label + sublabel */}
              <div className="etl__right">
                <div className="etl__label-row">
                  <span className="etl__label">{ev.label}</span>
                  <SeverityDot severity={ev.severity} />
                </div>
                <span className="etl__sublabel">{sublabel}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
